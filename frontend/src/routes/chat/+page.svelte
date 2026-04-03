<script lang="ts">
import { Check, Copy, Send, Sparkles } from "lucide-svelte";
import { tick } from "svelte";

type Message = { role: "user" | "assistant"; content: string };

let messages = $state<Message[]>([]);
let question = $state("");
let loading = $state(false);
let messagesEnd = $state<HTMLElement | null>(null);
let copiedIndex = $state<number | null>(null);

async function scrollToBottom() {
	await tick();
	messagesEnd?.scrollIntoView({ behavior: "smooth" });
}

async function handleSubmit() {
	const q = question.trim();
	if (!q || loading) return;

	messages = [...messages, { role: "user", content: q }];
	question = "";
	loading = true;

	messages = [...messages, { role: "assistant", content: "" }];
	await scrollToBottom();

	const res = await fetch("/api/chat", {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify({ question: q, messages: messages.slice(0, -1) }),
	});

	if (!res.ok || !res.body) {
		messages[messages.length - 1] = {
			role: "assistant",
			content: "Something went wrong. Please try again.",
		};
		loading = false;
		return;
	}

	const reader = res.body.getReader();
	const decoder = new TextDecoder();

	while (true) {
		const { done, value } = await reader.read();
		if (done) break;
		const chunk = decoder.decode(value, { stream: true });
		messages[messages.length - 1] = {
			role: "assistant",
			content: messages[messages.length - 1].content + chunk,
		};
		scrollToBottom();
	}

	loading = false;
}

function handleKeydown(e: KeyboardEvent) {
	if (e.key === "Enter" && !e.shiftKey) {
		e.preventDefault();
		handleSubmit();
	}
}

async function copyMessage(index: number, content: string) {
	await navigator.clipboard.writeText(content);
	copiedIndex = index;
	setTimeout(() => {
		copiedIndex = null;
	}, 2000);
}

const suggestions = [
	"Who won the 2023 WBC?",
	"How did Ohtani do in 2026?",
	"Which team had the best pool play record?",
	"Who hit the most home runs?",
];
</script>

<div class="flex flex-col h-[calc(100vh-8rem)] md:h-[calc(100vh-4rem)] max-w-3xl mx-auto animate-fade-in">
	<div class="mb-4 shrink-0">
		<h1 class="text-xl md:text-2xl font-bold text-white">AI Chat</h1>
		<p class="text-sm text-[#8888a0] mt-1">Ask anything about the World Baseball Classic</p>
	</div>

	<!-- Messages -->
	<div class="flex-1 overflow-y-auto space-y-4 pr-1 mb-4">
		{#if messages.length === 0}
			<div class="flex flex-col items-center justify-center h-full gap-8 text-center">
				<div>
					<div class="w-16 h-16 rounded-2xl bg-accent/10 border border-accent/20 flex items-center justify-center mx-auto mb-4">
						<Sparkles class="w-8 h-8 text-accent" />
					</div>
					<p class="text-[#8888a0] text-sm max-w-md">
						Ask anything about the World Baseball Classic — stats, results, players, or history.
					</p>
				</div>
				<div class="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-lg">
					{#each suggestions as s}
						<button
							type="button"
							onclick={() => { question = s; handleSubmit(); }}
							class="text-left px-4 py-3 bg-surface border border-border rounded-xl text-sm text-[#f0f0f5] hover:border-accent/30 hover:text-white transition-all duration-200"
						>{s}</button>
					{/each}
				</div>
			</div>
		{:else}
			{#each messages as msg, i}
				<div class="flex {msg.role === 'user' ? 'justify-end' : 'justify-start'}">
					<div class="max-w-[85%] group relative
						{msg.role === 'user'
							? 'bg-accent text-white rounded-2xl rounded-br-sm px-4 py-3 text-sm'
							: 'bg-surface border border-border text-[#f0f0f5] rounded-2xl rounded-bl-sm px-4 py-3 text-sm whitespace-pre-wrap'}">
						{#if msg.role === 'assistant' && msg.content === '' && loading && i === messages.length - 1}
							<div class="flex items-center gap-1.5 py-1">
								<div class="w-2 h-2 bg-[#8888a0] rounded-full animate-bounce" style="animation-delay: 0ms"></div>
								<div class="w-2 h-2 bg-[#8888a0] rounded-full animate-bounce" style="animation-delay: 150ms"></div>
								<div class="w-2 h-2 bg-[#8888a0] rounded-full animate-bounce" style="animation-delay: 300ms"></div>
							</div>
						{:else}
							{msg.content}
						{/if}

						{#if msg.role === 'assistant' && msg.content && !loading}
							<button
								type="button"
								onclick={() => copyMessage(i, msg.content)}
								class="absolute -top-2 -right-2 p-1.5 bg-surface-hover border border-border-light rounded-lg opacity-0 group-hover:opacity-100 transition-opacity text-[#8888a0] hover:text-white"
								title="Copy"
							>
								{#if copiedIndex === i}
									<Check class="w-3.5 h-3.5 text-success" />
								{:else}
									<Copy class="w-3.5 h-3.5" />
								{/if}
							</button>
						{/if}
					</div>
				</div>
			{/each}
			<div bind:this={messagesEnd}></div>
		{/if}
	</div>

	<!-- Input -->
	<div class="shrink-0 bg-surface border border-border rounded-xl focus-within:border-accent/50 transition-colors">
		<textarea
			bind:value={question}
			onkeydown={handleKeydown}
			rows="2"
			placeholder="Ask anything about the WBC..."
			disabled={loading}
			class="w-full bg-transparent px-4 pt-3 pb-1 text-sm text-white placeholder-[#555570] resize-none focus:outline-none disabled:opacity-50"
		></textarea>
		<div class="flex items-center justify-end px-3 pb-2">
			<button
				type="button"
				onclick={handleSubmit}
				disabled={loading || !question.trim()}
				class="px-4 py-1.5 bg-accent hover:bg-accent-hover disabled:opacity-40 rounded-lg text-xs font-semibold transition-colors flex items-center gap-1.5"
			>
				<Send class="w-3.5 h-3.5" />
				{loading ? 'Thinking…' : 'Send'}
			</button>
		</div>
	</div>
</div>