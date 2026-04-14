<script lang="ts">
import Flag from "$lib/components/Flag.svelte";
import type { GameSummary } from "$lib/types";

let { game }: { game: GameSummary } = $props();
</script>

<table class="w-full text-sm sm:text-base min-w-max">
  <thead class="bg-zinc-950/50 text-zinc-400 uppercase tracking-wider text-xs sm:text-sm font-medium">
    <tr class="border-b border-zinc-800">
      <th class="text-left py-3 px-4 w-30 sticky-column bg-[#111113]">Team</th>
      {#each game.away_innings as _, i}
        <th class="text-center py-3 px-3 w-9">{i + 1}</th>
      {/each}
      <th class="text-center py-3 px-3 w-12 text-white">R</th>
      <th class="text-center py-3 px-3 w-12 text-white">H</th>
      <th class="text-center py-3 px-3 w-12 text-white">E</th>
    </tr>
  </thead>
  <tbody>
    <tr class="border-b border-zinc-800/50">
      <td class="py-2.5 px-4 font-semibold flex items-center gap-3 sticky-column bg-zinc-900">
        <Flag country={game.away_team_abbreviation} size="md" />
        {game.away_team_abbreviation}
      </td>
      {#each game.away_innings as run}
        <td class="text-center py-2.5 px-3 text-zinc-300">{run ?? '-'}</td>
      {/each}
      <td class="text-center py-2.5 px-3 font-bold text-white">{game.away_r}</td>
      <td class="text-center py-2.5 px-3 text-white">{game.away_h}</td>
      <td class="text-center py-2.5 px-3 text-white">{game.away_e}</td>
    </tr>
    <tr>
      <td class="py-2.5 px-4 font-semibold flex items-center gap-3 sticky-column bg-zinc-900">
        <Flag country={game.home_team_abbreviation} size="md" />
        {game.home_team_abbreviation}
      </td>
      {#each game.home_innings as run}
        <td class="text-center py-2.5 px-3 text-zinc-300">{run ?? '-'}</td>
      {/each}
      <td class="text-center py-2.5 px-3 font-bold text-white">{game.home_r}</td>
      <td class="text-center py-2.5 px-3 text-white">{game.home_h}</td>
      <td class="text-center py-2.5 px-3 text-white">{game.home_e}</td>
    </tr>
  </tbody>
</table>
