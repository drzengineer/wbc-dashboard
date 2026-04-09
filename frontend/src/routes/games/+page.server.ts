import { supabase } from "$lib/server/db";
import type { PageServerLoad } from "./$types";
import type { GameDetailRow, TeamStats, FullGame } from "$lib/types";
import { buildTeamStats } from '$lib/utils';

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