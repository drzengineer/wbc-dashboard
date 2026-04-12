<script lang="ts">
import { Check, Copy, Send, Sparkles, X, MessageCircle } from "lucide-svelte";
import { tick } from "svelte";

type Message = { role: "user" | "assistant"; content: string };

let open = $state(false);

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
	"how far did USA go in 2013?",
	"Who hit the most home runs?",
];
</script>

{#if open}
<!-- Backdrop overlay -->
<div 
	class="fixed inset-0 z-40 bg-black/30"
	onclick={() => open = false}
></div>

<!-- Chat drawer -->
<div class="fixed right-0 bottom-0 z-50 w-full sm:w-[85%] md:w-[65%] lg:w-[48%] xl:w-[38%] max-w-[520px] h-[75vh] bg-[#0a0a0f] border border-border rounded-t-xl shadow-2xl flex flex-col animate-slide-in">
	<!-- Chat header -->
	<div class="flex items-center justify-between px-[4%] py-2.5 border-b border-border shrink-0">
		<div>
			<h2 class="text-base font-semibold text-white">AI Chat</h2>
		</div>
		<button 
			type="button" 
			onclick={() => open = false}
			class="p-2 rounded-lg text-[#8888a0] hover:text-white hover:bg-surface-hover transition-colors"
		>
			<X class="w-5 h-5" />
		</button>
	</div>

	<!-- Messages -->
	<div class="flex-1 overflow-y-auto space-y-4 px-[4%] py-4">
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
				<div class="grid grid-cols-2 gap-2 w-full">
					{#each suggestions as s}
						<button
							type="button"
							onclick={() => { question = s; handleSubmit(); }}
						class="text-left px-3 py-2.5 bg-surface border border-border rounded-xl text-sm text-[#f0f0f5] hover:border-accent/30 hover:text-white transition-all duration-200"
						>{s}</button>
					{/each}
				</div>
			</div>
		{:else}
			{#each messages as msg, i}
				<div class="flex {msg.role === 'user' ? 'justify-end' : 'justify-start'}">
					<div class="max-w-[88%] sm:max-w-[82%] md:max-w-[78%] lg:max-w-[72%] group relative
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
								class="absolute -top-2 -right-2 p-1.5 bg-surface-hover border border-border rounded-lg opacity-0 group-hover:opacity-100 transition-opacity text-[#8888a0] hover:text-white"
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
	<div class="shrink-0 p-[4%] pb-[calc(env(safe-area-inset-bottom)+1rem)]">
		<div class="bg-surface border border-border rounded-xl focus-within:border-accent/50 transition-colors">
			<textarea
				bind:value={question}
				onkeydown={handleKeydown}
				rows="2"
				placeholder="Ask anything about the WBC..."
				disabled={loading}
				class="w-full bg-transparent px-4 pt-3 pb-1 text-sm text-white placeholder-[#555570] resize-none focus:outline-none focus:ring-0 disabled:opacity-50"
				style="outline: none !important; box-shadow: none !important;"
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
</div>
{/if}

<!-- Floating toggle button -->
<button
	type="button"
	onclick={() => open = !open}
	class="fixed bottom-[3%] right-[3%] z-30 w-[clamp(48px,6vw,64px)] h-[clamp(48px,6vw,64px)] rounded-full bg-accent text-white shadow-lg shadow-accent/30 hover:bg-accent-hover hover:scale-105 transition-all duration-200 flex items-center justify-center"
	title="Toggle AI Chat"
>
	<MessageCircle class="w-[clamp(20px,3vw,28px)] h-[clamp(20px,3vw,28px)]" style="transform: scaleX(-1);" />
</button>

<style>
@keyframes slide-in {
	from {
		transform: translateX(100%);
	}
	to {
		transform: translateX(0);
	}
}
.animate-slide-in {
	animation: slide-in 0.2s ease-out;
}
</style>