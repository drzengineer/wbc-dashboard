<script lang="ts">
import { onMount } from "svelte";

let {
	value,
	duration = 1200,
	label = "",
	color = "",
}: {
	value: number;
	duration?: number;
	label?: string;
	color?: string;
} = $props();

let displayValue = $state(0);
let containerEl: HTMLDivElement | null = $state(null);

let textColor = $derived(
	color === "gold"
		? "text-gold"
		: color === "success"
			? "text-success"
			: color === "accent"
				? "text-accent"
				: "text-white",
);

onMount(() => {
	if (!containerEl) return;
	const io = new IntersectionObserver(
		([entry]) => {
			if (entry.isIntersecting) {
				animate();
				io.disconnect();
			}
		},
		{ threshold: 0.3 },
	);
	io.observe(containerEl);
	return () => io.disconnect();
});

function animate() {
	const start = performance.now();
	const step = (now: number) => {
		const elapsed = now - start;
		const progress = Math.min(elapsed / duration, 1);
		// Ease out cubic
		const eased = 1 - (1 - progress) ** 3;
		displayValue = Math.round(eased * value);
		if (progress < 1) {
			requestAnimationFrame(step);
		}
	};
	requestAnimationFrame(step);
}
</script>

<div bind:this={containerEl} class="flex flex-col items-center">
	<span class="text-3xl md:text-4xl font-bold tabular-nums {textColor}">
		{displayValue.toLocaleString()}
	</span>
	{#if label}
		<span class="text-xs text-[#8888a0] font-medium mt-1">{label}</span>
	{/if}
</div>