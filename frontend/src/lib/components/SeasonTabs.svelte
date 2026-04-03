<script lang="ts">
let {
	seasons,
	selected,
	onSelect,
}: {
	seasons: (string | number)[];
	selected: string | number;
	onSelect: (season: string | number) => void;
} = $props();
</script>

<div class="flex gap-1 bg-surface border border-border rounded-lg p-1 w-fit">
	{#each seasons as season}
		<button
			type="button"
			onclick={() => onSelect(season)}
			class="px-3 py-1.5 rounded-md text-sm font-medium transition-all duration-200
				{selected === season
					? 'bg-accent text-white shadow-lg shadow-accent/20'
					: 'text-[#8888a0] hover:text-white hover:bg-surface-hover'}"
		>
			{season}
		</button>
	{/each}
</div>