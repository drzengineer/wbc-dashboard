<script lang="ts">
import { ChevronDown, ChevronRight } from "lucide-svelte";
import GameDetailTableSection from "$lib/components/GameDetailTableSection.svelte";
import type { GameDetailRow } from "$lib/types";

let { 
  players, 
  bench, 
  benchExpanded, 
  onToggleBench 
}: { 
  players: GameDetailRow[]; 
  bench: GameDetailRow[];
  benchExpanded: boolean;
  onToggleBench: () => void;
} = $props();
</script>

<GameDetailTableSection>
<table class="gdt-table">
<thead>
  <tr>
    <th class="text-left px-4 w-[200px] sticky-column">Player</th>
    <th class="w-10">AB</th>
    <th class="w-10">R</th>
    <th class="w-10">H</th>
    <th class="w-10">2B</th>
    <th class="w-10">3B</th>
    <th class="w-10">HR</th>
    <th class="w-10">RBI</th>
    <th class="w-10">BB</th>
    <th class="w-10">K</th>
    <th class="w-10">SB</th>
    <th class="w-10">HBP</th>
    <th class="w-10">TB</th>
  </tr>
</thead>
<tbody>
  {#each players as p}
  <tr>
    <td class="px-4 text-white font-semibold flex items-center gap-3 sticky-column bg-[#111113]">
      <span class="text-zinc-500 w-4 text-right shrink-0">{p.batting_order}</span>
      <span class="text-zinc-400 font-mono text-xs w-6 shrink-0">{p.primary_position_abbreviation ?? ''}</span>
      <span class="truncate">
        {p.boxscore_name ?? p.full_name ?? '—'}
        {#if p.is_substitute}<span class="text-zinc-500 text-[10px] sm:text-xs ml-1 font-normal">(sub)</span>{/if}
      </span>
    </td>
    <td>{p.player_batting_ab ?? 0}</td>
    <td>{p.player_batting_runs ?? 0}</td>
    <td>{p.player_batting_hits ?? 0}</td>
    <td>{p.player_batting_doubles ?? 0}</td>
    <td>{p.player_batting_triples ?? 0}</td>
    <td>{p.player_batting_hr ?? 0}</td>
    <td>{p.player_batting_rbi ?? 0}</td>
    <td>{p.player_batting_bb ?? 0}</td>
    <td>{p.player_batting_so ?? 0}</td>
    <td>{p.player_batting_sb ?? 0}</td>
    <td>{p.player_batting_hbp ?? 0}</td>
    <td class="text-zinc-400">{p.player_batting_tb ?? 0}</td>
  </tr>
  {/each}

  {#if bench.length > 0}
  <tr class="group">
    <td class="p-0 sticky-column bg-[#111113]">
      <button onclick={onToggleBench} class="w-full flex items-center py-3 px-4 text-xs font-semibold uppercase tracking-widest text-zinc-400 group-hover:bg-zinc-800/40 transition-colors bg-zinc-900/30">
        Bench Reserves ({bench.length})
      </button>
    </td>
    <td colspan="12" class="p-0 text-right">
      <button onclick={onToggleBench} class="w-full flex items-center justify-end py-3 px-4 text-zinc-400 group-hover:bg-zinc-800/40 transition-colors bg-zinc-900/30">
        {#if benchExpanded}<ChevronDown class="w-4 h-4" />{:else}<ChevronRight class="w-4 h-4" />{/if}
      </button>
    </td>
  </tr>
  {#if benchExpanded}
    {#each bench as p}
    <tr class="bg-zinc-900/20">
      <td class="px-4 text-zinc-400 font-medium flex items-center gap-3 sticky-column bg-[#111113]">
        <span class="text-zinc-600 w-4 text-right shrink-0">—</span>
        <span class="text-zinc-500 font-mono text-xs w-6 shrink-0">{p.primary_position_abbreviation ?? ''}</span>
        <span class="truncate">{p.boxscore_name ?? p.full_name ?? '—'}</span>
      </td>
      <td class="text-zinc-500">{p.player_batting_ab ?? 0}</td>
      <td class="text-zinc-500">{p.player_batting_runs ?? 0}</td>
      <td class="text-zinc-500">{p.player_batting_hits ?? 0}</td>
      <td class="text-zinc-500">{p.player_batting_doubles ?? 0}</td>
      <td class="text-zinc-500">{p.player_batting_triples ?? 0}</td>
      <td class="text-zinc-500">{p.player_batting_hr ?? 0}</td>
      <td class="text-zinc-500">{p.player_batting_rbi ?? 0}</td>
      <td class="text-zinc-500">{p.player_batting_bb ?? 0}</td>
      <td class="text-zinc-500">{p.player_batting_so ?? 0}</td>
      <td class="text-zinc-500">{p.player_batting_sb ?? 0}</td>
      <td class="text-zinc-500">{p.player_batting_hbp ?? 0}</td>
      <td class="text-zinc-500">{p.player_batting_tb ?? 0}</td>
    </tr>
    {/each}
  {/if}
  {/if}
</tbody>
</table>
</GameDetailTableSection>
