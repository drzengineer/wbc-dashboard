// src/routes/players/[id]/+page.server.ts

import { error } from "@sveltejs/kit";
import { supabase } from "$lib/server/db";
import type { PageServerLoad } from "./$types";

export const load: PageServerLoad = async ({ params }) => {
	const personId = Number(params.id);
	if (!personId || Number.isNaN(personId)) throw error(404, "Player not found");

	// Single query to app layer table - all data pre-joined, pre-calculated
	const { data, error: dbError } = await supabase
		.from("app_player_details")
		.select("*")
		.eq("person_id", personId)
		.maybeSingle();

	if (dbError || !data) {
		throw error(404, "Player not found");
	}

	return {
		player: data, // Return the full record so bio fields are accessible
		tournamentStats: data.tournament_stats,
		gameLogs: data.game_logs,
		maxStatsBySeason: data.max_stats_by_season,
		careerBatting: data.career_batting,
		careerPitching: data.career_pitching,
	};
};
