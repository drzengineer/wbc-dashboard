// src/routes/players/[id]/+page.server.ts
import { supabase } from '$lib/server/db';
import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ params }) => {
  const personId = Number(params.id);
  if (!personId || isNaN(personId)) throw error(404, 'Player not found');

  // Fetch tournament stats and game logs in parallel
  const [{ data: tournamentStats }, { data: gameLogs }] = await Promise.all([
    supabase
      .from('player_tournament_stats')
      .select('*')
      .eq('person_id', personId)
      .order('season', { ascending: false }),

    supabase
      .from('player_game_stats')
      .select('game_pk,season,official_date,team_abbreviation,team_side,represented_country,position_abbreviation,position_type,batting_order,is_on_bench,is_substitute,batting_ab,batting_h,batting_2b,batting_3b,batting_hr,batting_rbi,batting_r,batting_bb,batting_so,batting_sb,batting_avg,pitching_ip,pitching_er,pitching_r,pitching_so,pitching_bb,pitching_h,pitching_hr,pitching_bf,pitching_w,pitching_l,pitching_sv,pitching_era')
      .eq('person_id', personId)
      .order('season', { ascending: false })
      .order('official_date', { ascending: true }),
  ]);

  if (!tournamentStats || tournamentStats.length === 0) {
    throw error(404, 'Player not found');
  }

  // Fetch game results only for games this player appeared in
  const gamePks = [...new Set((gameLogs ?? []).map((g: any) => g.game_pk))];
  let gameResults: any[] = [];
  if (gamePks.length > 0) {
    const { data } = await supabase
      .from('game_results')
      .select('game_pk,away_team_abbreviation,home_team_abbreviation,away_score,home_score,round_label,pool_display')
      .in('game_pk', gamePks);
    gameResults = data ?? [];
  }

  // Build lookup map and merge in one pass
  const gameResultMap: Record<number, any> = Object.fromEntries(
    gameResults.map(gr => [gr.game_pk, gr])
  );

  const mergedLogs = (gameLogs ?? []).map((g: any) => ({
    ...g,
    _gr: gameResultMap[g.game_pk] ?? null,
  }));

  return {
    player: tournamentStats[0],
    tournamentStats,
    gameLogs: mergedLogs,
  };
};