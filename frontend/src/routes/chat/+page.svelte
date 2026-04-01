<script lang="ts">
  import { onMount, tick } from 'svelte';

  type Message = { role: 'user' | 'assistant'; content: string };

  let messages = $state<Message[]>([]);
  let question = $state('');
  let loading  = $state(false);
  let messagesEnd = $state<HTMLElement | null>(null);

  async function scrollToBottom() {
    await tick();
    messagesEnd?.scrollIntoView({ behavior: 'smooth' });
  }

  async function handleSubmit() {
    const q = question.trim();
    if (!q || loading) return;

    messages = [...messages, { role: 'user', content: q }];
    question = '';
    loading = true;

    // Add empty assistant message that we'll stream into
    messages = [...messages, { role: 'assistant', content: '' }];
    await scrollToBottom();

    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: q }),
    });

    if (!res.ok || !res.body) {
      messages[messages.length - 1] = { role: 'assistant', content: 'Something went wrong. Please try again.' };
      loading = false;
      return;
    }

    const reader  = res.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const chunk = decoder.decode(value, { stream: true });
      messages[messages.length - 1] = {
        role: 'assistant',
        content: messages[messages.length - 1].content + chunk,
      };
      scrollToBottom();
    }

    loading = false;
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  }

  // Suggestions
  const suggestions = [
    'Who won the 2023 WBC?',
    'How did Ohtani do in 2026?',
    'Which team had the best pool play record?',
    'Who hit the most home runs?',
  ];
</script>

<div class="flex flex-col h-[calc(100vh-8rem)] md:h-[calc(100vh-4rem)] max-w-3xl mx-auto">
  <h1 class="text-xl md:text-2xl font-bold mb-4 shrink-0">AI Chat</h1>

  <!-- Message area -->
  <div class="flex-1 overflow-y-auto space-y-4 pr-1 mb-4">
    {#if messages.length === 0}
      <!-- Empty state with suggestions -->
      <div class="flex flex-col items-center justify-center h-full gap-6 text-center">
        <div>
          <div class="text-4xl mb-3">⚾</div>
          <p class="text-gray-400 text-sm">Ask anything about the World Baseball Classic — stats, results, players, or history.</p>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-lg">
          {#each suggestions as s}
            <button
            type="button"
              onclick={() => { question = s; handleSubmit(); }}
              class="text-left px-4 py-3 bg-gray-800/60 border border-gray-700 rounded-xl text-sm text-gray-300 hover:border-blue-500/50 hover:text-white transition-colors"
            >{s}</button>
          {/each}
        </div>
      </div>
    {:else}
      {#each messages as msg, i}
        <div class="flex {msg.role === 'user' ? 'justify-end' : 'justify-start'}">
          <div class="max-w-[85%] {msg.role === 'user'
            ? 'bg-blue-600 text-white rounded-2xl rounded-br-sm px-4 py-3 text-sm'
            : 'bg-gray-800 border border-gray-700 text-gray-200 rounded-2xl rounded-bl-sm px-4 py-3 text-sm whitespace-pre-wrap'}">
            {#if msg.role === 'assistant' && msg.content === '' && loading && i === messages.length - 1}
              <!-- Typing indicator -->
              <div class="flex items-center gap-1.5 py-1">
                <div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 0ms"></div>
                <div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 150ms"></div>
                <div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 300ms"></div>
              </div>
            {:else}
              {msg.content}
            {/if}
          </div>
        </div>
      {/each}
      <div bind:this={messagesEnd}></div>
    {/if}
  </div>

  <!-- Input area -->
  <div class="shrink-0 bg-gray-900 border border-gray-700 rounded-xl focus-within:border-blue-500 transition-colors">
    <textarea
      bind:value={question}
      onkeydown={handleKeydown}
      rows="2"
      placeholder="Ask anything about the WBC..."
      disabled={loading}
      class="w-full bg-transparent px-4 pt-3 pb-1 text-sm text-white placeholder-gray-500 resize-none focus:outline-none disabled:opacity-50"
    ></textarea>
    <div class="flex items-center justify-end px-3 pb-2">
      <button
      type="button"
        onclick={handleSubmit}
        disabled={loading || !question.trim()}
        class="px-4 py-1.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-40 rounded-lg text-xs font-semibold transition-colors"
      >
        {loading ? 'Thinking…' : 'Send'}
      </button>
    </div>
  </div>
</div>