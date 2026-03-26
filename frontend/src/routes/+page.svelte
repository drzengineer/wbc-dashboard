<script lang="ts">
let question = $state("");
let answer = $state("");
let loading = $state(false);

async function ask() {
	loading = true;
	answer = "";

	const res = await fetch("/api/chat", {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify({ question }),
	});

	if (!res.ok || !res.body) {
		answer = "Something went wrong.";
		loading = false;
		return;
	}

	const reader = res.body.getReader();
	const decoder = new TextDecoder();

	while (true) {
		const { done, value } = await reader.read();
		if (done) break;
		answer += decoder.decode(value, { stream: true });
	}

	loading = false;
}
</script>

<main>
  <h1>WBC RAG Test</h1>
  <input bind:value={question} placeholder="Ask about the WBC..." />
  <button onclick={ask} disabled={loading}>
    {loading ? 'Thinking...' : 'Ask'}
  </button>
  {#if answer}
    <p>{answer}</p>
  {/if}
</main>