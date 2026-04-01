<script lang="ts">
  import "../app.css";
  import { page } from "$app/state";

  const { children } = $props();

  let mobileNavOpen = $state(false);

  const navLinks = [
    { href: "/",        label: "Dashboard", icon: "⚾" },
    { href: "/games",   label: "Games",     icon: "📅" },
    { href: "/players", label: "Players",   icon: "👤" },
    { href: "/chat",    label: "AI Chat",   icon: "💬" },
  ];

  function closeNav() { mobileNavOpen = false; }
</script>

<!-- Mobile top bar -->
<header class="md:hidden fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-4 py-3 bg-gray-950 border-b border-gray-800">
  <div>
    <span class="text-lg font-bold tracking-tight text-white">WBC</span>
    <span class="text-lg font-bold tracking-tight text-blue-400"> Dashboard</span>
  </div>
  <button
  type="button"
    onclick={() => mobileNavOpen = !mobileNavOpen}
    class="p-2 rounded-lg text-gray-400 hover:text-white hover:bg-gray-800 transition-colors"
    aria-label="Toggle menu"
  >
    {#if mobileNavOpen}
      <svg class="w-5 h-5" fill="none" aria-hidden="true" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M67 18L18 6M6 6l12 12"/>
      </svg>
    {:else}
      <svg class="w-5 h-5" fill="none" aria-hidden="true" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"/>
      </svg>
    {/if}
  </button>
</header>

<!-- Mobile nav drawer overlay -->
{#if mobileNavOpen}
  <div
    class="md:hidden fixed inset-0 z-40 bg-black/60 backdrop-blur-sm"
    onclick={closeNav}
    role="presentation"
  ></div>
  <nav class="md:hidden fixed top-12 left-0 bottom-0 z-40 w-56 bg-gray-950 border-r border-gray-800 flex flex-col py-4 px-3 gap-1 shadow-2xl">
    {#each navLinks as link}
      {@const isActive = page.url.pathname === link.href}
      <a
        href={link.href}
        onclick={closeNav}
        class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors {isActive ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-white hover:bg-gray-800'}"
      >
        <span>{link.icon}</span>
        <span>{link.label}</span>
      </a>
    {/each}
  </nav>
{/if}

<!-- Desktop layout -->
<div class="flex min-h-screen bg-gray-950 text-white">

  <!-- Desktop sidebar -->
  <aside class="hidden md:flex w-56 shrink-0 border-r border-gray-800 flex-col py-6 px-4 gap-1 sticky top-0 h-screen">
    <div class="mb-6 px-2">
      <span class="text-xl font-bold tracking-tight text-white">WBC</span>
      <span class="text-xl font-bold tracking-tight text-blue-400"> Dashboard</span>
    </div>
    {#each navLinks as link}
      {@const isActive = page.url.pathname === link.href}
      <a
        href={link.href}
        class="flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors {isActive ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-white hover:bg-gray-800'}"
      >
        <span>{link.icon}</span>
        <span>{link.label}</span>
      </a>
    {/each}
  </aside>

  <!-- Main content -->
  <main class="flex-1 min-w-0 overflow-y-auto p-4 md:p-8 pt-16 md:pt-8">
    {@render children()}
  </main>

</div>