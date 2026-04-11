<script lang="ts">
import {
  X, Calendar, MapPin,
  ChevronDown, ChevronRight
} from "lucide-svelte";
import Flag from "$lib/components/Flag.svelte";
import type { GameSummary, GameDetailRow } from "$lib/types";
import { roundBadgeClass, roundLabel } from "$lib/utils";

// ─── Props ────────────────────────────────────────────────────────────────────
let { game, onclose }: { game: GameSummary; onclose: () => void } = $props();

// ─── Section expand state ─────────────────────────────────────────────────────
let expanded = $state<Record<string, boolean>>({
  boxscore: true,
  teamBatting: true,
  teamPitching: false,
  teamFielding: false,
  awayLineup: false,
  homeLineup: false,
  awayBench: false,
  homeBench: false,
  awayPitching: false,
  homePitching: false,
});
const toggle = (k: string) => (expanded[k] = !expanded[k]);

// ─── Player helpers ───────────────────────────────────────────────────────────
const teamPlayers = (teamId: number): GameDetailRow[] =>
  game.players.filter(p => p.team_id === teamId);

const startingBatters = (teamId: number): GameDetailRow[] =>
  teamPlayers(teamId)
    .filter(p => p.batting_order !== null && (p.batting_order ?? 99) <= 9)
    .sort((a, b) => (a.batting_order ?? 99) - (b.batting_order ?? 99));

const benchPlayers = (teamId: number): GameDetailRow[] =>
  teamPlayers(teamId).filter(
    p => p.is_on_bench || p.batting_order === null || (p.batting_order ?? 0) > 9
  );

const pitchers = (teamId: number): GameDetailRow[] =>
  teamPlayers(teamId).filter(
    p => (p.player_pitching_outs ?? 0) > 0 || (p.player_pitching_gs ?? 0) > 0
  );

// ─── Formatters ───────────────────────────────────────────────────────────────
const ip = (outs: number | null): string => {
  if (!outs) return "0";
  const full = Math.floor(outs / 3);
  const rem = outs % 3;
  return rem > 0 ? `${full}.${rem}` : `${full}`;
};

const pct = (n: number | null, d: number | null): string => {
  if (!n || !d || d === 0) return "0%";
  return `${Math.round((n / d) * 100)}%`;
};


// Helper for the new pivoted stat tables
const compareStat = (val: number, opp: number, type: 'away' | 'home', invert = false) => {
  if (val === opp) return "text-zinc-300";
  const wins = invert ? val < opp : val > opp;
  return wins ? "text-white font-bold" : "text-zinc-500";
};

// ─── Pivoted Stat Definitions ──────────────────────────────────────────────────
const teamBattingStats = $derived([
  { l: 'R', a: game.away_team.batting.runs, h: game.home_team.batting.runs },
  { l: 'H', a: game.away_team.batting.hits, h: game.home_team.batting.hits },
  { l: '2B', a: game.away_team.batting.doubles, h: game.home_team.batting.doubles },
  { l: '3B', a: game.away_team.batting.triples, h: game.home_team.batting.triples },
  { l: 'HR', a: game.away_team.batting.hr, h: game.home_team.batting.hr },
  { l: 'RBI', a: game.away_team.batting.rbi, h: game.home_team.batting.rbi },
  { l: 'BB', a: game.away_team.batting.bb, h: game.home_team.batting.bb },
  { l: 'SO', a: game.away_team.batting.so, h: game.home_team.batting.so, inv: true },
  { l: 'HBP', a: game.away_team.batting.hbp, h: game.home_team.batting.hbp },
  { l: 'SB', a: game.away_team.batting.sb, h: game.home_team.batting.sb },
  { l: 'TB', a: game.away_team.batting.tb, h: game.home_team.batting.tb },
  { l: 'LOB', a: game.away_team.batting.lob, h: game.home_team.batting.lob, inv: true },
  { l: 'GIDP', a: game.away_team.batting.gidp, h: game.home_team.batting.gidp, inv: true }
]);

const teamPitchingStats = $derived([
  { l: 'IP', a: game.away_team.pitching.outs, h: game.home_team.pitching.outs, aS: ip(game.away_team.pitching.outs), hS: ip(game.home_team.pitching.outs) },
  { l: 'Pit', a: game.away_team.pitching.total_pitches, h: game.home_team.pitching.total_pitches },
  { l: 'Str', a: game.away_team.pitching.strikes, h: game.home_team.pitching.strikes },
  { l: 'Str%', a: game.away_team.pitching.strikes / (game.away_team.pitching.total_pitches||1), h: game.home_team.pitching.strikes / (game.home_team.pitching.total_pitches||1), aS: pct(game.away_team.pitching.strikes, game.away_team.pitching.total_pitches), hS: pct(game.home_team.pitching.strikes, game.home_team.pitching.total_pitches) },
  { l: 'K', a: game.away_team.pitching.so, h: game.home_team.pitching.so },
  { l: 'BB', a: game.away_team.pitching.bb, h: game.home_team.pitching.bb, inv: true },
  { l: 'H', a: game.away_team.pitching.hits_allowed, h: game.home_team.pitching.hits_allowed, inv: true },
  { l: 'ER', a: game.away_team.pitching.er, h: game.home_team.pitching.er, inv: true },
  { l: 'HR', a: game.away_team.pitching.hr_allowed, h: game.home_team.pitching.hr_allowed, inv: true },
  { l: 'HBP', a: game.away_team.pitching.hbp, h: game.home_team.pitching.hbp, inv: true },
  { l: 'WP', a: game.away_team.pitching.wp, h: game.home_team.pitching.wp, inv: true },
  { l: 'BF', a: game.away_team.pitching.bf, h: game.home_team.pitching.bf }
]);

