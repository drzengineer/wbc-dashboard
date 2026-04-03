<script lang="ts">
let {
	label,
	value,
	color = "",
	sublabel = "",
}: {
	label: string;
	value: string | number;
	color?: string;
	sublabel?: string;
} = $props();

let textColor = $derived(
	color === "gold"
		? "text-gold"
		: color === "success"
			? "text-success"
			: color === "warning"
				? "text-warning"
				: color === "danger"
					? "text-danger"
					: color === "accent"
						? "text-accent"
						: "text-white",
);
</script>

<div class="bg-surface border border-border rounded-xl px-4 py-4 hover:border-border-light transition-colors duration-200">
	<p class="text-xs text-[#8888a0] uppercase tracking-wider mb-1.5 font-medium">{label}</p>
	<p class="text-2xl font-bold tabular-nums {textColor}">{value}</p>
	{#if sublabel}
		<p class="text-xs text-[#555570] mt-0.5">{sublabel}</p>
	{/if}
</div>