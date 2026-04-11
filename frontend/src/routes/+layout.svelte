<script lang="ts">
	import "../app.css";
	import { Calendar, Home, Users } from "lucide-svelte";
	import { page } from "$app/state";
	import AIChat from "$lib/components/AIChat.svelte";

	const { children } = $props();

	const navLinks = [
		{ href: "/", label: "Dashboard", icon: Home },
		{ href: "/games", label: "Games", icon: Calendar },
		{ href: "/players", label: "Players", icon: Users },
	];

	function isActive(href: string) {
		if (href === "/") return page.url.pathname === "/";
		return page.url.pathname.startsWith(href);
	}
</script>

<!-- Permanent Top Navbar -->
<header class="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-6 py-4 bg-[#0a0a0f]/95 backdrop-blur-sm border-b border-border max-md:px-4">
	<div class="flex items-center gap-2">
		<span class="text-lg font-bold tracking-tight text-white">WBC</span>
		<span class="text-lg font-bold tracking-tight text-accent">Dashboard</span>
	</div>

	<nav class="flex items-center gap-1">
		{#each navLinks as link}
			<a
				href={link.href}
				class="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200
					{isActive(link.href)
						? 'bg-accent text-white shadow-lg shadow-accent/20'
						: 'text-[#8888a0] hover:text-white hover:bg-surface-hover'}
					max-md:px-3 max-md:gap-0"
			>
				<link.icon class="w-4 h-4" />
				<span class="max-md:hidden">{link.label}</span>
			</a>
		{/each}
	</nav>
</header>

<!-- Main content -->
<div class="min-h-screen bg-[#0a0a0f] text-[#f0f0f5] pt-18">
	<main class="p-8">
		{@render children()}
	</main>
</div>

<AIChat />