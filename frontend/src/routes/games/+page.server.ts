import { supabase } from "$lib/server/db";
import type { PageServerLoad } from "./$types";
import type { FullGame } from "$lib/types";

export const load: PageServerLoad = async () => {
  // 1. Fetch data in parallel
  const [games, results] = await Promise.all([
    supabase.from("dim_games").select("*"),
    supabase.from("app_game_results").select("*")
  ]);

  const allGames = results.data ?? [];
  const gameinfo = games.data ?? [];

  // Create lookup map for game metadata
  const gameLookup = new Map(gameinfo.map(g => [g.game_pk, g]));

  // Merge pool_group and metadata onto each game
  allGames.forEach(game => {
    const meta = gameLookup.get(game.game_pk);
    if (meta) {
      game.pool_group = meta.pool_group;
      game.is_one_run_game = meta.is_one_run_game;
      game.is_mercy_rule = meta.is_mercy_rule;
    }
  });

  // Extract pool groups per season
  const pools: Record<number, string[]> = {};
  allGames.forEach(game => {
    if (game.pool_group) {
      pools[game.season] ??= [];
      if (!pools[game.season].includes(game.pool_group)) {
        pools[game.season].push(game.pool_group);
      }
    }
  });

  // Sort pools alphabetically
  Object.keys(pools).forEach(season => {
    pools[Number(season)].sort();
  });

  return {
    seasons: [...new Set(allGames.map(g => g.season))],
    pools,
    games: allGames
  };
};