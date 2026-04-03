<script lang="ts">
let { size = "md" }: { size?: "sm" | "md" | "lg" } = $props();

let sizeClass = $derived(
	size === "sm"
		? "w-4 h-4 border-2"
		: size === "lg"
			? "w-8 h-8 border-2"
			: "w-5 h-5 border-2",
);
</script>

<div class="{sizeClass} border-accent border-t-transparent rounded-full animate-spin"></div>