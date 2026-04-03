import { error } from "@sveltejs/kit";
import { queryRagStream } from "$lib/server/rag";
import type { RequestHandler } from "./$types";

export const POST: RequestHandler = async ({ request }) => {
	const body = await request.json();
	const question: string = body.question?.trim();
	const history: Array<{ role: "user" | "assistant"; content: string }> =
		body.messages ?? [];

	if (!question) {
		throw error(400, "question is required");
	}

	try {
		const stream = await queryRagStream(question, history);
		return new Response(stream, {
			headers: {
				"Content-Type": "text/plain; charset=utf-8",
				"X-Content-Type-Options": "nosniff",
			},
		});
	} catch (err) {
		console.error("RAG error:", err);
		throw error(500, "RAG query failed");
	}
};
