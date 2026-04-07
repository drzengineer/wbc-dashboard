import { supabase } from "$lib/server/db";
import type { PageServerLoad } from "./$types";
import type { MainPageData, GameStats, PoolTeam, FullGame } from "$lib/types";

export const load: PageServerLoad<MainPageData> = async () => {
  // 1. Fetch data in parallel
  const [stats, standings, results] = await Promise.all([
    supabase.from("dim_games").select("game_pk, season, pool_group, is_one_run_game, is_mercy_rule, run_margin, total_runs"),
    supabase.from("app_pool_standings").select("*"),
    supabase.from("app_game_results").select("*")
  ]);

  const allGames = results.data ?? [];

  // 2. Group Pools by Season and Group Name
  const pools: MainPageData["pools"] = {};
  standings.data?.forEach(team => {
    pools[team.season] ??= {};
    (pools[team.season][team.pool_group] ??= []).push(team);
  });

  // 3. Simple Bracket Grouping
  const brackets: MainPageData["brackets"] = {};
  allGames.forEach(game => {
    brackets[game.season] ??= { qf: [], sf: [], final: null };
    const b = brackets[game.season];

    if (game.round_label === "Quarterfinals") b.qf.push(game);
    else if (game.round_label === "Semifinals") b.sf.push(game);
    else if (game.round_label === "Championship") b.final = game;
  });

  // 4. Calculate Season Totals (DRY approach)
  const seasonTeamTotals: MainPageData["seasonTeamTotals"] = {};
  allGames.forEach(game => {
    seasonTeamTotals[game.season] ??= {};
    const season = seasonTeamTotals[game.season];

    const addStats = (name: string, abbr: string, scored: number, allowed: number) => {
      season[name] ??= { team_name: name, team_abbreviation: abbr, total_runs_scored: 0, total_runs_allowed: 0, total_run_differential: 0 };
      const t = season[name];
      t.total_runs_scored += scored;
      t.total_runs_allowed += allowed;
      t.total_run_differential += (scored - allowed);
    };

    addStats(game.away_team_name, game.away_team_abbreviation, game.away_score, game.home_score);
    addStats(game.home_team_name, game.home_team_abbreviation, game.home_score, game.away_score);
  });

  return {
    seasons: [...new Set(allGames.map(g => g.season))],
    games: stats.data ?? [],
    pools,
    brackets,
    recentGames: allGames.slice(0, 10),
    allGames,
    seasonTeamTotals
  };
};