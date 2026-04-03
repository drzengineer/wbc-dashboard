// src/routes/players/[id]/+page.server.ts

import { error } from "@sveltejs/kit";
import { supabase } from "$lib/server/db";
import type { PageServerLoad } from "./$types";

export const load: PageServerLoad = async ({ params }) => {
	const personId = Number(params.id);
	if (!personId || Number.isNaN(personId)) throw error(404, "Player not found");

	// Fetch tournament stats and game logs in parallel
	const [{ data: tournamentStats }, { data: gameLogs }] = await Promise.all([
		supabase
			.from("player_tournament_stats")
			.select("*")
			.eq("person_id", personId)
			.order("season", { ascending: false }),

		supabase
			.from("player_game_stats")
			.select("*")
			.eq("person_id", personId)
			.order("season", { ascending: false })
			.order("official_date", { ascending: true }),
	]);

	if (!tournamentStats || tournamentStats.length === 0) {
		throw error(404, "Player not found");
	}

	// Fetch game results only for games this player appeared in
	const gamePks = [...new Set((gameLogs ?? []).map((g: any) => g.game_pk))];
	let gameResults: any[] = [];
	if (gamePks.length > 0) {
		const { data } = await supabase
			.from("game_results")
			.select("*")
			.in("game_pk", gamePks);
		gameResults = data ?? [];
	}

	// Build lookup map and merge in one pass
	const gameResultMap: Record<number, any> = Object.fromEntries(
		gameResults.map((gr) => [gr.game_pk, gr]),
	);

	const mergedLogs = (gameLogs ?? []).map((g: any) => ({
		...g,
		_gr: gameResultMap[g.game_pk] ?? null,
	}));

	// Fetch max values per season for radar chart and gauge scaling
	const seasons = [...new Set(tournamentStats.map((s: any) => s.season))];

	const maxStatsBySeason: Record<number, any> = {};

	await Promise.all(
		seasons.map(async (season) => {
			const [
				avgMax,
				obpMax,
				slgMax,
				opsMax,
				hrMax,
				rbiMax,
				sbMax,
				soMax,
				ipMax,
				wMax,
				svMax,
				gMax,
				bfMax,
			] = await Promise.all([
				supabase.from("player_tournament_stats").select("season_batting_avg").eq("season", season).not("season_batting_avg", "is", null).order("season_batting_avg", { ascending: false }).limit(1).maybeSingle(),
				supabase.from("player_tournament_stats").select("season_batting_obp").eq("season", season).not("season_batting_obp", "is", null).order("season_batting_obp", { ascending: false }).limit(1).maybeSingle(),
				supabase.from("player_tournament_stats").select("season_batting_slg").eq("season", season).not("season_batting_slg", "is", null).order("season_batting_slg", { ascending: false }).limit(1).maybeSingle(),
				supabase.from("player_tournament_stats").select("season_batting_ops").eq("season", season).not("season_batting_ops", "is", null).order("season_batting_ops", { ascending: false }).limit(1).maybeSingle(),
				supabase.from("player_tournament_stats").select("season_batting_hr").eq("season", season).not("season_batting_hr", "is", null).order("season_batting_hr", { ascending: false }).limit(1).maybeSingle(),
				supabase.from("player_tournament_stats").select("season_batting_rbi").eq("season", season).not("season_batting_rbi", "is", null).order("season_batting_rbi", { ascending: false }).limit(1).maybeSingle(),
				supabase.from("player_tournament_stats").select("season_batting_sb").eq("season", season).not("season_batting_sb", "is", null).order("season_batting_sb", { ascending: false }).limit(1).maybeSingle(),
				supabase.from("player_tournament_stats").select("season_pitching_so").eq("season", season).not("season_pitching_so", "is", null).order("season_pitching_so", { ascending: false }).limit(1).maybeSingle(),
				supabase.from("player_tournament_stats").select("season_pitching_ip").eq("season", season).not("season_pitching_ip", "is", null).order("season_pitching_ip", { ascending: false }).limit(1).maybeSingle(),
				supabase.from("player_tournament_stats").select("season_pitching_w").eq("season", season).not("season_pitching_w", "is", null).order("season_pitching_w", { ascending: false }).limit(1).maybeSingle(),
				supabase.from("player_tournament_stats").select("season_pitching_sv").eq("season", season).not("season_pitching_sv", "is", null).order("season_pitching_sv", { ascending: false }).limit(1).maybeSingle(),
				supabase.from("player_tournament_stats").select("games_played").eq("season", season).not("games_played", "is", null).order("games_played", { ascending: false }).limit(1).maybeSingle(),
				supabase.from("player_tournament_stats").select("season_pitching_bf").eq("season", season).not("season_pitching_bf", "is", null).order("season_pitching_bf", { ascending: false }).limit(1).maybeSingle(),
			]);

			maxStatsBySeason[season] = {
				batting: {
					season_batting_avg: avgMax?.data?.season_batting_avg,
					season_batting_obp: obpMax?.data?.season_batting_obp,
					season_batting_slg: slgMax?.data?.season_batting_slg,
					season_batting_ops: opsMax?.data?.season_batting_ops,
					season_batting_hr: hrMax?.data?.season_batting_hr,
					season_batting_rbi: rbiMax?.data?.season_batting_rbi,
					season_batting_sb: sbMax?.data?.season_batting_sb,
				},
				pitching: {
					season_pitching_so: soMax?.data?.season_pitching_so,
					season_pitching_ip: ipMax?.data?.season_pitching_ip,
					season_pitching_w: wMax?.data?.season_pitching_w,
					season_pitching_sv: svMax?.data?.season_pitching_sv,
					games_played: gMax?.data?.games_played,
					season_pitching_bf: bfMax?.data?.season_pitching_bf,
				},
			};
		})
	);

	return {
		player: tournamentStats[0],
		tournamentStats,
		gameLogs: mergedLogs,
		maxStatsBySeason,
	};
};
