// src/routes/games/+page.server.ts
import { supabase } from '$lib/server/db';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async () => {
  const { data: games } = await supabase
    .from('game_results')
    .select('game_pk,season,official_date,day_night,round_label,round_order,pool_display,pool_label,game_type,away_team_name,away_team_abbreviation,home_team_name,home_team_abbreviation,away_score,home_score,winning_team_name,winning_team_abbreviation,run_margin,is_mercy_rule,venue_name')
    .eq('abstract_game_state', 'Final')
    .order('season', { ascending: false })
    .order('official_date', { ascending: false });

  return { games: games ?? [] };
};