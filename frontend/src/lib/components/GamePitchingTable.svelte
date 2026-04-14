<script lang="ts">
import type { GameDetailRow } from "$lib/types";
import { formatIP, formatPct } from "$lib/utils";

let { pitchers }: { pitchers: GameDetailRow[] } = $props();
</script>

<table class="gdt-table">
  <thead>
  <tr>
    <th class="text-left px-4 w-50 sticky-column">Pitcher</th>
    <th class="w-10">IP</th>
    <th class="w-10">H</th>
    <th class="w-10">R</th>
    <th class="w-10">ER</th>
    <th class="w-10">BB</th>
    <th class="w-10">K</th>
    <th class="w-10">HBP</th>
    <th class="w-10">WP</th>
    <th class="w-10">Pit</th>
    <th class="w-10">Str%</th>
    <th class="w-10">BF</th>
  </tr>
</thead>
<tbody>
  {#each pitchers as p}
  <tr>
    <td class="px-4 text-white font-semibold sticky-column bg-[#111113]">
      <div class="flex items-center gap-3">
        <a href="/players/{p.player_id}" class="font-medium text-white hover:text-accent transition-colors truncate">
          {p.boxscore_name ?? p.full_name ?? '—'}
        </a>
        <span class="text-xs ml-1.5 flex gap-1">
          {#if p.player_pitching_wins}<span class="text-zinc-400 font-bold">W</span>{/if}
          {#if p.player_pitching_losses}<span class="text-zinc-400 font-bold">L</span>{/if}
          {#if p.player_pitching_saves}<span class="text-zinc-400 font-bold">Sv</span>{/if}
          {#if p.player_pitching_holds}<span class="text-zinc-400 font-bold">H</span>{/if}
          {#if p.player_pitching_bs}<span class="text-zinc-400 font-bold">BS</span>{/if}
          {#if p.player_pitching_gs}<span class="text-zinc-500 font-normal">(GS)</span>{/if}
        </span>
      </div>
    </td>
    <td class="text-zinc-200 font-mono">{formatIP(p.player_pitching_outs)}</td>
    <td>{p.player_pitching_hits_allowed ?? 0}</td>
    <td>{p.player_pitching_runs_allowed ?? 0}</td>
    <td>{p.player_pitching_er ?? 0}</td>
    <td>{p.player_pitching_bb ?? 0}</td>
    <td>{p.player_pitching_so ?? 0}</td>
    <td>{p.player_pitching_hbp ?? 0}</td>
    <td>{p.player_pitching_wp ?? 0}</td>
    <td class="text-zinc-400">{p.player_pitching_total_pitches ?? 0}</td>
    <td class="text-zinc-400">{formatPct(p.player_pitching_strikes, p.player_pitching_total_pitches)}</td>
    <td class="text-zinc-500">{p.player_pitching_bf ?? 0}</td>
  </tr>
  {/each}
  </tbody>
</table>