const teamFieldingStats = $derived([
  { l: 'E', a: game.away_team.fielding.errors, h: game.home_team.fielding.errors, inv: true },
  { l: 'Ast', a: game.away_team.fielding.assists, h: game.home_team.fielding.assists },
  { l: 'PO', a: game.away_team.fielding.put_outs, h: game.home_team.fielding.put_outs },
  { l: 'Ch', a: game.away_team.fielding.chances, h: game.home_team.fielding.chances },
  { l: 'PB', a: game.away_team.fielding.passed_balls, h: game.home_team.fielding.passed_balls, inv: true },
  { l: 'PK', a: game.away_team.fielding.pickoffs, h: game.home_team.fielding.pickoffs }
]);
</script>

<div class="bg-surface border border-border rounded-xl overflow-hidden animate-fade-in shadow-2xl">

  <div class="flex items-center justify-between px-6 py-4 border-b border-border bg-zinc-900/80 backdrop-blur">
    <div class="flex items-center gap-3 text-base font-medium text-white">
      Game Detail
    </div>
    <button
      onclick={onclose}
      class="text-[#8888a0] hover:text-white transition-colors p-1.5 rounded hover:bg-zinc-700"
    >
      <X class="w-5 h-5" />
    </button>
  </div>

    <div class="bg-linear-to-br from-zinc-950 via-zinc-900 to-zinc-950 px-4 py-8 sm:px-6 sm:py-12 relative overflow-hidden min-h-[140px]">
      <!-- Background Away Flag -->
      <div class="absolute top-1/2 -translate-y-1/2 flex items-center pointer-events-none left-30 max-sm:left-5">
        <div class="scale-[12] sm:scale-[17] opacity-8 mask-r-from-0% mask-r-to-100%">
          <Flag country={game.away_team_abbreviation}/>
        </div>
      </div>

      <!-- Background Home Flag -->
      <div class="absolute top-1/2 -translate-y-1/2 flex items-center pointer-events-none right-30 max-sm:right-5">
        <div class="scale-[12] sm:scale-[17] opacity-8 mask-l-from-0% mask-l-to-100%">
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
          <div class="flex items-center justify-center gap-1 text-[10px] sm:text-sm text-zinc-400">
            <Calendar class="w-3 h-3 sm:w-4 h-4" />
            <span class="hidden sm:inline">{game.official_date}</span>
            <span class="sm:hidden">{game.official_date.split('-').slice(1).join('/')}</span>
          </div>
          <div class="hidden sm:flex items-center justify-center gap-1 text-sm text-zinc-500 whitespace-nowrap">
            <MapPin class="w-4 h-4" />
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

  <section class="border-b border-border">
    <button onclick={() => toggle('boxscore')}
      class="w-full flex items-center justify-between px-6 py-4 hover:bg-zinc-800/40 transition-colors text-base">
      <span class="flex items-center gap-2.5 font-medium text-white">
        Box Score
      </span>
      {#if expanded.boxscore}<ChevronDown class="w-5 h-5 text-zinc-500" />
      {:else}<ChevronRight class="w-5 h-5 text-zinc-500" />{/if}
    </button>

    {#if expanded.boxscore}
    <div class="px-6 pb-6">
      <div class="rounded-xl overflow-hidden bg-zinc-900 border border-zinc-800">
        <div 
          class="overflow-x-auto">
          <table class="w-full text-sm sm:text-base min-w-max table-fixed">
          <thead class="bg-zinc-950/50 text-zinc-400 uppercase tracking-wider text-xs sm:text-sm font-medium">
            <tr class="border-b border-zinc-800">
<th class="text-left py-3 px-4 w-[250px] sticky left-0 bg-zinc-900">Team</th>
              {#each game.away_innings as _, i}
                <th class="text-center py-3 px-3 w-9">{i + 1}</th>
              {/each}
              <th class="text-center py-3 px-3 w-12 text-white bg-zinc-800/50">R</th>
              <th class="text-center py-3 px-3 w-12 text-white bg-zinc-800/50">H</th>
              <th class="text-center py-3 px-3 w-12 text-white bg-zinc-800/50">E</th>
            </tr>
          </thead>
          <tbody>
            <tr class="border-b border-zinc-800/50">
              <td class="py-2.5 px-4 font-semibold flex items-center gap-3 sticky left-0">
                <Flag country={game.away_team_abbreviation} size="md" />
                {game.away_team_abbreviation}
              </td>
              {#each game.away_innings as run}
                <td class="text-center py-2.5 px-3 text-zinc-300">{run ?? '-'}</td>
              {/each}
              <td class="text-center py-2.5 px-3 font-bold text-white bg-zinc-800/30">{game.away_r}</td>
              <td class="text-center py-2.5 px-3 text-white bg-zinc-800/30">{game.away_h}</td>
              <td class="text-center py-2.5 px-3 text-white bg-zinc-800/30">{game.away_e}</td>
            </tr>
            <tr>
              <td class="py-2.5 px-4 font-semibold flex items-center gap-3 sticky left-0">
                <Flag country={game.home_team_abbreviation} size="md" />
                {game.home_team_abbreviation}
              </td>
              {#each game.home_innings as run}
                <td class="text-center py-2.5 px-3 text-zinc-300">{run ?? '-'}</td>
              {/each}
              <td class="text-center py-2.5 px-3 font-bold text-white bg-zinc-800/30">{game.home_r}</td>
              <td class="text-center py-2.5 px-3 text-white bg-zinc-800/30">{game.home_h}</td>
              <td class="text-center py-2.5 px-3 text-white bg-zinc-800/30">{game.home_e}</td>
            </tr>
          </tbody>
        </table>
        </div>
      </div>
    </div>
    {/if}
  </section>

  <section class="border-b border-border">
    <button onclick={() => toggle('teamBatting')}
      class="w-full flex items-center justify-between px-6 py-4 hover:bg-zinc-800/40 transition-colors text-base">
      <span class="flex items-center gap-3.5 font-medium text-white">
        Team Batting
      </span>
      {#if expanded.teamBatting}<ChevronDown class="w-5 h-5 text-zinc-500" />
      {:else}<ChevronRight class="w-5 h-5 text-zinc-500" />{/if}
    </button>

    {#if expanded.teamBatting}
    <div class="px-6 pb-6">
      <div class="rounded-xl overflow-hidden bg-zinc-900 border border-zinc-800">
        <div class="overflow-x-auto">
        <table class="w-full text-sm sm:text-base min-w-max table-fixed">
          <thead class="bg-zinc-950/50 text-zinc-400 uppercase tracking-wider text-xs sm:text-sm font-medium">
            <tr class="border-b border-zinc-800">
<th class="text-left py-3 px-4 w-[250px] sticky left-0">Team</th>
              {#each teamBattingStats as s}
                <th class="text-center py-3 px-2 w-10">{s.l}</th>
              {/each}
            </tr>
          </thead>
          <tbody>
            <tr class="border-b border-zinc-800/50 hover:bg-zinc-800/20">
              <td class="py-2.5 px-4 font-semibold flex items-center gap-3 sticky left-0 bg-zinc-900">
                <Flag country={game.away_team_abbreviation} size="md" />
                {game.away_team_abbreviation}
              </td>
              {#each teamBattingStats as s}
                <td class="text-center py-2.5 px-2 {compareStat(s.a, s.h, 'away', s.inv)}">{s.a}</td>
              {/each}
            </tr>
            <tr class="hover:bg-zinc-800/20">
              <td class="py-2.5 px-4 font-semibold flex items-center gap-3 sticky left-0 bg-zinc-900">
                <Flag country={game.home_team_abbreviation} size="md" />
                {game.home_team_abbreviation}
              </td>
              {#each teamBattingStats as s}
                <td class="text-center py-2.5 px-2 {compareStat(s.h, s.a, 'home', s.inv)}">{s.h}</td>
              {/each}
            </tr>
          </tbody>
        </table>
        </div>
      </div>
    </div>
    {/if}
  </section>

  <section class="border-b border-border">
    <button onclick={() => toggle('teamPitching')}
      class="w-full flex items-center justify-between px-6 py-4 hover:bg-zinc-800/40 transition-colors text-base">
      <span class="flex items-center gap-2.5 font-medium text-white">
        Team Pitching
      </span>
      {#if expanded.teamPitching}<ChevronDown class="w-5 h-5 text-zinc-500" />
      {:else}<ChevronRight class="w-5 h-5 text-zinc-500" />{/if}
    </button>

    {#if expanded.teamPitching}
    <div class="px-6 pb-6">
      <div class="rounded-xl overflow-hidden bg-zinc-900 border border-zinc-800">
        <div class="overflow-x-auto">
        <table class="w-full text-sm sm:text-base min-w-max table-fixed">
          <thead class="bg-zinc-950/50 text-zinc-400 uppercase tracking-wider text-xs sm:text-sm font-medium">
            <tr class="border-b border-zinc-800">
              <th class="text-left py-3 px-4 w-[250px] sticky left-0 bg-zinc-900">Team</th>
              {#each teamPitchingStats as s}
                <th class="text-center py-3 px-2 w-10">{s.l}</th>
              {/each}
            </tr>
          </thead>
          <tbody>
            <tr class="border-b border-zinc-800/50 hover:bg-zinc-800/20">
              <td class="py-2.5 px-4 font-semibold flex items-center gap-3 sticky left-0 bg-zinc-900">
                <Flag country={game.away_team_abbreviation} size="md" />
                {game.away_team_abbreviation}
              </td>
              {#each teamPitchingStats as s}
                <td class="text-center py-2.5 px-2 {compareStat(s.a, s.h, 'away', s.inv)}">{s.aS ?? s.a}</td>
              {/each}
            </tr>
            <tr class="hover:bg-zinc-800/20">
              <td class="py-2.5 px-4 font-semibold flex items-center gap-3 sticky left-0 bg-zinc-900">
                <Flag country={game.home_team_abbreviation} size="md" />
                {game.home_team_abbreviation}
              </td>
              {#each teamPitchingStats as s}
                <td class="text-center py-2.5 px-2 {compareStat(s.h, s.a, 'home', s.inv)}">{s.hS ?? s.h}</td>
              {/each}
            </tr>
          </tbody>
        </table>
        </div>
      </div>
    </div>
    {/if}
  </section>

  <section class="border-b border-border">
    <button onclick={() => toggle('teamFielding')}
      class="w-full flex items-center justify-between px-6 py-4 hover:bg-zinc-800/40 transition-colors text-base">
      <span class="flex items-center gap-2.5 font-medium text-white">
        Team Fielding
      </span>
      {#if expanded.teamFielding}<ChevronDown class="w-5 h-5 text-zinc-500" />
      {:else}<ChevronRight class="w-5 h-5 text-zinc-500" />{/if}
    </button>

    {#if expanded.teamFielding}
    <div class="px-6 pb-6">
      <div class="rounded-xl overflow-hidden bg-zinc-900 border border-zinc-800">
        <div class="overflow-x-auto">
        <table class="w-full text-sm sm:text-base min-w-max table-fixed">
          <thead class="bg-zinc-950/50 text-zinc-400 uppercase tracking-wider text-xs sm:text-sm font-medium">
            <tr class="border-b border-zinc-800">
              <th class="text-left py-3 px-4 w-[250px] sticky left-0 bg-zinc-900">Team</th>
              {#each teamFieldingStats as s}
                <th class="text-center py-3 px-2 w-10">{s.l}</th>
              {/each}
            </tr>
          </thead>
          <tbody>
            <tr class="border-b border-zinc-800/50 hover:bg-zinc-800/20">
              <td class="py-2.5 px-4 font-semibold flex items-center gap-3 sticky left-0 bg-zinc-900">
                <Flag country={game.away_team_abbreviation} size="md" />
                {game.away_team_abbreviation}
              </td>
              {#each teamFieldingStats as s}
                <td class="text-center py-2.5 px-2 {compareStat(s.a, s.h, 'away', s.inv)}">{s.a}</td>
              {/each}
            </tr>
            <tr class="hover:bg-zinc-800/20">
              <td class="py-2.5 px-4 font-semibold flex items-center gap-3 sticky left-0 bg-zinc-900">
                <Flag country={game.home_team_abbreviation} size="md" />
                {game.home_team_abbreviation}
              </td>
              {#each teamFieldingStats as s}
                <td class="text-center py-2.5 px-2 {compareStat(s.h, s.a, 'home', s.inv)}">{s.h}</td>
              {/each}
            </tr>
          </tbody>
        </table>
        </div>
      </div>
    </div>
    {/if}
  </section>

  {#if startingBatters(game.away_team_id).length > 0}
  <section class="border-b border-border">
    <button onclick={() => toggle('awayLineup')}
      class="w-full flex items-center justify-between px-6 py-4 hover:bg-zinc-800/40 transition-colors text-base">
      <span class="flex items-center gap-2.5 font-medium text-white">
        <span class="text-zinc-300">{game.away_team_abbreviation}</span>&nbsp;Batting Lineup
      </span>
      {#if expanded.awayLineup}<ChevronDown class="w-5 h-5 text-zinc-500" />
      {:else}<ChevronRight class="w-5 h-5 text-zinc-500" />{/if}
    </button>

    {#if expanded.awayLineup}
    <div class="px-6 pb-6">
      <div class="rounded-xl overflow-hidden bg-zinc-900 border border-zinc-800">
        <div class="overflow-x-auto">
        <table class="w-full text-sm sm:text-base min-w-max table-fixed">
        <thead class="bg-zinc-950/50">
          <tr class="border-b border-zinc-800 text-zinc-400 uppercase tracking-wider text-xs sm:text-sm font-medium">
<th class="text-left py-3 px-4 w-[250px] sticky left-0 bg-zinc-900">Player</th>
            <th class="text-center py-3 px-2 w-10">AB</th>
            <th class="text-center py-3 px-2 w-10">R</th>
            <th class="text-center py-3 px-2 w-10">H</th>
            <th class="text-center py-3 px-2 w-10">2B</th>
            <th class="text-center py-3 px-2 w-10">3B</th>
            <th class="text-center py-3 px-2 w-10">HR</th>
            <th class="text-center py-3 px-2 w-10">RBI</th>
            <th class="text-center py-3 px-2 w-10">BB</th>
            <th class="text-center py-3 px-2 w-10">K</th>
            <th class="text-center py-3 px-2 w-10">SB</th>
            <th class="text-center py-3 px-2 w-10">HBP</th>
            <th class="text-center py-3 px-2 w-10">TB</th>
          </tr>
        </thead>
        <tbody>
          {#each startingBatters(game.away_team_id) as p}
          <tr class="border-b border-zinc-800/50 hover:bg-zinc-800/20">
            <td class="py-2.5 px-4 text-white font-semibold flex items-center gap-3 sticky left-0 bg-zinc-900">
              <span class="text-zinc-500 w-4 text-right shrink-0">{p.batting_order}</span>
              <span class="text-zinc-400 font-mono text-xs w-6 shrink-0">{p.primary_position_abbreviation ?? ''}</span>
              <span class="truncate">
                {p.boxscore_name ?? p.full_name ?? '—'}
                {#if p.is_substitute}<span class="text-zinc-500 text-[10px] sm:text-xs ml-1 font-normal">(sub)</span>{/if}
              </span>
            </td>
            <td class="text-center py-2.5 px-2 text-zinc-300">{p.player_batting_ab ?? 0}</td>
            <td class="text-center py-2.5 px-2 text-zinc-300">{p.player_batting_runs ?? 0}</td>
            <td class="text-center py-2.5 px-2 {(p.player_batting_hits ?? 0) >= 2 ? 'text-green-400 font-bold' : 'text-zinc-300'}">{p.player_batting_hits ?? 0}</td>
            <td class="text-center py-2.5 px-2 {(p.player_batting_doubles ?? 0) > 0 ? 'text-green-300 font-medium' : 'text-zinc-300'}">{p.player_batting_doubles ?? 0}</td>
            <td class="text-center py-2.5 px-2 {(p.player_batting_triples ?? 0) > 0 ? 'text-blue-300 font-medium' : 'text-zinc-300'}">{p.player_batting_triples ?? 0}</td>
            <td class="text-center py-2.5 px-2 {(p.player_batting_hr ?? 0) > 0 ? 'text-yellow-400 font-black' : 'text-zinc-300'}">{p.player_batting_hr ?? 0}</td>
            <td class="text-center py-2.5 px-2 text-zinc-300">{p.player_batting_rbi ?? 0}</td>
            <td class="text-center py-2.5 px-2 text-zinc-300">{p.player_batting_bb ?? 0}</td>
            <td class="text-center py-2.5 px-2 {(p.player_batting_so ?? 0) >= 3 ? 'text-red-400 font-semibold' : 'text-zinc-300'}">{p.player_batting_so ?? 0}</td>
            <td class="text-center py-2.5 px-2 text-zinc-300">{p.player_batting_sb ?? 0}</td>
            <td class="text-center py-2.5 px-2 text-zinc-300">{p.player_batting_hbp ?? 0}</td>
            <td class="text-center py-2.5 px-2 text-zinc-400">{p.player_batting_tb ?? 0}</td>
          </tr>
          {/each}

          {#if benchPlayers(game.away_team_id).length > 0}
          <tr>
            <td colspan="13" class="p-0 border-b border-zinc-800">
              <button onclick={() => toggle('awayBench')} class="w-full flex items-center justify-between py-3 px-4 text-xs font-semibold uppercase tracking-widest text-zinc-400 hover:bg-zinc-800/40 transition-colors bg-zinc-900/30">
                <span>Bench Reserves ({benchPlayers(game.away_team_id).length})</span>
                {#if expanded.awayBench}<ChevronDown class="w-4 h-4" />{:else}<ChevronRight class="w-4 h-4" />{/if}
              </button>
            </td>
          </tr>
          {#if expanded.awayBench}
            {#each benchPlayers(game.away_team_id) as p}
            <tr class="border-b border-zinc-800/30 bg-zinc-900/20">
              <td class="py-2 px-4 text-zinc-400 font-medium flex items-center gap-3 sticky left-0 bg-zinc-900">
                <span class="text-zinc-600 w-4 text-right shrink-0">—</span>
                <span class="text-zinc-500 font-mono text-xs w-6 shrink-0">{p.primary_position_abbreviation ?? ''}</span>
                <span class="truncate">{p.boxscore_name ?? p.full_name ?? '—'}</span>
              </td>
              <td class="text-center py-2 px-2 text-zinc-500">{p.player_batting_ab ?? 0}</td>
              <td class="text-center py-2 px-2 text-zinc-500">{p.player_batting_runs ?? 0}</td>
              <td class="text-center py-2 px-2 text-zinc-500">{p.player_batting_hits ?? 0}</td>
              <td class="text-center py-2 px-2 text-zinc-500">{p.player_batting_doubles ?? 0}</td>
              <td class="text-center py-2 px-2 text-zinc-500">{p.player_batting_triples ?? 0}</td>
              <td class="text-center py-2 px-2 text-zinc-500">{p.player_batting_hr ?? 0}</td>
              <td class="text-center py-2 px-2 text-zinc-500">{p.player_batting_rbi ?? 0}</td>
              <td class="text-center py-2 px-2 text-zinc-500">{p.player_batting_bb ?? 0}</td>
              <td class="text-center py-2 px-2 text-zinc-500">{p.player_batting_so ?? 0}</td>
              <td class="text-center py-2 px-2 text-zinc-500">{p.player_batting_sb ?? 0}</td>
              <td class="text-center py-2 px-2 text-zinc-500">{p.player_batting_hbp ?? 0}</td>
              <td class="text-center py-2 px-2 text-zinc-500">{p.player_batting_tb ?? 0}</td>
            </tr>
            {/each}
          {/if}
          {/if}
        </tbody>
        </table>
        </div>
      </div>
    </div>
    {/if}
  </section>
  {/if}

  {#if startingBatters(game.home_team_id).length > 0}
  <section class="border-b border-border">
    <button onclick={() => toggle('homeLineup')}
      class="w-full flex items-center justify-between px-6 py-4 hover:bg-zinc-800/40 transition-colors text-base">
      <span class="flex items-center gap-2.5 font-medium text-white">
        <span class="text-zinc-300">{game.home_team_abbreviation}</span>&nbsp;Batting Lineup
      </span>
      {#if expanded.homeLineup}<ChevronDown class="w-5 h-5 text-zinc-500" />
      {:else}<ChevronRight class="w-5 h-5 text-zinc-500" />{/if}
    </button>

    {#if expanded.homeLineup}
    <div class="px-6 pb-6">
      <div class="rounded-xl overflow-hidden bg-zinc-900 border border-zinc-800">
        <div class="overflow-x-auto">
        <table class="w-full text-sm sm:text-base min-w-max table-fixed">
          <thead class="bg-zinc-950/50">
            <tr class="border-b border-zinc-800 text-zinc-400 uppercase tracking-wider text-xs sm:text-sm font-medium">
              <th class="text-left py-3 px-4 w-[250px] sticky left-0 bg-zinc-900">Player</th>
              <th class="text-center py-3 px-2 w-10">AB</th>
              <th class="text-center py-3 px-2 w-10">R</th>
              <th class="text-center py-3 px-2 w-10">H</th>
              <th class="text-center py-3 px-2 w-10">2B</th>
              <th class="text-center py-3 px-2 w-10">3B</th>
              <th class="text-center py-3 px-2 w-10">HR</th>
              <th class="text-center py-3 px-2 w-10">RBI</th>
              <th class="text-center py-3 px-2 w-10">BB</th>
              <th class="text-center py-3 px-2 w-10">K</th>
              <th class="text-center py-3 px-2 w-10">SB</th>
              <th class="text-center py-3 px-2 w-10">HBP</th>
              <th class="text-center py-3 px-2 w-10">TB</th>
            </tr>
          </thead>
        <tbody>
          {#each startingBatters(game.home_team_id) as p}
          <tr class="border-b border-zinc-800/50 hover:bg-zinc-800/20">
            <td class="py-2.5 px-4 text-white font-semibold flex items-center gap-3 sticky left-0 bg-zinc-900">
              <span class="text-zinc-500 w-4 text-right shrink-0">{p.batting_order}</span>
              <span class="text-zinc-400 font-mono text-xs w-6 shrink-0">{p.primary_position_abbreviation ?? ''}</span>
              <span class="truncate">
                {p.boxscore_name ?? p.full_name ?? '—'}
                {#if p.is_substitute}<span class="text-zinc-500 text-[10px] sm:text-xs ml-1 font-normal">(sub)</span>{/if}
              </span>
            </td>
            <td class="text-center py-2.5 px-2 text-zinc-300">{p.player_batting_ab ?? 0}</td>
            <td class="text-center py-2.5 px-2 text-zinc-300">{p.player_batting_runs ?? 0}</td>
            <td class="text-center py-2.5 px-2 {(p.player_batting_hits ?? 0) >= 2 ? 'text-green-400 font-bold' : 'text-zinc-300'}">{p.player_batting_hits ?? 0}</td>
            <td class="text-center py-2.5 px-2 {(p.player_batting_doubles ?? 0) > 0 ? 'text-green-300 font-medium' : 'text-zinc-300'}">{p.player_batting_doubles ?? 0}</td>
            <td class="text-center py-2.5 px-2 {(p.player_batting_triples ?? 0) > 0 ? 'text-blue-300 font-medium' : 'text-zinc-300'}">{p.player_batting_triples ?? 0}</td>
            <td class="text-center py-2.5 px-2 {(p.player_batting_hr ?? 0) > 0 ? 'text-yellow-400 font-black' : 'text-zinc-300'}">{p.player_batting_hr ?? 0}</td>
            <td class="text-center py-2.5 px-2 text-zinc-300">{p.player_batting_rbi ?? 0}</td>
            <td class="text-center py-2.5 px-2 text-zinc-300">{p.player_batting_bb ?? 0}</td>
            <td class="text-center py-2.5 px-2 {(p.player_batting_so ?? 0) >= 3 ? 'text-red-400 font-semibold' : 'text-zinc-300'}">{p.player_batting_so ?? 0}</td>
            <td class="text-center py-2.5 px-2 text-zinc-300">{p.player_batting_sb ?? 0}</td>
            <td class="text-center py-2.5 px-2 text-zinc-300">{p.player_batting_hbp ?? 0}</td>
            <td class="text-center py-2.5 px-2 text-zinc-400">{p.player_batting_tb ?? 0}</td>
          </tr>
          {/each}

          {#if benchPlayers(game.home_team_id).length > 0}
          <tr>
            <td colspan="13" class="p-0 border-b border-zinc-800">
              <button onclick={() => toggle('homeBench')} class="w-full flex items-center justify-between py-3 px-4 text-xs font-semibold uppercase tracking-widest text-zinc-400 hover:bg-zinc-800/40 transition-colors bg-zinc-900/30">
                <span>Bench Reserves ({benchPlayers(game.home_team_id).length})</span>
                {#if expanded.homeBench}<ChevronDown class="w-4 h-4" />{:else}<ChevronRight class="w-4 h-4" />{/if}
              </button>
            </td>
          </tr>
          {#if expanded.homeBench}
            {#each benchPlayers(game.home_team_id) as p}
            <tr class="border-b border-zinc-800/30 bg-zinc-900/20">
              <td class="py-2 px-4 text-zinc-400 font-medium flex items-center gap-3 sticky left-0 bg-zinc-900">
                <span class="text-zinc-600 w-4 text-right shrink-0">—</span>
                <span class="text-zinc-500 font-mono text-xs w-6 shrink-0">{p.primary_position_abbreviation ?? ''}</span>
                <span class="truncate">{p.boxscore_name ?? p.full_name ?? '—'}</span>
              </td>
              <td class="text-center py-2 px-2 text-zinc-500">{p.player_batting_ab ?? 0}</td>
              <td class="text-center py-2 px-2 text-zinc-500">{p.player_batting_runs ?? 0}</td>
              <td class="text-center py-2 px-2 text-zinc-500">{p.player_batting_hits ?? 0}</td>
              <td class="text-center py-2 px-2 text-zinc-500">{p.player_batting_doubles ?? 0}</td>
              <td class="text-center py-2 px-2 text-zinc-500">{p.player_batting_triples ?? 0}</td>
              <td class="text-center py-2 px-2 text-zinc-500">{p.player_batting_hr ?? 0}</td>
              <td class="text-center py-2 px-2 text-zinc-500">{p.player_batting_rbi ?? 0}</td>
              <td class="text-center py-2 px-2 text-zinc-500">{p.player_batting_bb ?? 0}</td>
              <td class="text-center py-2 px-2 text-zinc-500">{p.player_batting_so ?? 0}</td>
              <td class="text-center py-2 px-2 text-zinc-500">{p.player_batting_sb ?? 0}</td>
              <td class="text-center py-2 px-2 text-zinc-500">{p.player_batting_hbp ?? 0}</td>
              <td class="text-center py-2 px-2 text-zinc-500">{p.player_batting_tb ?? 0}</td>
            </tr>
            {/each}
          {/if}
          {/if}
          </tbody>
        </table>
        </div>
      </div>
    </div>
    {/if}
  </section>
  {/if}

  {#if pitchers(game.away_team_id).length > 0}
  <section class="border-b border-border">
    <button onclick={() => toggle('awayPitching')}
      class="w-full flex items-center justify-between px-6 py-4 hover:bg-zinc-800/40 transition-colors text-base">
      <span class="flex items-center gap-2.5 font-medium text-white">
        <span class="text-zinc-300">{game.away_team_abbreviation}</span>&nbsp;Pitching
      </span>
      {#if expanded.awayPitching}<ChevronDown class="w-5 h-5 text-zinc-500" />
      {:else}<ChevronRight class="w-5 h-5 text-zinc-500" />{/if}
    </button>

    {#if expanded.awayPitching}
    <div class="px-6 pb-6">
      <div class="rounded-xl overflow-hidden bg-zinc-900 border border-zinc-800">
        <div class="overflow-x-auto">
        <table class="w-full text-sm sm:text-base min-w-max table-fixed">
          <thead class="bg-zinc-950/50">
          <tr class="border-b border-zinc-800 text-zinc-400 uppercase tracking-wider text-xs sm:text-sm font-medium">
<th class="text-left py-3 px-4 w-[250px] sticky left-0 bg-zinc-900">Pitcher</th>
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
          {#each pitchers(game.away_team_id) as p}
          <tr class="border-b border-zinc-800/50 hover:bg-zinc-800/20">
            <td class="py-2.5 px-4 text-white font-semibold flex items-center gap-3 sticky left-0 bg-zinc-900">
              <span class="truncate">
                {p.boxscore_name ?? p.full_name ?? '—'}
              </span>
              <span class="text-xs ml-1.5">
                {#if p.player_pitching_wins}<span class="text-green-400 font-bold mr-1">W</span>{/if}
                {#if p.player_pitching_losses}<span class="text-red-400 font-bold mr-1">L</span>{/if}
                {#if p.player_pitching_saves}<span class="text-blue-400 font-bold mr-1">Sv</span>{/if}
                {#if p.player_pitching_holds}<span class="text-purple-400 font-bold mr-1">H</span>{/if}
                {#if p.player_pitching_bs}<span class="text-orange-400 font-bold mr-1">BS</span>{/if}
                {#if p.player_pitching_gs}<span class="text-zinc-500 font-normal">(GS)</span>{/if}
              </span>
            </td>
            <td class="text-center py-2.5 px-2 text-zinc-200 font-mono">{ip(p.player_pitching_outs)}</td>
            <td class="text-center py-2.5 px-2 text-zinc-300">{p.player_pitching_hits_allowed ?? 0}</td>
            <td class="text-center py-2.5 px-2 text-zinc-300">{p.player_pitching_runs_allowed ?? 0}</td>
            <td class="text-center py-2.5 px-2 text-zinc-300">{p.player_pitching_er ?? 0}</td>
            <td class="text-center py-2.5 px-2 text-zinc-300">{p.player_pitching_bb ?? 0}</td>
            <td class="text-center py-2.5 px-2 {(p.player_pitching_so ?? 0) >= 5 ? 'text-green-400 font-bold' : 'text-zinc-300'}">{p.player_pitching_so ?? 0}</td>
            <td class="text-center py-2.5 px-2 text-zinc-300">{p.player_pitching_hbp ?? 0}</td>
            <td class="text-center py-2.5 px-2 {(p.player_pitching_wp ?? 0) > 0 ? 'text-orange-400 font-medium' : 'text-zinc-300'}">{p.player_pitching_wp ?? 0}</td>
            <td class="text-center py-2.5 px-2 text-zinc-400">{p.player_pitching_total_pitches ?? 0}</td>
            <td class="text-center py-2.5 px-2 text-zinc-400">{pct(p.player_pitching_strikes, p.player_pitching_total_pitches)}</td>
            <td class="text-center py-2.5 px-2 text-zinc-500">{p.player_pitching_bf ?? 0}</td>
          </tr>
          {/each}
          </tbody>
        </table>
        </div>
      </div>
    </div>
    {/if}
  </section>
  {/if}

  {#if pitchers(game.home_team_id).length > 0}
  <section class="border-b border-border">
    <button onclick={() => toggle('homePitching')}
      class="w-full flex items-center justify-between px-6 py-4 hover:bg-zinc-800/40 transition-colors text-base">
      <span class="flex items-center gap-2.5 font-medium text-white">
        <span class="text-zinc-300">{game.home_team_abbreviation}</span>&nbsp;Pitching
      </span>
      {#if expanded.homePitching}<ChevronDown class="w-5 h-5 text-zinc-500" />
      {:else}<ChevronRight class="w-5 h-5 text-zinc-500" />{/if}
    </button>

    {#if expanded.homePitching}
    <div class="px-6 pb-6">
      <div class="rounded-xl overflow-hidden bg-zinc-900 border border-zinc-800">
        <div class="overflow-x-auto">
        <table class="w-full text-sm sm:text-base min-w-max table-fixed">
          <thead class="bg-zinc-950/50">
          <tr class="border-b border-zinc-800 text-zinc-400 uppercase tracking-wider text-xs sm:text-sm font-medium">
            <th class="text-left py-3 px-4 w-[250px] sticky left-0 bg-zinc-900">Pitcher</th>
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
          {#each pitchers(game.home_team_id) as p}
          <tr class="border-b border-zinc-800/50 hover:bg-zinc-800/20">
            <td class="py-2.5 px-4 text-white font-semibold flex items-center gap-3 sticky left-0 bg-zinc-900">
              <span class="truncate">
                {p.boxscore_name ?? p.full_name ?? '—'}
              </span>
              <span class="text-xs ml-1.5">
                {#if p.player_pitching_wins}<span class="text-green-400 font-bold mr-1">W</span>{/if}
                {#if p.player_pitching_losses}<span class="text-red-400 font-bold mr-1">L</span>{/if}
                {#if p.player_pitching_saves}<span class="text-blue-400 font-bold mr-1">Sv</span>{/if}
                {#if p.player_pitching_holds}<span class="text-purple-400 font-bold mr-1">H</span>{/if}
                {#if p.player_pitching_bs}<span class="text-orange-400 font-bold mr-1">BS</span>{/if}
                {#if p.player_pitching_gs}<span class="text-zinc-500 font-normal">(GS)</span>{/if}
              </span>
            </td>
            <td class="text-center py-2.5 px-2 text-zinc-200 font-mono">{ip(p.player_pitching_outs)}</td>
            <td class="text-center py-2.5 px-2 text-zinc-300">{p.player_pitching_hits_allowed ?? 0}</td>
            <td class="text-center py-2.5 px-2 text-zinc-300">{p.player_pitching_runs_allowed ?? 0}</td>
            <td class="text-center py-2.5 px-2 text-zinc-300">{p.player_pitching_er ?? 0}</td>
            <td class="text-center py-2.5 px-2 text-zinc-300">{p.player_pitching_bb ?? 0}</td>
            <td class="text-center py-2.5 px-2 {(p.player_pitching_so ?? 0) >= 5 ? 'text-green-400 font-bold' : 'text-zinc-300'}">{p.player_pitching_so ?? 0}</td>
            <td class="text-center py-2.5 px-2 text-zinc-300">{p.player_pitching_hbp ?? 0}</td>
            <td class="text-center py-2.5 px-2 {(p.player_pitching_wp ?? 0) > 0 ? 'text-orange-400 font-medium' : 'text-zinc-300'}">{p.player_pitching_wp ?? 0}</td>
            <td class="text-center py-2.5 px-2 text-zinc-400">{p.player_pitching_total_pitches ?? 0}</td>
            <td class="text-center py-2.5 px-2 text-zinc-400">{pct(p.player_pitching_strikes, p.player_pitching_total_pitches)}</td>
            <td class="text-center py-2.5 px-2 text-zinc-500">{p.player_pitching_bf ?? 0}</td>
          </tr>
          {/each}
          </tbody>
        </table>
        </div>
      </div>
    </div>
    {/if}
  </section>
  {/if}

  <div class="px-6 py-4 bg-zinc-950/80 text-xs sm:text-sm text-zinc-500 flex flex-wrap gap-x-6 gap-y-2">
    <span><span class="text-zinc-600 mr-1">Season</span> {game.season}</span>
    {#if game.pool_group && game.pool_group.toLowerCase().includes('pool')}<span><span class="text-zinc-600 mr-1">Pool</span> {game.pool_group}</span>{/if}
    <span><span class="text-zinc-600 mr-1">Venue</span> {game.venue_name}</span>
  </div>
</div>