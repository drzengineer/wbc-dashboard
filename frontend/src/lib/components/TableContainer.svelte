<script lang="ts">
  // ─── Props ────────────────────────────────────────────────────────────────────
  let { children }: {
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
    background-color: #111113 !important;
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

  /* Shared table base styles */
  :global(.gdt-table) {
    width: 100%;
    font-size: 0.875rem;
    min-width: max-content;
  }
  @media (min-width: 640px) {
    :global(.gdt-table) {
      font-size: 1rem;
    }
  }

  :global(.gdt-table thead) {
    background-color: rgba(9, 9, 11, 0.5);
  }

  :global(.gdt-table thead tr) {
    border-bottom: 1px solid #27272a;
  }

  :global(.gdt-table thead th) {
    color: #a1a1aa;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    font-size: 0.75rem;
    font-weight: 500;
    text-align: center;
    padding-top: 0.75rem;
    padding-bottom: 0.75rem;
    padding-left: 0.5rem;
    padding-right: 0.5rem;
  }
  @media (min-width: 640px) {
    :global(.gdt-table thead th) {
      font-size: 0.875rem;
    }
  }

  :global(.gdt-table tbody tr) {
    border-bottom: 1px solid rgba(39, 39, 42, 0.5);
  }

  :global(.gdt-table tbody tr:last-child) {
    border-bottom: none;
  }

  :global(.gdt-table tbody tr:hover) {
    background-color: rgba(39, 39, 42, 0.2);
  }

  :global(.gdt-table tbody td) {
    padding-top: 0.625rem;
    padding-bottom: 0.625rem;
    padding-left: 0.5rem;
    padding-right: 0.5rem;
    text-align: center;
    color: #d4d4d8;
  }
</style>

  <div class="rounded-xl overflow-hidden bg-zinc-900 border border-zinc-800">
    <div class="overflow-x-auto [&::-webkit-overflow-scrolling:touch] relative isolate">
      {@render children()}
    </div>
  </div>
