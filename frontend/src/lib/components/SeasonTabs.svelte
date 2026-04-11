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

<div class="flex gap-1 bg-surface border border-border rounded-lg p-1 w-full overflow-x-auto [&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] [scrollbar-width:none]">
	{#each seasons as season}
		<button
			type="button"
			onclick={() => onSelect(season)}
			class="flex-1 shrink min-w-0 px-3 py-1.5 rounded-md text-sm font-medium transition-all duration-200
				{selected === season
					? 'bg-accent text-white shadow-lg shadow-accent/20'
					: 'text-[#8888a0] hover:text-white hover:bg-surface-hover'}
				max-md:px-2 max-md:py-1"
		>
			{season}
		</button>
	{/each}
</div>
