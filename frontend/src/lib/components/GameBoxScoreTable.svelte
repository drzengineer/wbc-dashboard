<script lang="ts">
import Flag from "$lib/components/Flag.svelte";
import GameDetailTableSection from "$lib/components/GameDetailTableSection.svelte";
import type { GameSummary } from "$lib/types";

let { game }: { game: GameSummary } = $props();
</script>

<GameDetailTableSection>
<table class="gdt-table">
  <thead>
    <tr>
      <th class="text-left px-4 w-30 sticky-column">Team</th>
      {#each game.away_innings as _, i}
        <th class="w-9">{i + 1}</th>
      {/each}
      <th class="w-12 text-white">R</th>
      <th class="w-12 text-white">H</th>
      <th class="w-12 text-white">E</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td class="px-4 font-semibold flex items-center gap-3 sticky-column bg-[#111113]">
        <Flag country={game.away_team_abbreviation} size="md" />
        {game.away_team_abbreviation}
      </td>
      {#each game.away_innings as run}
        <td>{run ?? '-'}</td>
      {/each}
      <td class="font-bold text-white">{game.away_r}</td>
      <td class="text-white">{game.away_h}</td>
      <td class="text-white">{game.away_e}</td>
    </tr>
    <tr>
      <td class="px-4 font-semibold flex items-center gap-3 sticky-column bg-[#111113]">
        <Flag country={game.home_team_abbreviation} size="md" />
        {game.home_team_abbreviation}
      </td>
      {#each game.home_innings as run}
        <td>{run ?? '-'}</td>
      {/each}
      <td class="font-bold text-white">{game.home_r}</td>
      <td class="text-white">{game.home_h}</td>
      <td class="text-white">{game.home_e}</td>
    </tr>
  </tbody>
</table>
</GameDetailTableSection>
