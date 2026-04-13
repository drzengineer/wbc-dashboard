// src/routes/players/+page.server.ts
import { supabase } from "$lib/server/db";
import type { PageServerLoad } from "./$types";

export const load: PageServerLoad = async () => {
	// Fetch batters and pitchers in parallel, select only needed columns
	const [{ data: batters }, { data: pitchers }] = await Promise.all([
		supabase
			.from("app_player_season_stats")
			.select("*")
			.neq("position_type", "Pitcher")
			.order("season", { ascending: false }),

		supabase
			.from("app_player_season_stats")
			.select("*")
			.eq("position_type", "Pitcher")
			.order("season", { ascending: false }),
	]);

	return { batters: batters ?? [], pitchers: pitchers ?? [] };
};
