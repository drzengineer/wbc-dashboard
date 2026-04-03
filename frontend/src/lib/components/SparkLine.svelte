<script lang="ts">
let {
	data,
	width = 80,
	height = 24,
	color = "#3b82f6",
	fillOpacity = 0.1,
}: {
	data: number[];
	width?: number;
	height?: number;
	color?: string;
	fillOpacity?: number;
} = $props();

const padding = 2;

let points = $derived(() => {
	if (data.length < 2) return "";
	const min = Math.min(...data);
	const max = Math.max(...data);
	const range = max - min || 1;
	const innerW = width - padding * 2;
	const innerH = height - padding * 2;

	return data
		.map((v, i) => {
			const x = padding + (i / (data.length - 1)) * innerW;
			const y = padding + innerH - ((v - min) / range) * innerH;
			return `${x},${y}`;
		})
		.join(" ");
});

let areaPoints = $derived(() => {
	if (data.length < 2) return "";
	const line = points();
	const startX = padding;
	const endX = width - padding;
	return `${startX},${height} ${line} ${endX},${height}`;
});
</script>

{#if data.length >= 2}
	<svg {width} {height} viewBox="0 0 {width} {height}" role="img" aria-label="Spark line chart">
		<defs>
			<linearGradient id="spark-fill" x1="0" y1="0" x2="0" y2="1">
				<stop offset="0%" stop-color={color} stop-opacity={fillOpacity} />
				<stop offset="100%" stop-color={color} stop-opacity="0" />
			</linearGradient>
		</defs>
		<polygon
			points={areaPoints()}
			fill="url(#spark-fill)"
		/>
		<polyline
			points={points()}
			fill="none"
			stroke={color}
			stroke-width="1.5"
			stroke-linecap="round"
			stroke-linejoin="round"
		/>
	</svg>
{/if}