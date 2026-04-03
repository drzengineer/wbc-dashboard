<script lang="ts">
import "../app.css";
import { Calendar, Home, Menu, MessageCircle, Users, X } from "lucide-svelte";
import { page } from "$app/state";

const { children } = $props();

let mobileNavOpen = $state(false);

const navLinks = [
	{ href: "/", label: "Dashboard", icon: Home },
	{ href: "/games", label: "Games", icon: Calendar },
	{ href: "/players", label: "Players", icon: Users },
	{ href: "/chat", label: "AI Chat", icon: MessageCircle },
];

function isActive(href: string) {
	if (href === "/") return page.url.pathname === "/";
	return page.url.pathname.startsWith(href);
}

function closeNav() {
	mobileNavOpen = false;
}
</script>

<!-- Mobile header -->
<header class="md:hidden fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-4 py-3 bg-[#0a0a0f]/95 backdrop-blur-sm border-b border-border">
	<div class="flex items-center gap-2">
		<span class="text-lg font-bold tracking-tight text-white">WBC</span>
		<span class="text-lg font-bold tracking-tight text-accent">Dashboard</span>
	</div>
	<button
		type="button"
		onclick={() => mobileNavOpen = !mobileNavOpen}
		class="p-2 rounded-lg text-[#8888a0] hover:text-white hover:bg-surface-hover transition-colors"
		aria-label="Toggle menu"
	>
		{#if mobileNavOpen}
			<X class="w-5 h-5" />
		{:else}
			<Menu class="w-5 h-5" />
		{/if}
	</button>
</header>

<!-- Mobile drawer overlay -->
{#if mobileNavOpen}
	<div
		class="md:hidden fixed inset-0 z-40 bg-black/60 backdrop-blur-sm"
		onclick={closeNav}
		role="presentation"
	></div>
	<nav class="md:hidden fixed top-13 left-0 bottom-0 z-40 w-56 bg-[#0a0a0f] border-r border-border flex flex-col py-4 px-3 gap-1 shadow-2xl animate-fade-in">
		{#each navLinks as link}
			<a
				href={link.href}
				onclick={closeNav}
				class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200
					{isActive(link.href)
						? 'bg-accent text-white shadow-lg shadow-accent/20'
						: 'text-[#8888a0] hover:text-white hover:bg-surface-hover'}"
			>
				<link.icon class="w-4 h-4" />
				<span>{link.label}</span>
			</a>
		{/each}
	</nav>
{/if}

<!-- Desktop layout -->
<div class="flex min-h-screen bg-[#0a0a0f] text-[#f0f0f5]">
	<!-- Desktop sidebar -->
	<aside class="hidden md:flex w-56 shrink-0 border-r border-border flex-col py-6 px-3 gap-1 sticky top-0 h-screen">
		<div class="mb-6 px-3">
			<span class="text-xl font-bold tracking-tight text-white">WBC</span>
			<span class="text-xl font-bold tracking-tight text-accent"> Dashboard</span>
		</div>
		{#each navLinks as link}
			<a
				href={link.href}
				class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200
					{isActive(link.href)
						? 'bg-accent text-white shadow-lg shadow-accent/20'
						: 'text-[#8888a0] hover:text-white hover:bg-surface-hover'}"
			>
				<link.icon class="w-4 h-4" />
				<span>{link.label}</span>
			</a>
		{/each}
	</aside>

	<!-- Main content -->
	<main class="flex-1 min-w-0 overflow-y-auto p-4 md:p-8 pt-17 md:pt-8">
		{@render children()}
	</main>
</div>