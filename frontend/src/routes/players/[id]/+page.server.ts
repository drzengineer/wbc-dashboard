// src/routes/players/[id]/+page.server.ts
import { supabase } from '$lib/server/db';
import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ params }) => {
	const personId = Number(params.id);
	if (!personId || isNaN(personId)) throw error(404, 'Player not found');

	// All tournament seasons for this player
	const { data: tournamentStats } = await supabase
		.from('player_tournament_stats')
		.select('*')
		.eq('person_id', personId)
		.order('season', { ascending: false });

	if (!tournamentStats || tournamentStats.length === 0) {
		throw error(404, 'Player not found');
	}

	// Game-by-game logs — player_game_stats doesn't have opponent or scores,
	// so we also fetch game_results and merge on game_pk client-side.
	const { data: gameLogs } = await supabase
		.from('player_game_stats')
		.select('*')
		.eq('person_id', personId)
		.order('season', { ascending: false })
		.order('official_date', { ascending: true });

	// Fetch game_results for all games this player appeared in so we can
	// show opponent abbreviation and final score in the game log.
	const gamePks = [...new Set((gameLogs ?? []).map((g: any) => g.game_pk))];
	let gameResults: any[] = [];
	if (gamePks.length > 0) {
		const { data } = await supabase
			.from('game_results')
			.select('game_pk, away_team_abbreviation, home_team_abbreviation, away_score, home_score, round_label, pool_display')
			.in('game_pk', gamePks);
		gameResults = data ?? [];
	}

	// Build a lookup map: game_pk → game_results row
	const gameResultMap: Record<number, any> = {};
	for (const gr of gameResults) {
		gameResultMap[gr.game_pk] = gr;
	}

	// Merge game_results fields onto each game log row
	const mergedLogs = (gameLogs ?? []).map((g: any) => ({
		...g,
		_gr: gameResultMap[g.game_pk] ?? null,
	}));

	return {
		player: tournamentStats[0], // bio from most recent season
		tournamentStats,
		gameLogs: mergedLogs,
	};
};