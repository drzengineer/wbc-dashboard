import { error } from "@sveltejs/kit";
import { queryRagStream } from "$lib/server/rag";
import type { RequestHandler } from "./$types";

export const POST: RequestHandler = async ({ request }) => {
	const body = await request.json();
	const question: string = body.question?.trim();

	if (!question) {
		throw error(400, "question is required");
	}

	try {
		const stream = await queryRagStream(question);
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
