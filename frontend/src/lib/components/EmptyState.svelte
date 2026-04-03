<script lang="ts">
import { Inbox } from "lucide-svelte";

let {
	title = "No data",
	description = "",
	icon = true,
}: {
	title?: string;
	description?: string;
	icon?: boolean;
} = $props();
</script>

<div class="bg-surface border border-border rounded-xl px-6 py-12 text-center">
	{#if icon}
		<div class="flex justify-center mb-4">
			<Inbox class="w-8 h-8 text-[#555570]" />
		</div>
	{/if}
	<p class="text-[#8888a0] text-sm font-medium">{title}</p>
	{#if description}
		<p class="text-[#555570] text-xs mt-1">{description}</p>
	{/if}
</div>