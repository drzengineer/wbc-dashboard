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

<table class="gdt-table">
  <thead>
    <tr>
      <th class="text-left px-4 w-30 sticky-column">Team</th>
      {#each stats as s}
        <th class="w-10">{s.l}</th>
      {/each}
    </tr>
  </thead>
  <tbody>
    <tr>
      <td class="px-4 font-semibold sticky-column bg-[#111113]">
        <div class="flex items-center gap-3">
          <Flag country={awayAbbr} size="md" />
          {awayAbbr}
        </div>
      </td>
      {#each stats as s}
        <td>{s.aS ?? s.a}</td>
      {/each}
    </tr>
    <tr>
      <td class="px-4 font-semibold sticky-column bg-[#111113]">
        <div class="flex items-center gap-3">
          <Flag country={homeAbbr} size="md" />
          {homeAbbr}
        </div>
      </td>
      {#each stats as s}
        <td>{s.hS ?? s.h}</td>
      {/each}
    </tr>
  </tbody>
</table>
