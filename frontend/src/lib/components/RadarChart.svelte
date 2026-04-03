<script lang="ts">
import { onMount } from "svelte";

interface RadarStat {
	label: string;
	value: number;
	max: number;
}

let {
	stats,
	size = 280,
	color = "#3b82f6",
	fillOpacity = 0.15,
}: {
	stats: RadarStat[];
	size?: number;
	color?: string;
	fillOpacity?: number;
} = $props();

let visible = $state(false);
let containerEl: HTMLDivElement | null = $state(null);

const center = $derived(size / 2);
const radius = $derived(size / 2 - 40);
const levels = 5;

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

function getPoint(index: number, value: number, max: number) {
	const angle = (Math.PI * 2 * index) / stats.length - Math.PI / 2;
	const r = (value / max) * radius;
	return {
		x: center + r * Math.cos(angle),
		y: center + r * Math.sin(angle),
	};
}

function getGridPoint(index: number, level: number) {
	const angle = (Math.PI * 2 * index) / stats.length - Math.PI / 2;
	const r = (level / levels) * radius;
	return {
		x: center + r * Math.cos(angle),
		y: center + r * Math.sin(angle),
	};
}

let polygonPoints = $derived(
	stats
		.map((s, i) => {
			const p = getPoint(i, s.value, s.max);
			return `${p.x},${p.y}`;
		})
		.join(" "),
);

let gridPolygons = $derived(
	Array.from({ length: levels }, (_, level) => {
		const l = level + 1;
		return stats
			.map((_, i) => {
				const p = getGridPoint(i, l);
				return `${p.x},${p.y}`;
			})
			.join(" ");
	}),
);

let axisLines = $derived(
	stats.map((_, i) => {
		const p = getGridPoint(i, levels);
		return { x1: center, y1: center, x2: p.x, y2: p.y };
	}),
);

let labelPositions = $derived(
	stats.map((s, i) => {
		const angle = (Math.PI * 2 * i) / stats.length - Math.PI / 2;
		const r = radius + 28;
		return {
			x: center + r * Math.cos(angle),
			y: center + r * Math.sin(angle),
			label: s.label,
			value: s.value,
		};
	}),
);
</script>

<div bind:this={containerEl} class="flex justify-center pb-5">
	<svg
		width={size}
		height={size}
		viewBox="0 0 {size} {size + 20}"
		class="transition-opacity duration-700 {visible ? 'opacity-100' : 'opacity-0'}"
		role="img"
		aria-label="Radar chart showing player stats"
	>
		<defs>
			<radialGradient id="radar-glow" cx="50%" cy="50%" r="50%">
				<stop offset="0%" stop-color={color} stop-opacity="0.3" />
				<stop offset="100%" stop-color={color} stop-opacity="0" />
			</radialGradient>
			<filter id="radar-blur">
				<feGaussianBlur in="SourceGraphic" stdDeviation="3" />
			</filter>
		</defs>

		<!-- Grid -->
		{#each gridPolygons as points}
			<polygon
				{points}
				fill="none"
				stroke="#2a2a3a"
				stroke-width="0.5"
			/>
		{/each}

		<!-- Axis lines -->
		{#each axisLines as line}
			<line
				x1={line.x1}
				y1={line.y1}
				x2={line.x2}
				y2={line.y2}
				stroke="#2a2a3a"
				stroke-width="0.5"
			/>
		{/each}

		<!-- Glow layer -->
		{#if visible}
			<polygon
				points={polygonPoints}
				fill="url(#radar-glow)"
				filter="url(#radar-blur)"
				style="transition: all 1s ease-out;"
			/>
		{/if}

		<!-- Data polygon -->
		{#if visible}
			<polygon
				points={polygonPoints}
				fill={color}
				fill-opacity={fillOpacity}
				stroke={color}
				stroke-width="2"
				stroke-linejoin="round"
				style="transition: all 1s ease-out;"
			/>
		{/if}

		<!-- Labels -->
		{#each labelPositions as lp}
			<text
				x={lp.x}
				y={lp.y}
				text-anchor="middle"
				dominant-baseline="middle"
				class="fill-[#8888a0] text-[10px] font-medium"
			>
				{lp.label}
			</text>
			<text
				x={lp.x}
				y={lp.y + 13}
				text-anchor="middle"
				dominant-baseline="middle"
				class="fill-white text-[11px] font-bold tabular-nums"
			>
				{lp.value}
			</text>
		{/each}
	</svg>
</div>