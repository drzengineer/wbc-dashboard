import { supabase } from "$lib/server/db";
import type { PageServerLoad } from "./$types";

export const load: PageServerLoad = async () => {
	// Run all three queries in parallel instead of sequentially
	const [{ data: standings }, { data: recentGames }, { data: knockoutGames }] =
		await Promise.all([
			supabase
				.from("standings")
				.select("*")
				.order("season", { ascending: false })
				.order("pool_win_pct", { ascending: false }),

			supabase
				.from("game_results")
				.select("*")
				.eq("abstract_game_state", "Final")
				.order("official_date", { ascending: false })
				.limit(10),

			supabase
				.from("game_results")
				.select("*")
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
