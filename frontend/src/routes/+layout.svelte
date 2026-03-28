<script lang="ts">
import "../app.css";
import { page } from "$app/state";

const { children } = $props();

const navLinks = [
	{ href: "/", label: "Dashboard", icon: "⚾" },
	{ href: "/games", label: "Games", icon: "📅" },
	{ href: "/players", label: "Players", icon: "👤" },
	{ href: "/chat", label: "AI Chat", icon: "💬" },
];
</script>

<div class="flex min-h-screen bg-gray-950 text-white">

  <!-- Sidebar -->
  <aside class="w-56 shrink-0 border-r border-gray-800 flex flex-col py-6 px-4 gap-1">

    <div class="mb-6 px-2">
      <span class="text-xl font-bold tracking-tight text-white">WBC</span>
      <span class="text-xl font-bold tracking-tight text-blue-400"> Dashboard</span>
    </div>

    {#each navLinks as link}
      {@const isActive = page.url.pathname === link.href}
      <a href={link.href}
        class="flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors {isActive ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-white hover:bg-gray-800'}"
      >
        	<span>{link.icon}</span>
        <span>{link.label}</span>
      </a>
    {/each}

  </aside>

  <!-- Main content -->
  <main class="flex-1 overflow-y-auto p-8">
    {@render children()}
  </main>

</div>