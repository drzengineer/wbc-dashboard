import { supabase } from '$lib/server/db';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async () => {
  const { data: batters } = await supabase
    .from('player_tournament_stats')
    .select('*')
    .neq('position_type', 'Pitcher')
    .order('season', { ascending: false });

  const { data: pitchers } = await supabase
    .from('player_tournament_stats')
    .select('*')
    .eq('position_type', 'Pitcher')
    .order('season', { ascending: false });

  return { batters: batters ?? [], pitchers: pitchers ?? [] };
};