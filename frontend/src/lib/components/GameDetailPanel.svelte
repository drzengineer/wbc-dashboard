<script lang="ts">
import { X } from "lucide-svelte";
import GameDetailTableSection from "$lib/components/GameDetailTableSection.svelte";
import GameDetailHeader from "$lib/components/GameDetailHeader.svelte";
import GameBoxScoreTable from "$lib/components/GameBoxScoreTable.svelte";
import GameTeamStatsTable from "$lib/components/GameTeamStatsTable.svelte";
import GameBattingTable from "$lib/components/GameBattingTable.svelte";
import GamePitchingTable from "$lib/components/GamePitchingTable.svelte";
import type { GameSummary, GameDetailRow } from "$lib/types";
import { formatIP, formatPct } from "$lib/utils";

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

// ─── Data Derived ─────────────────────────────────────────────────────────────
const teamPlayers = (teamId: number) => game.players.filter(p => p.team_id === teamId);

const getBatters = (teamId: number) => teamPlayers(teamId)
  .filter(p => p.batting_order !== null && (p.batting_order ?? 99) <= 9)
  .sort((a, b) => (a.batting_order ?? 99) - (b.batting_order ?? 99));

const getBench = (teamId: number) => teamPlayers(teamId).filter(
  p => p.is_on_bench || p.batting_order === null || (p.batting_order ?? 0) > 9
);

const getPitchers = (teamId: number) => teamPlayers(teamId).filter(
  p => (p.player_pitching_outs ?? 0) > 0 || (p.player_pitching_gs ?? 0) > 0
);

const awayLineup = $derived(getBatters(game.away_team_id));
const homeLineup = $derived(getBatters(game.home_team_id));
const awayBench = $derived(getBench(game.away_team_id));
const homeBench = $derived(getBench(game.home_team_id));
const awayPitchers = $derived(getPitchers(game.away_team_id));
const homePitchers = $derived(getPitchers(game.home_team_id));

// ─── Pivoted Stat Definitions ──────────────────────────────────────────────────
const teamBattingStats = $derived([
  { l: 'R', a: game.away_team.batting.runs, h: game.home_team.batting.runs },
  { l: 'H', a: game.away_team.batting.hits, h: game.home_team.batting.hits },
  { l: '2B', a: game.away_team.batting.doubles, h: game.home_team.batting.doubles },
  { l: '3B', a: game.away_team.batting.triples, h: game.home_team.batting.triples },
  { l: 'HR', a: game.away_team.batting.hr, h: game.home_team.batting.hr },
  { l: 'RBI', a: game.away_team.batting.rbi, h: game.home_team.batting.rbi },
  { l: 'BB', a: game.away_team.batting.bb, h: game.home_team.batting.bb },
  { l: 'SO', a: game.away_team.batting.so, h: game.home_team.batting.so },
  { l: 'HBP', a: game.away_team.batting.hbp, h: game.home_team.batting.hbp },
  { l: 'SB', a: game.away_team.batting.sb, h: game.home_team.batting.sb },
  { l: 'TB', a: game.away_team.batting.tb, h: game.home_team.batting.tb },
  { l: 'LOB', a: game.away_team.batting.lob, h: game.home_team.batting.lob },
  { l: 'GIDP', a: game.away_team.batting.gidp, h: game.home_team.batting.gidp }
]);

const teamPitchingStats = $derived([
  { l: 'IP', a: game.away_team.pitching.outs, h: game.home_team.pitching.outs, aS: formatIP(game.away_team.pitching.outs), hS: formatIP(game.home_team.pitching.outs) },
  { l: 'Pit', a: game.away_team.pitching.total_pitches, h: game.home_team.pitching.total_pitches },
  { l: 'Str', a: game.away_team.pitching.strikes, h: game.home_team.pitching.strikes },
  { l: 'Str%', a: 0, h: 0, aS: formatPct(game.away_team.pitching.strikes, game.away_team.pitching.total_pitches), hS: formatPct(game.home_team.pitching.strikes, game.home_team.pitching.total_pitches) },
  { l: 'K', a: game.away_team.pitching.so, h: game.home_team.pitching.so },
  { l: 'BB', a: game.away_team.pitching.bb, h: game.home_team.pitching.bb },
  { l: 'H', a: game.away_team.pitching.hits_allowed, h: game.home_team.pitching.hits_allowed },
  { l: 'ER', a: game.away_team.pitching.er, h: game.home_team.pitching.er },
  { l: 'HR', a: game.away_team.pitching.hr_allowed, h: game.home_team.pitching.hr_allowed },
  { l: 'HBP', a: game.away_team.pitching.hbp, h: game.home_team.pitching.hbp },
  { l: 'WP', a: game.away_team.pitching.wp, h: game.home_team.pitching.wp },
  { l: 'BF', a: game.away_team.pitching.bf, h: game.home_team.pitching.bf }
]);

