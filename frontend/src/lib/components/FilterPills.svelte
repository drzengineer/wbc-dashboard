<script lang="ts">
let {
	items,
	selected,
	onSelect,
	showAll = true,
}: {
	items: string[];
	selected: string;
	onSelect: (item: string) => void;
	showAll?: boolean;
} = $props();
</script>

<div class="flex flex-wrap gap-2 items-center">
	{#if showAll}
		<button
			type="button"
			onclick={() => onSelect('All')}
			class="px-3 py-1 rounded-full text-xs font-medium border transition-all duration-200
				{selected === 'All'
					? 'bg-accent border-accent text-white'
					: 'border-border-light text-[#8888a0] hover:text-white hover:border-[#555570]'}"
		>
			All
		</button>
	{/if}
	{#each items as item}
		<button
			type="button"
			onclick={() => onSelect(item)}
			class="px-3 py-1 rounded-full text-xs font-medium border transition-all duration-200
				{selected === item
					? 'bg-accent border-accent text-white'
					: 'border-border-light text-[#8888a0] hover:text-white hover:border-[#555570]'}"
		>
			{item}
		</button>
	{/each}
</div>