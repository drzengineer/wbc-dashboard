<script lang="ts">
  import { ChevronDown, ChevronRight } from "lucide-svelte";

  // ─── Props ────────────────────────────────────────────────────────────────────
  let { title, expanded, onToggle, children }: {
    title: string;
    expanded: boolean;
    onToggle: () => void;
    children: any;
  } = $props();
</script>

<style>
  /* Fix for Chromium sticky table border bug - pseudo-element divider that actually works */
  :global(.sticky-column) {
    position: sticky;
    left: 0;
    z-index: 10;
    transform: translateZ(0);
    will-change: transform;
  }
  :global(.sticky-column::after) {
    content: '';
    position: absolute;
    top: 0;
    right: 0;
    height: 100%;
    width: 1px;
    background-color: rgb(63 63 70 / 0.5);
    pointer-events: none;
    z-index: 1;
  }
</style>

<section class="border-b border-border">
  <button onclick={onToggle}
    class="w-full flex items-center justify-between px-6 py-4 hover:bg-zinc-800/40 transition-colors text-base">
    <span class="flex items-center gap-2.5 font-medium text-white">
      {title}
    </span>
    {#if expanded}<ChevronDown class="w-5 h-5 text-zinc-500" />
    {:else}<ChevronRight class="w-5 h-5 text-zinc-500" />{/if}
  </button>

  {#if expanded}
  <div class="px-6 pb-6">
    <div class="rounded-xl overflow-hidden bg-zinc-900 border border-zinc-800">
      <div class="overflow-x-auto [&::-webkit-overflow-scrolling:touch] relative isolate">
        {@render children()}
      </div>
    </div>
  </div>
  {/if}
</section>
