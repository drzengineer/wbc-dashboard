import { supabase } from "$lib/server/db";
import type { PageServerLoad } from "./$types";

export const load: PageServerLoad = async () => {
	const { data: games } = await supabase
		.from("game_results")
		.select("*")
		.eq("abstract_game_state", "Final")
		.order("official_date", { ascending: false });

	return { games: games ?? [] };
};