const teamFieldingStats = $derived([
  { l: 'E', a: game.away_team.fielding.errors, h: game.home_team.fielding.errors },
  { l: 'Ast', a: game.away_team.fielding.assists, h: game.home_team.fielding.assists },
  { l: 'PO', a: game.away_team.fielding.put_outs, h: game.home_team.fielding.put_outs },
  { l: 'Ch', a: game.away_team.fielding.chances, h: game.home_team.fielding.chances },
  { l: 'PB', a: game.away_team.fielding.passed_balls, h: game.home_team.fielding.passed_balls },
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

  <GameDetailHeader {game} />

  <GameDetailTableSection title="Box Score" expanded={expanded.boxscore} onToggle={() => toggle('boxscore')}>
    <GameBoxScoreTable {game} />
  </GameDetailTableSection>

  <GameDetailTableSection title="Team Batting" expanded={expanded.teamBatting} onToggle={() => toggle('teamBatting')}>
    <GameTeamStatsTable stats={teamBattingStats} awayAbbr={game.away_team_abbreviation} homeAbbr={game.home_team_abbreviation} />
  </GameDetailTableSection>

  <GameDetailTableSection title="Team Pitching" expanded={expanded.teamPitching} onToggle={() => toggle('teamPitching')}>
    <GameTeamStatsTable stats={teamPitchingStats} awayAbbr={game.away_team_abbreviation} homeAbbr={game.home_team_abbreviation} />
  </GameDetailTableSection>

  <GameDetailTableSection title="Team Fielding" expanded={expanded.teamFielding} onToggle={() => toggle('teamFielding')}>
    <GameTeamStatsTable stats={teamFieldingStats} awayAbbr={game.away_team_abbreviation} homeAbbr={game.home_team_abbreviation} />
  </GameDetailTableSection>

  {#if awayLineup.length > 0}
  <GameDetailTableSection title={`${game.away_team_abbreviation} Batting Lineup`} expanded={expanded.awayLineup} onToggle={() => toggle('awayLineup')}>
    <GameBattingTable players={awayLineup} bench={awayBench} benchExpanded={expanded.awayBench} onToggleBench={() => toggle('awayBench')} />
  </GameDetailTableSection>
  {/if}

  {#if homeLineup.length > 0}
  <GameDetailTableSection title={`${game.home_team_abbreviation} Batting Lineup`} expanded={expanded.homeLineup} onToggle={() => toggle('homeLineup')}>
    <GameBattingTable players={homeLineup} bench={homeBench} benchExpanded={expanded.homeBench} onToggleBench={() => toggle('homeBench')} />
  </GameDetailTableSection>
  {/if}

  {#if awayPitchers.length > 0}
  <GameDetailTableSection title={`${game.away_team_abbreviation} Pitching`} expanded={expanded.awayPitching} onToggle={() => toggle('awayPitching')}>
    <GamePitchingTable pitchers={awayPitchers} />
  </GameDetailTableSection>
  {/if}

  {#if homePitchers.length > 0}
  <GameDetailTableSection title={`${game.home_team_abbreviation} Pitching`} expanded={expanded.homePitching} onToggle={() => toggle('homePitching')}>
    <GamePitchingTable pitchers={homePitchers} />
  </GameDetailTableSection>
  {/if}

  <div class="px-6 py-4 bg-zinc-950/80 text-xs sm:text-sm text-zinc-500 flex flex-wrap gap-x-6 gap-y-2">
    <span><span class="text-zinc-600 mr-1">Season</span> {game.season}</span>
    {#if game.pool_group && game.pool_group.toLowerCase().includes('pool')}<span><span class="text-zinc-600 mr-1">Pool</span> {game.pool_group}</span>{/if}
    <span><span class="text-zinc-600 mr-1">Venue</span> {game.venue_name}</span>
  </div>
</div>
