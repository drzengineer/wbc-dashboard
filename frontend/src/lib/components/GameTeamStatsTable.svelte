<script lang="ts">
import Flag from "$lib/components/Flag.svelte";

interface StatRow {
  l: string;
  a: number | string;
  h: number | string;
  aS?: string;
  hS?: string;
}

let { stats, awayAbbr, homeAbbr }: { 
  stats: StatRow[]; 
  awayAbbr: string; 
  homeAbbr: string;
} = $props();
</script>

<table class="w-full text-sm sm:text-base min-w-max table-fixed">
  <thead class="bg-zinc-950/50 text-zinc-400 uppercase tracking-wider text-xs sm:text-sm font-medium">
    <tr class="border-b border-zinc-800">
      <th class="text-left py-3 px-4 w-30 sticky-column bg-[#111113]">Team</th>
      {#each stats as s}
        <th class="text-center py-3 px-2 w-10">{s.l}</th>
      {/each}
    </tr>
  </thead>
  <tbody>
    <tr class="border-b border-zinc-800/50 hover:bg-zinc-800/20">
      <td class="py-2.5 px-4 font-semibold flex items-center gap-3 sticky-column bg-zinc-900">
        <Flag country={awayAbbr} size="md" />
        {awayAbbr}
      </td>
      {#each stats as s}
        <td class="text-center py-2.5 px-2 text-zinc-300">{s.aS ?? s.a}</td>
      {/each}
    </tr>
    <tr class="hover:bg-zinc-800/20">
      <td class="py-2.5 px-4 font-semibold flex items-center gap-3 sticky-column bg-zinc-900">
        <Flag country={homeAbbr} size="md" />
        {homeAbbr}
      </td>
      {#each stats as s}
        <td class="text-center py-2.5 px-2 text-zinc-300">{s.hS ?? s.h}</td>
      {/each}
    </tr>
  </tbody>
</table>
