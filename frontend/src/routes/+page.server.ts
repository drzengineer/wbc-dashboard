import { supabase } from "$lib/server/db";
import type { PageServerLoad } from "./$types";

export const load: PageServerLoad = async () => {
	const { data: standings } = await supabase
		.from("standings")
		.select("*")
		.order("season", { ascending: false })
		.order("pool_win_pct", { ascending: false });

	const { data: recentGames } = await supabase
		.from("game_results")
		.select("*")
		.eq("abstract_game_state", "Final")
		.order("official_date", { ascending: false })
		.limit(10);

	return { standings: standings ?? [], recentGames: recentGames ?? [] };
};
