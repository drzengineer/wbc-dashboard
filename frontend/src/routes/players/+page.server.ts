// src/routes/players/+page.server.ts
import { supabase } from '$lib/server/db';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async () => {
  // Fetch batters and pitchers in parallel, select only needed columns
  const [{ data: batters }, { data: pitchers }] = await Promise.all([
    supabase
      .from('player_tournament_stats')
      .select('person_id,season,full_name,represented_country,team_abbreviation,position_abbreviation,position_type,games_played,season_batting_avg,season_batting_obp,season_batting_slg,season_batting_ops,season_batting_ab,season_batting_h,season_batting_hr,season_batting_rbi,season_batting_r,season_batting_bb,season_batting_so,season_batting_sb')
      .neq('position_type', 'Pitcher')
      .order('season', { ascending: false }),

    supabase
      .from('player_tournament_stats')
      .select('person_id,season,full_name,represented_country,team_abbreviation,position_abbreviation,position_type,games_played,season_pitching_era,season_pitching_ip,season_pitching_w,season_pitching_l,season_pitching_sv,season_pitching_so,season_pitching_bb,season_pitching_bf')
      .eq('position_type', 'Pitcher')
      .order('season', { ascending: false }),
  ]);

  return { batters: batters ?? [], pitchers: pitchers ?? [] };
};