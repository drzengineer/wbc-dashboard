<script lang="ts">
import type { GameDetailRow } from "$lib/types";
import { formatIP, formatPct } from "$lib/utils";

let { pitchers }: { pitchers: GameDetailRow[] } = $props();
</script>

<table class="w-full text-sm sm:text-base min-w-max">
  <thead class="bg-zinc-950/50">
  <tr class="border-b border-zinc-800 text-zinc-400 uppercase tracking-wider text-xs sm:text-sm font-medium">
    <th class="text-left py-3 px-4 w-[200px] sticky-column bg-[#111113]">Pitcher</th>
    <th class="text-center py-3 px-2 w-10">IP</th>
    <th class="text-center py-3 px-2 w-10">H</th>
    <th class="text-center py-3 px-2 w-10">R</th>
    <th class="text-center py-3 px-2 w-10">ER</th>
    <th class="text-center py-3 px-2 w-10">BB</th>
    <th class="text-center py-3 px-2 w-10">K</th>
    <th class="text-center py-3 px-2 w-10">HBP</th>
    <th class="text-center py-3 px-2 w-10">WP</th>
    <th class="text-center py-3 px-2 w-10">Pit</th>
    <th class="text-center py-3 px-2 w-10">Str%</th>
    <th class="text-center py-3 px-2 w-10">BF</th>
  </tr>
</thead>
<tbody>
  {#each pitchers as p}
  <tr class="border-b border-zinc-800/50 hover:bg-zinc-800/20">
    <td class="py-2.5 px-4 text-white font-semibold flex items-center gap-3 sticky-column bg-zinc-900">
      <span class="truncate">
        {p.boxscore_name ?? p.full_name ?? '—'}
      </span>
      <span class="text-xs ml-1.5 flex gap-1">
        {#if p.player_pitching_wins}<span class="text-zinc-400 font-bold">W</span>{/if}
        {#if p.player_pitching_losses}<span class="text-zinc-400 font-bold">L</span>{/if}
        {#if p.player_pitching_saves}<span class="text-zinc-400 font-bold">Sv</span>{/if}
        {#if p.player_pitching_holds}<span class="text-zinc-400 font-bold">H</span>{/if}
        {#if p.player_pitching_bs}<span class="text-zinc-400 font-bold">BS</span>{/if}
        {#if p.player_pitching_gs}<span class="text-zinc-500 font-normal">(GS)</span>{/if}
      </span>
    </td>
    <td class="text-center py-2.5 px-2 text-zinc-200 font-mono">{formatIP(p.player_pitching_outs)}</td>
    <td class="text-center py-2.5 px-2 text-zinc-300">{p.player_pitching_hits_allowed ?? 0}</td>
    <td class="text-center py-2.5 px-2 text-zinc-300">{p.player_pitching_runs_allowed ?? 0}</td>
    <td class="text-center py-2.5 px-2 text-zinc-300">{p.player_pitching_er ?? 0}</td>
    <td class="text-center py-2.5 px-2 text-zinc-300">{p.player_pitching_bb ?? 0}</td>
    <td class="text-center py-2.5 px-2 text-zinc-300">{p.player_pitching_so ?? 0}</td>
    <td class="text-center py-2.5 px-2 text-zinc-300">{p.player_pitching_hbp ?? 0}</td>
    <td class="text-center py-2.5 px-2 text-zinc-300">{p.player_pitching_wp ?? 0}</td>
    <td class="text-center py-2.5 px-2 text-zinc-400">{p.player_pitching_total_pitches ?? 0}</td>
    <td class="text-center py-2.5 px-2 text-zinc-400">{formatPct(p.player_pitching_strikes, p.player_pitching_total_pitches)}</td>
    <td class="text-center py-2.5 px-2 text-zinc-500">{p.player_pitching_bf ?? 0}</td>
  </tr>
  {/each}
  </tbody>
</table>
