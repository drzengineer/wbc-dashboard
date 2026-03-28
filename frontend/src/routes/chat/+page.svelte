<script lang="ts">
  let question = $state('');
  let answer = $state('');
  let loading = $state(false);

  async function handleSubmit() {
    if (!question.trim() || loading) return;

    loading = true;
    answer = '';

    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question }),
    });

    if (!res.ok || !res.body) {
      answer = 'Something went wrong.';
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

<h1 class="text-2xl font-bold mb-6">AI Chat</h1>

<div class="max-w-2xl flex flex-col gap-4">
  <textarea
    bind:value={question}
    rows="3"
    placeholder="Ask anything about the WBC..."
    class="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-3 text-sm text-white placeholder-gray-500 resize-none focus:outline-none focus:border-blue-500"
  ></textarea>

  <button
    type="button"
    onclick={handleSubmit}
    disabled={loading}
    class="self-start px-5 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 rounded-lg text-sm font-medium transition-colors"
  >
    {loading ? 'Thinking...' : 'Ask'}
  </button>

  {#if answer}
    <div class="bg-gray-900 border border-gray-800 rounded-lg px-4 py-3 text-sm text-gray-200 whitespace-pre-wrap">
      {answer}
    </div>
  {/if}
</div>