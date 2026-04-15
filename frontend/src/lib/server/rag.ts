import { pipeline } from "@xenova/transformers";
import Groq from "groq-sdk";
import { GROQ_API_KEY } from "$env/static/private";
import { supabase } from "./db";

const groq = new Groq({ apiKey: GROQ_API_KEY });

// ── Embedding ─────────────────────────────────────────────────────────────────

let embedder: any;
let embedderLoadingPromise: Promise<any> | null = null;

async function embedQuestion(question: string): Promise<number[]> {
	if (!embedder) {
		if (!embedderLoadingPromise) {
			console.log("[RAG] Loading local embedding model (all-MiniLM-L6-v2)...");
			embedderLoadingPromise = pipeline("feature-extraction", "Xenova/all-MiniLM-L6-v2");
			embedder = await embedderLoadingPromise;
			console.log("[RAG] Embedding model loaded.");
		} else {
			await embedderLoadingPromise;
		}
	}
	const output = await embedder(question, { pooling: "mean", normalize: true });
	const embedding = Array.from(output.data) as number[];
	console.log(
		`[RAG] Embedded question (${embedding.length} dims): "${question}"`,
	);
	return embedding;
}

// ── Retrieval ─────────────────────────────────────────────────────────────────

type VectorRow = {
	content: string;
	similarity: number;
	metadata: Record<string, unknown>;
};

async function retrieveContext(
	embedding: number[],
	allowedCategories: string[],
	filters: { seasons: number[], teams: string[], players: string[] }
): Promise<string> {

	// ✅ Graduated Fallback Logic - 3 attempts in priority order
	const fallbackAttempts = [
		{
			name: "Full filters",
			teams: filters.teams,
			players: filters.players,
			threshold: 0.40
		},
		{
			name: "Removed player filter",
			teams: filters.teams,
			players: [],
			threshold: 0.40
		},
		{
			name: "Removed team + player filters",
			teams: [],
			players: [],
			threshold: 0.40
		}
	];

	let allResults: VectorRow[] = [];

	for (const attempt of fallbackAttempts) {
		const activeFilters = [
			`categories=${allowedCategories.join(",")}`,
			filters.seasons.length > 0 ? `seasons=${filters.seasons}` : null,
			attempt.teams.length > 0 ? `teams=${attempt.teams}` : null,
			attempt.players.length > 0 ? `players=${attempt.players}` : null,
		].filter(Boolean).join(" ");
		
		console.log(`[RAG] Querying pgvector [${attempt.name}]: ${activeFilters}`);

		const { data, error } = await supabase
			.schema("vectors")
			.rpc(`match_embeddings`, {
				query_embedding: embedding,
				match_count: 50,
				match_threshold: attempt.threshold,
				allowed_categories: allowedCategories,
				filter_seasons: filters.seasons.length > 0 ? filters.seasons : null,
				filter_teams: attempt.teams.length > 0 ? attempt.teams : null,
				filter_players: attempt.players.length > 0 ? attempt.players : null,
			});

		if (error) {
			console.warn(`[RAG] Warning: failed querying vectors: ${error.message}`);
			continue;
		}

		allResults = data ? (data as VectorRow[]) : [];

		if (allResults.length > 0) {
			console.log(`[RAG] ✅ Found ${allResults.length} vectors on fallback attempt`);
			break;
		}

		console.log(`[RAG] No results, proceeding to next fallback level`);
	}

	if (allResults.length === 0) {
		console.log("[RAG] No vectors returned after all fallbacks — context will be empty.");
		return "";
	}

	const results = allResults.slice(0, 50);

	// We don't have question in scope here, it was intentionally removed as unused parameter
	console.log(`[RAG] Retrieved ${results.length} total vectors`);
	console.log("[RAG] ── Matched vectors (best → worst) ─────────────────────");
	results.forEach((r, i) => {
		const sim = r.similarity.toFixed(4);
		const category = r.metadata?.category ?? "unknown";
		const season = r.metadata?.season ?? "";
		const team = r.metadata?.team ?? "";
		const player = r.metadata?.player ?? "";
		
		const metaParts = [category, season, team, player].filter(Boolean).join(" ");
		const preview = r.content.length > 120 ? `${r.content.slice(0, 120)}…` : r.content;
		
		console.log(
			`[RAG]  ${String(i + 1).padStart(2)}. [${sim}] (${metaParts}) ${preview}`,
		);
	});
	console.log("[RAG] ──────────────────────────────────────────────────────");

	const context = results.map((r) => r.content).join("\n\n");
	console.log("[RAG] ── Full context sent to Groq ─────────────────────────");
	console.log(context);
	console.log("[RAG] ──────────────────────────────────────────────────────");

	return context;
}

