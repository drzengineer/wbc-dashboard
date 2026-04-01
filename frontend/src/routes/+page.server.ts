import { supabase } from "$lib/server/db";
import type { PageServerLoad } from "./$types";

export const load: PageServerLoad = async () => {
  // Run all three queries in parallel instead of sequentially
  const [
    { data: standings },
    { data: recentGames },
    { data: knockoutGames },
  ] = await Promise.all([
    supabase
      .from("standings")
      .select("season,pool_display,pool_label,team_name,team_abbreviation,pool_wins,pool_losses,pool_win_pct,pool_run_differential,is_champion,tournament_format")
      .order("season", { ascending: false })
      .order("pool_win_pct", { ascending: false }),

    supabase
      .from("game_results")
      .select("game_pk,season,official_date,round_label,pool_display,away_team_name,away_team_abbreviation,home_team_name,home_team_abbreviation,away_score,home_score,winning_team_abbreviation,game_type,is_mercy_rule")
      .eq("abstract_game_state", "Final")
      .order("official_date", { ascending: false })
      .limit(10),

    supabase
      .from("game_results")
      .select("game_pk,season,official_date,round_label,round_order,away_team_name,away_team_abbreviation,home_team_name,home_team_abbreviation,away_score,home_score,winning_team_abbreviation,game_type,away_team_is_placeholder")
      .in("game_type", ["D", "L", "W"])
      .eq("abstract_game_state", "Final")
      .order("season", { ascending: false })
      .order("official_date", { ascending: true }),
  ]);

  return {
    standings: standings ?? [],
    recentGames: recentGames ?? [],
    knockoutGames: knockoutGames ?? [],
  };
};