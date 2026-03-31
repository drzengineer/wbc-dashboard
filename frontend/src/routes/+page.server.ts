import { supabase } from "$lib/server/db";
import type { PageServerLoad } from "./$types";

export const load: PageServerLoad = async () => {
	const { data: standings, error: e1 } = await supabase
		.from("standings")
		.select("*")
		.order("season", { ascending: false })
		.order("pool_win_pct", { ascending: false });

	const { data: recentGames, error: e2 } = await supabase
		.from("game_results")
		.select("*")
		.eq("abstract_game_state", "Final")
		.order("official_date", { ascending: false })
		.limit(10);

	const { data: knockoutGames, error: e3 } = await supabase
		.from("game_results")
		.select("*")
		.in("game_type", ["D", "L", "W"])
		.eq("abstract_game_state", "Final")
		.order("season", { ascending: false })
		.order("official_date", { ascending: true });

	// console.log('standings:', standings?.length, e1);
	// console.log('recentGames:', recentGames?.length, e2);
	// console.log('knockoutGames:', knockoutGames?.length, e3);

	return { standings: standings ?? [], recentGames: recentGames ?? [], knockoutGames: knockoutGames ?? [] };
};