type HistoryMessage = { role: "user" | "assistant"; content: string };

// ── Combined Intelligence ─────────────────────────────────────────────────────
// ✅ 3 operations in ONE single LLM call: rewrite + classify + extract
// Cuts latency by ~66% and reduces Groq costs by 66%

async function processQuestion(
	question: string,
	history: HistoryMessage[],
): Promise<{
	standaloneQuestion: string;
	categories: string[];
	seasons: number[];
	teams: string[];
	players: string[];
}> {
	if (history.length > 0) {
		console.log(`[RAG] Processing question with ${history.length} history messages...`);
	}

	const completion = await groq.chat.completions.create({
		model: "llama-3.3-70b-versatile",
		max_tokens: 256,
		temperature: 0,
		response_format: { type: "json_object" },
		messages: [
			{
				role: "system",
				content: `You are the WBC RAG intelligence layer. Process this question and return ONLY valid JSON.

Perform ALL 3 tasks and return:
{
  "standalone": "rewritten standalone question using conversation history",
  "categories": [array of matching categories from list below],
  "seasons": [array of year integers mentioned],
  "teams": [array of WBC team names mentioned],
  "players": [array of full player names mentioned]
}

AVAILABLE CATEGORIES:
- game_recap: Game stories, results, scores, knockout matches
- game_qa: Direct knockout game Q&A pairs
- team_profile: Team season performance, standings, advancement
- player_profile: Single tournament player performance
- player_career: Multi-tournament player history
- player_bio: Player biographical information
- standout_game: Individual player single game hero moments

RULES:
- Standalone question must be fully self contained using context from history
- Do NOT answer the question, only rewrite it
- Return 1+ relevant categories
- If unsure, return all categories

✅ TEAM NORMALIZATION:
For teams, return BOTH the 3 letter abbreviation AND the full official name.
Use EXACTLY these values only:
  USA → ["USA", "United States"]
  JPN → ["JPN", "Japan"]
  DOM → ["DOM", "Dominican Republic"]
  PUR → ["PUR", "Puerto Rico"]
  KOR → ["KOR", "Korea"]
  MEX → ["MEX", "Mexico"]
  VEN → ["VEN", "Venezuela"]
  CAN → ["CAN", "Canada"]
  CUB → ["CUB", "Cuba"]
  TPE → ["TPE", "Chinese Taipei"]
  COL → ["COL", "Colombia"]
  AUS → ["AUS", "Australia"]
  NED → ["NED", "Kingdom of the Netherlands"]
  ITA → ["ITA", "Italy"]
  ISR → ["ISR", "Israel"]
  CZE → ["CZE", "Czechia"]
  GBR → ["GBR", "Great Britain"]
  PAN → ["PAN", "Panama"]
  NCA → ["NCA", "Nicaragua"]
  ESP → ["ESP", "Spain"]
  BRA → ["BRA", "Brazil"]
  RSA → ["RSA", "South Africa"]
  CHN → ["CHN", "China"]

✅ EXAMPLE:
If user says "how did USA do in 2017?" you must return "teams": ["USA", "United States"]
Do not invent team names. Do not use "United States of America".

- No extra text. Return ONLY valid JSON.`,
			},
			...history.slice(-6),
			{ role: "user", content: question },
		],
	});

	try {
		const result = JSON.parse(completion.choices[0]?.message?.content || "{}");
		
		const standalone = result.standalone || question;
		const categories = result.categories || ["game_recap"];
		const seasons = result.seasons || [];
		const teams = result.teams || [];
		const players = result.players || [];

		if (standalone !== question) {
			console.log(`[RAG] Rewritten: "${question}" → "${standalone}"`);
		}
		console.log(`[RAG] Classified intent: ${categories.join(", ")}`);
		console.log(`[RAG] Extracted entities: seasons=${JSON.stringify(seasons)} teams=${JSON.stringify(teams)} players=${JSON.stringify(players)}`);

		return {
			standaloneQuestion: standalone,
			categories,
			seasons,
			teams,
			players
		};
	} catch (e) {
		console.warn(`[RAG] Failed to parse, falling back to defaults`);
		return {
			standaloneQuestion: question,
			categories: ["game_recap"],
			seasons: [],
			teams: [],
			players: []
		};
	}
}

