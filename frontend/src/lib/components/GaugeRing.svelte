<script lang="ts">
import { onMount } from "svelte";

let {
	value,
	max = 1,
	size = 100,
	strokeWidth = 8,
	label = "",
	color = "#3b82f6",
	formatValue = (v: number) => String(v),
}: {
	value: number;
	max?: number;
	size?: number;
	strokeWidth?: number;
	label?: string;
	color?: string;
	formatValue?: (v: number) => string;
} = $props();

let visible = $state(false);
let containerEl: HTMLDivElement | null = $state(null);

const center = $derived(size / 2);
const radius = $derived(size / 2 - strokeWidth);
const circumference = $derived(2 * Math.PI * radius);
const pct = $derived(Math.min(value / max, 1));
const dashOffset = $derived(circumference * (1 - pct));

onMount(() => {
	if (!containerEl) return;
	const io = new IntersectionObserver(
		([entry]) => {
			if (entry.isIntersecting) {
				visible = true;
				io.disconnect();
			}
		},
		{ threshold: 0.3 },
	);
	io.observe(containerEl);
	return () => io.disconnect();
});
</script>

<div bind:this={containerEl} class="flex flex-col items-center gap-2">
	<div class="relative" style="width: {size}px; height: {size}px;">
		<svg
			width={size}
			height={size}
			viewBox="0 0 {size} {size}"
			class="transform -rotate-90"
			role="img"
			aria-label="{label}: {formatValue(value)}"
		>
			<defs>
				<filter id="gauge-glow-{size}">
					<feGaussianBlur in="SourceGraphic" stdDeviation="2" />
				</filter>
			</defs>

			<!-- Background track -->
			<circle
				cx={center}
				cy={center}
				r={radius}
				fill="none"
				stroke="#1e1e2e"
				stroke-width={strokeWidth}
			/>

			<!-- Glow layer -->
			{#if visible}
				<circle
					cx={center}
					cy={center}
					r={radius}
					fill="none"
					stroke={color}
					stroke-width={strokeWidth + 4}
					stroke-linecap="round"
					stroke-dasharray={circumference}
					stroke-dashoffset={visible ? dashOffset : circumference}
					opacity="0.3"
					filter="url(#gauge-glow-{size})"
					style="transition: stroke-dashoffset 1.2s ease-out;"
				/>
			{/if}

			<!-- Value arc -->
			{#if visible}
				<circle
					cx={center}
					cy={center}
					r={radius}
					fill="none"
					stroke={color}
					stroke-width={strokeWidth}
					stroke-linecap="round"
					stroke-dasharray={circumference}
					stroke-dashoffset={visible ? dashOffset : circumference}
					style="transition: stroke-dashoffset 1.2s ease-out;"
				/>
			{/if}
		</svg>

		<!-- Center text -->
		<div class="absolute inset-0 flex flex-col items-center justify-center">
			<span class="text-lg font-bold tabular-nums text-white">{formatValue(value)}</span>
		</div>
	</div>

	{#if label}
		<span class="text-xs text-[#8888a0] font-medium">{label}</span>
	{/if}
</div>