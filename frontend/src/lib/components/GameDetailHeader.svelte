<script lang="ts">
import { Calendar, MapPin } from "lucide-svelte";
import Flag from "$lib/components/Flag.svelte";
import type { GameSummary } from "$lib/types";
import { roundBadgeClass, roundLabel } from "$lib/utils";

let { game }: { game: GameSummary } = $props();
</script>

<div class="bg-linear-to-br from-zinc-950 via-zinc-900 to-zinc-950 px-4 py-8 sm:px-6 sm:py-12 relative overflow-hidden min-h-35">
  <!-- Background Away Flag -->
  <div class="absolute top-1/2 -translate-y-1/2 pointer-events-none left-30 max-sm:left-5">
    <div class="scale-[12] sm:scale-[17] opacity-8" style="mask-image: linear-gradient(to right, transparent 0%, black 25%, black 45%, transparent 100%); -webkit-mask-image: linear-gradient(to right, transparent 0%, black 25%, black 45%, transparent 100%);">
      <Flag country={game.away_team_abbreviation}/>
    </div>
  </div>

  <!-- Background Home Flag -->
  <div class="absolute top-1/2 -translate-y-1/2 pointer-events-none right-30 max-sm:right-5">
    <div class="scale-[12] sm:scale-[17] opacity-8" style="mask-image: linear-gradient(to left, transparent 0%, black 25%, black 45%, transparent 100%); -webkit-mask-image: linear-gradient(to left, transparent 0%, black 25%, black 45%, transparent 100%);">
      <Flag country={game.home_team_abbreviation}/>
    </div>
  </div>

  <div class="grid grid-cols-5 gap-2 sm:gap-4 items-center max-w-4xl mx-auto relative">
    <div class="col-span-2 text-center flex flex-col items-center">
      <div class="text-[10px] sm:text-xs tracking-widest uppercase text-zinc-500 mb-1 sm:mb-2">Away</div>
      <div class="flex items-center gap-1.5 sm:gap-3">
        <div class="hidden sm:block"><Flag country={game.away_team_abbreviation} size="lg" /></div>
        <div class="sm:hidden"><Flag country={game.away_team_abbreviation} size="md" /></div>
        <div class="text-sm sm:text-lg md:text-xl font-bold whitespace-nowrap {game.away_is_winner ? 'text-white' : 'text-zinc-400'}">
          <span class="hidden md:inline">{game.away_team_name}</span>
          <span class="md:hidden">{game.away_team_abbreviation}</span>
        </div>
      </div>
      <div class="text-4xl sm:text-6xl md:text-[5rem] leading-none font-black tracking-tight mt-1 sm:mt-2 {game.away_is_winner ? 'text-white' : 'text-zinc-400'}">
        {game.away_score}
      </div>
      <div class="mt-2 sm:mt-3 text-[10px] sm:text-xs font-bold tracking-widest uppercase text-zinc-200">
        {game.away_is_winner ? 'WIN' : 'LOSE'}
      </div>
    </div>

    <div class="text-center space-y-3 sm:space-y-6">
      <div class="flex items-center justify-center gap-1 text-[10px] sm:text-sm text-zinc-500 whitespace-nowrap overflow-visible">
        <Calendar class="w-3 h-3" />
        <span class="hidden sm:inline">{game.official_date}</span>
        <span class="sm:hidden">{game.official_date.split('-').slice(1).join('/')}</span>
      </div>
      <div class="hidden sm:flex flex items-center justify-center gap-1 text-[10px] sm:text-sm text-zinc-500 whitespace-nowrap overflow-visible">
        <MapPin class="w-4 h-4  overflow-visible" />
        <span class="truncate">{game.venue_name}</span>
      </div>
      <div class="flex flex-col items-center gap-1.5">
        <span class="border rounded-full px-1.5 py-0.5 sm:px-3 sm:py-0.5 font-medium text-center text-[10px] sm:text-xs whitespace-nowrap {roundBadgeClass(roundLabel(game))}">
          {roundLabel(game)}
        </span>
        <div class="flex flex-col items-center gap-1">
          {#if game.is_mercy_rule}
            <span class="font-medium bg-warning/15 text-warning border border-warning/25 rounded-full px-1.5 py-0 sm:px-3 sm:py-.5 inline-block text-[9px] sm:text-[10px] whitespace-nowrap">
              Mercy
            </span>
          {/if}
          {#if game.is_one_run_game}
            <span class="font-medium bg-warning/15 text-warning border border-warning/25 rounded-full px-1.5 py-0 sm:px-3 sm:py-.5 inline-block text-[9px] sm:text-[10px] whitespace-nowrap">
              1-Run
            </span>
          {/if}
        </div>
      </div>
    </div>

    <div class="col-span-2 text-center flex flex-col items-center">
      <div class="text-[10px] sm:text-xs tracking-widest uppercase text-zinc-500 mb-1 sm:mb-2">Home</div>
      <div class="flex items-center gap-1.5 sm:gap-3">
        <div class="text-sm sm:text-lg md:text-xl font-bold whitespace-nowrap {game.home_is_winner ? 'text-white' : 'text-zinc-400'}">
          <span class="hidden md:inline">{game.home_team_name}</span>
          <span class="md:hidden">{game.home_team_abbreviation}</span>
        </div>
        <div class="hidden sm:block"><Flag country={game.home_team_abbreviation} size="lg" /></div>
        <div class="sm:hidden"><Flag country={game.home_team_abbreviation} size="md" /></div>
      </div>
      <div class="text-4xl sm:text-6xl md:text-[5rem] leading-none font-black tracking-tight mt-1 sm:mt-2 {game.home_is_winner ? 'text-white' : 'text-zinc-400'}">
        {game.home_score}
      </div>
      <div class="mt-2 sm:mt-3 text-[10px] sm:text-xs font-bold tracking-widest uppercase text-zinc-200">
        {game.home_is_winner ? 'WIN' : 'LOSE'}
      </div>
    </div>
  </div>
</div>