// ── RAG stream ────────────────────────────────────────────────────────────────

export async function queryRagStream(
	question: string,
	history: HistoryMessage[] = [],
): Promise<ReadableStream> {
	console.log(
		`\n[RAG] ═══════════════════════════════════════════════════════`,
	);
	console.log(`[RAG] New question: "${question}"`);
	if (history.length > 0) {
		console.log(`[RAG] Conversation history: ${history.length} messages`);
	}

	const processed = await processQuestion(question, history);
	const embedding = await embedQuestion(processed.standaloneQuestion);
	const context = await retrieveContext(embedding, processed.categories, processed);

	if (!context) {
		console.log("[RAG] Sending to Groq with empty context.");
	} else {
		console.log(
			`[RAG] Sending to Groq — context length: ${context.length} chars`,
		);
	}

	const groqStream = await groq.chat.completions.create({
		model: "llama-3.3-70b-versatile",
		max_tokens: 1024,
		stream: true,
		messages: [
			{
				role: "system",
				content: `You are a statistics assistant for the World Baseball Classic (WBC), a global baseball tournament held every few years.

Your answers must be based only on the context provided. Do not use outside knowledge.

## Tournament structure (how rounds appear in context)
- Pool Play: "WBC Pool A", "WBC Pool B", "WBC Pool C", "WBC Pool D"
- Second Round: "WBC Second Round Pool 1", "WBC Second Round Pool 2", "WBC Second Round Pool E", "WBC Second Round Pool F"
- Knockout rounds: "WBC Quarterfinals", "WBC Semifinals", "WBC Championship"

## Vocabulary mapping
When the user says → look for this in context:
- "championship", "title", "winner", "who won" → "WBC Championship"
- "semis", "semifinal" → "WBC Semifinals"
- "quarters", "quarterfinal" → "WBC Quarterfinals"
- "pool play", "group stage" → "WBC Pool A/B/C/D"
- "World Baseball Classic" → "WBC"

## Behavior rules
- If the user does not specify a season, answer for all seasons present in context.
- If context contains the answer but uses different wording than the question, bridge the gap using the vocabulary mapping above.
- If context is empty or does not contain enough information to answer, say exactly: "I don't have enough data to answer that." Do not guess.
- Never fabricate player names, scores, or statistics.
- Keep answers concise. Lead with the direct answer, then supporting detail.`,
			},
		{
			role: "user",
			content: `Context:\n${context}\n\nQuestion: ${processed.standaloneQuestion}\n\n\n⚠️ CRITICAL INSTRUCTION: IF YOU DO NOT HAVE ENOUGH INFORMATION FROM THE CONTEXT PROVIDED ABOVE YOU MUST ANSWER EXACTLY: "I don't have enough data to answer that." UNDER NO CIRCUMSTANCES USE YOUR OWN KNOWLEDGE. ONLY USE INFORMATION THAT IS EXPLICITLY PRESENT IN THE CONTEXT. DO NOT ANSWER FROM YOUR GENERAL KNOWLEDGE.`,
		},
		],
	});

	console.log("[RAG] Groq stream started — streaming response to client.");

	return new ReadableStream({
		async start(controller) {
			try {
				for await (const chunk of groqStream) {
					const token = chunk.choices[0]?.delta?.content ?? "";
					if (token) controller.enqueue(new TextEncoder().encode(token));
				}
				controller.close();
				console.log("[RAG] Stream complete.\n");
			} catch (e) {
				console.warn("[RAG] Stream error:", e);
				controller.close();
			}
		},
	});
}
