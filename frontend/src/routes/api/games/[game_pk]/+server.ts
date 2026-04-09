import { json } from '@sveltejs/kit';
import { supabase } from "$lib/server/db";
import type { RequestHandler } from './$types';
import type { GameDetailRow, GameSummary } from "$lib/types";

function buildTeamStats(row: GameDetailRow, side: 'away' | 'home') {
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

export const GET: RequestHandler = async ({ params }) => {
  const gameId = Number(params.game_pk);
  
  const { data, error } = await supabase
    .from("app_game_detail")
    .select("*")
    .eq('game_pk', gameId);

  if (error) {
    console.error("❌ app_game_detail single game query error:", error);
    return json({ error: 'Failed to load game details' }, { status: 500 });
  }

  const rows: GameDetailRow[] = data ?? [];
  
  if (rows.length === 0) {
    return json({ error: 'Game not found' }, { status: 404 });
  }

  const r0 = rows[0];

  const gameSummary: GameSummary = {
    game_pk: gameId,
    season: r0.season,
    official_date: r0.official_date,
    round_label: r0.round_label,
    round_order: r0.round_order,
    game_type: r0.game_type,
    pool_group: r0.pool_group,
    is_mercy_rule: r0.is_mercy_rule,
    is_one_run_game: r0.is_one_run_game,
    run_margin: r0.run_margin,
    total_runs: r0.total_runs,
    venue_name: r0.venue_name,
    away_team_id: r0.away_team_id,
    away_team_name: r0.away_team_name,
    away_team_abbreviation: r0.away_team_abbreviation,
    away_score: r0.away_score,
    away_is_winner: r0.away_is_winner,
    home_team_id: r0.home_team_id,
    home_team_name: r0.home_team_name,
    home_team_abbreviation: r0.home_team_abbreviation,
    home_score: r0.home_score,
    home_is_winner: r0.home_is_winner,
    away_innings: r0.away_innings,
    home_innings: r0.home_innings,
    away_r: r0.away_r, away_h: r0.away_h, away_e: r0.away_e,
    home_r: r0.home_r, home_h: r0.home_h, home_e: r0.home_e,
    away_team: buildTeamStats(r0, 'away'),
    home_team: buildTeamStats(r0, 'home'),
    players: rows,
  };

  return json(gameSummary);
};