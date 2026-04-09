import { supabase } from "$lib/server/db";
import type { PageServerLoad } from "./$types";
import type { GameDetailRow, TeamStats, FullGame } from "$lib/types";

// ─── Helper: assemble TeamStats from a flat row ───────────────────────────────

function buildTeamStats(row: GameDetailRow, side: 'away' | 'home'): TeamStats {
  const p = (k: string) => (row as any)[`${side}_${k}`] ?? 0;
  return {
    team_id: p('team_id'),
    team_name: side === 'away' ? row.away_team_name : row.home_team_name,
    team_abbreviation: side === 'away' ? row.away_team_abbreviation : row.home_team_abbreviation,
    score: side === 'away' ? row.away_score : row.home_score,
    is_winner: side === 'away' ? row.away_is_winner : row.home_is_winner,
    batting: {
      pa: p('batting_pa'), ab: p('batting_ab'), runs: p('batting_runs'),
      hits: p('batting_hits'), doubles: p('batting_doubles'), triples: p('batting_triples'),
      hr: p('batting_hr'), rbi: p('batting_rbi'), bb: p('batting_bb'),
      ibb: p('batting_ibb'), so: p('batting_so'), hbp: p('batting_hbp'),
      sac: p('batting_sac'), sf: p('batting_sf'), sb: p('batting_sb'),
      cs: p('batting_cs'), lob: p('batting_lob'), tb: p('batting_tb'),
      gidp: p('batting_gidp'),
    },
    pitching: {
      outs: p('pitching_outs'), total_pitches: p('pitching_total_pitches'),
      strikes: p('pitching_strikes'), balls: p('pitching_balls'),
      hits_allowed: p('pitching_hits_allowed'), runs_allowed: p('pitching_runs_allowed'),
      er: p('pitching_er'), hr_allowed: p('pitching_hr_allowed'),
      so: p('pitching_so'), bb: p('pitching_bb'), hbp: p('pitching_hbp'),
      wp: p('pitching_wp'), bk: p('pitching_bk'), bf: p('pitching_bf'),
    },
    fielding: {
      errors: p('fielding_errors'), assists: p('fielding_assists'),
      put_outs: p('fielding_put_outs'), chances: p('fielding_chances'),
      passed_balls: p('fielding_passed_balls'), pickoffs: p('fielding_pickoffs'),
    },
  };
}

// ─── Load ─────────────────────────────────────────────────────────────────────

export const load: PageServerLoad = async () => {
  // ✅ Optimized: Load ONLY lightweight game results for list view
  const { data, error } = await supabase
    .from("app_game_results")
    .select("*");

  if (error) {
    console.error("❌ app_game_results query error:", error);
  }

  const games: FullGame[] = data ?? [];

  // Sort games: most recent first
  games.sort((a, b) => b.official_date.localeCompare(a.official_date));

  // ── Derive season list and pool map ─────────────────────────────────────────
  const seasonSet = new Set<number>();
  const poolsMap: Record<number, string[]> = {};

  for (const g of games) {
    seasonSet.add(g.season);
    if (g.pool_group) {
      poolsMap[g.season] ??= [];
      if (!poolsMap[g.season].includes(g.pool_group)) {
        poolsMap[g.season].push(g.pool_group);
      }
    }
  }

  const seasons = [...seasonSet].sort((a, b) => b - a);
  Object.keys(poolsMap).forEach(s => poolsMap[Number(s)].sort());

  return { seasons, pools: poolsMap, games };
};