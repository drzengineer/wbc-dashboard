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
      .select('*')
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
      .select('*')
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