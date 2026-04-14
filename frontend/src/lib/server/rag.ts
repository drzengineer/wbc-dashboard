import { pipeline } from "@xenova/transformers";
import Groq from "groq-sdk";
import { GROQ_API_KEY } from "$env/static/private";
import { supabase } from "./db";

const groq = new Groq({ apiKey: GROQ_API_KEY });

// ── Embedding ─────────────────────────────────────────────────────────────────

let embedder: any;
async function embedQuestion(question: string): Promise<number[]> {
	if (!embedder) {
		console.log("[RAG] Loading local embedding model (all-MiniLM-L6-v2)...");
		embedder = await pipeline("feature-extraction", "Xenova/all-MiniLM-L6-v2");
		console.log("[RAG] Embedding model loaded.");
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
	question: string,
	targetTables: string[],
): Promise<string> {
	console.log(`[RAG] Querying pgvector tables: ${targetTables.join(", ")}`);
	
	const allResults: VectorRow[] = [];
	const PER_TABLE_RESULTS = Math.floor(30 / targetTables.length);

	for (const table of targetTables) {
		console.log(`[RAG]  → Querying ${table}...`);
		
		const { data, error } = await supabase
			.schema("vectors")
			.rpc(`match_${table}`, {
				query_embedding: embedding,
				match_count: PER_TABLE_RESULTS,
				match_threshold: 0.4,
			});

		if (error) {
			console.warn(`[RAG] Warning: failed querying ${table}: ${error.message}`);
			continue;
		}

		if (data && data.length > 0) {
			allResults.push(...(data as VectorRow[]));
		}
	}

	if (allResults.length === 0) {
		console.log("[RAG] No vectors returned — context will be empty.");
		return "";
	}

	const results = allResults.sort((a, b) => b.similarity - a.similarity).slice(0, 40);

	console.log(`[RAG] Retrieved ${results.length} total vectors for: "${question}"`);
	console.log("[RAG] ── Matched vectors (best → worst) ─────────────────────");
	results.forEach((r, i) => {
		const sim = r.similarity.toFixed(4);
		const source = r.metadata?.source ?? "unknown";
		const season = r.metadata?.season ?? "";
		const preview =
			r.content.length > 120 ? `${r.content.slice(0, 120)}…` : r.content;
		console.log(
			`[RAG]  ${String(i + 1).padStart(2)}. [${sim}] (${source}${season ? ` ${season}` : ""}) ${preview}`,
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

// ── Question rewriting ────────────────────────────────────────────────────────

async function classifyQuestionIntent(question: string): Promise<string[]> {
	console.log(`[RAG] Classifying intent for: "${question}"`);

	const completion = await groq.chat.completions.create({
		model: "llama-3.3-70b-versatile",
		max_tokens: 64,
		temperature: 0,
		messages: [
			{
				role: "system",
				content: `You are a WBC question classifier. Classify what type of information is being requested.

AVAILABLE CATEGORIES:
- game_results: Game scores, results, knockouts, mercy rule, innings, venues, blowouts
- standings: Pool standings, pool winners, win/loss records
- team_season: Overall team season records
- player_season: Player season stats, season leaders, advanced stats
- player_bio: Player biographical info, height, weight, birthplace, position
- player_game: Single game player performance
- team_game: Team per-game stats

RULES:
- Return ONLY comma-separated category names from the list above
- Return multiple categories if the question asks for multiple types
- If unsure, return all categories
- No explanation, just the comma separated list

Examples:
"Who won 2023 WBC?" → game_results
"How did Ohtani bat in 2023?" → player_season
"What was Ohtani's ERA in the final game?" → player_game
"Who won Pool A?" → standings
"How tall is Ohtani?" → player_bio
`,
			},
			{ role: "user", content: question },
		],
	});

	const categories = completion.choices[0]?.message?.content?.trim() || "game_results";
	const targetTables = categories.split(",").map(s => s.trim()).filter(s => s.length > 0);
	
	console.log(`[RAG] Classified intent: ${targetTables.join(", ")}`);
	return targetTables;
}

async function rewriteQuestion(
	question: string,
	history: HistoryMessage[],
): Promise<string> {
	if (history.length === 0) return question;

	console.log(
		`[RAG] Rewriting question with ${history.length} history messages...`,
	);

	const completion = await groq.chat.completions.create({
		model: "llama-3.3-70b-versatile",
		max_tokens: 128,
		temperature: 0,
		messages: [
			{
				role: "system",
				content: `You are a question rewriter. Your ONLY job is to rewrite the user's question into a standalone question using context from the conversation history.

CRITICAL RULES:
- DO NOT answer the question. Only rewrite it.
- DO NOT add facts, statistics, names, or information not explicitly mentioned in the conversation history.
- ONLY add context that was directly stated in prior messages (player names, years, teams).
- The output must be a QUESTION, not a statement or answer.
- If the question is already standalone, return it unchanged.

Examples:
- "who won each year?" → "Which team won the World Baseball Classic in each year?"
- "how many rbi's did he get?" (history mentions Ohtani) → "How many RBI's did Ohtani get?"
- "what about 2023?" (history about 2026 results) → "What were the results for the 2023 World Baseball Classic?"
- "how did they do?" (history about Japan) → "How did Japan do?"

Output ONLY the rewritten question.`,
			},
			...history.slice(-6),
			{ role: "user", content: question },
		],
	});

	const rewritten = completion.choices[0]?.message?.content?.trim() || question;
	console.log(`[RAG] Rewritten: "${question}" → "${rewritten}"`);
	return rewritten;
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

	const standaloneQuestion = await rewriteQuestion(question, history);
	const targetTables = await classifyQuestionIntent(standaloneQuestion);
	const embedding = await embedQuestion(standaloneQuestion);
	const context = await retrieveContext(embedding, standaloneQuestion, targetTables);

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
				content: `Context:\n${context}\n\nQuestion: ${standaloneQuestion}`,
			},
		],
	});

	console.log("[RAG] Groq stream started — streaming response to client.");

	return new ReadableStream({
		async start(controller) {
			for await (const chunk of groqStream) {
				const token = chunk.choices[0]?.delta?.content ?? "";
				if (token) controller.enqueue(new TextEncoder().encode(token));
			}
			controller.close();
			console.log("[RAG] Stream complete.\n");
		},
	});
}
