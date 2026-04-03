// ─── Supabase Row Types ───────────────────────────────────────────────────────

export interface GameResult {
	game_pk: number;
	season: number;
	official_date: string;
	day_night: string | null;
	game_type: "F" | "D" | "L" | "W";
	round_label: string | null;
	round_order: number;
	tournament_format: string;
	pool_label: string | null;
	pool_display: string | null;
	away_team_name: string | null;
	away_team_abbreviation: string | null;
	away_team_id: number | null;
	home_team_name: string | null;
	home_team_abbreviation: string | null;
	home_team_id: number | null;
	away_score: number | null;
	home_score: number | null;
	away_is_winner: boolean | null;
	home_is_winner: boolean | null;
	winning_team_name: string | null;
	winning_team_abbreviation: string | null;
	run_margin: number | null;
	abstract_game_state: string;
	detailed_state: string | null;
	is_mercy_rule: boolean | null;
	venue_name: string | null;
	description: string | null;
	series_description: string | null;
	if_necessary: string | null;
	away_team_is_placeholder: boolean | null;
	home_team_is_placeholder: boolean | null;
}

export interface Standing {
	season: number;
	round: number;
	pool_label: string | null;
	pool_display: string | null;
	tournament_format: string;
	team_name: string;
	team_abbreviation: string;
	pool_gp: number;
	pool_wins: number;
	pool_losses: number;
	pool_run_differential: number | null;
	pool_runs_scored: number | null;
	pool_runs_allowed: number | null;
	pool_win_pct: number | null;
	is_champion: boolean | null;
}

export interface PlayerTournamentStat {
	person_id: number;
	season: number;
	full_name: string;
	represented_country: string;
	team_name: string | null;
	team_abbreviation: string | null;
	position_abbreviation: string | null;
	position_type: string | null;
	games_played: number | null;
	birth_date: string | null;
	birth_country: string | null;
	bat_side: string | null;
	pitch_hand: string | null;
	height: string | null;
	weight: number | null;
	mlb_debut_date: string | null;
	is_active: boolean | null;
	season_batting_avg: string | null;
	season_batting_obp: string | null;
	season_batting_slg: string | null;
	season_batting_ops: string | null;
	season_batting_ab: number | null;
	season_batting_h: number | null;
	season_batting_hr: number | null;
	season_batting_rbi: number | null;
	season_batting_r: number | null;
	season_batting_bb: number | null;
	season_batting_so: number | null;
	season_batting_sb: number | null;
	season_pitching_ip_raw: string | null;
	season_pitching_ip: number | null;
	season_pitching_era: string | null;
	season_pitching_w: number | null;
	season_pitching_l: number | null;
	season_pitching_sv: number | null;
	season_pitching_so: number | null;
	season_pitching_bb: number | null;
	season_pitching_bf: number | null;
}

export interface PlayerGameStat {
	game_pk: number;
	season: number;
	official_date: string | null;
	team_side: string | null;
	team_abbreviation: string | null;
	team_name: string | null;
	represented_country: string | null;
	person_id: number;
	full_name: string | null;
	birth_date: string | null;
	birth_country: string | null;
	bat_side: string | null;
	pitch_hand: string | null;
	position_abbreviation: string | null;
	position_type: string | null;
	height: string | null;
	weight: number | null;
	mlb_debut_date: string | null;
	jersey_number: string | null;
	batting_order: number | null;
	batting_order_raw: number | null;
	is_on_bench: boolean | null;
	is_substitute: boolean | null;
	batting_ab: number | null;
	batting_h: number | null;
	batting_2b: number | null;
	batting_3b: number | null;
	batting_hr: number | null;
	batting_rbi: number | null;
	batting_r: number | null;
	batting_bb: number | null;
	batting_so: number | null;
	batting_sb: number | null;
	batting_lob: number | null;
	batting_sf: number | null;
	batting_hbp: number | null;
	batting_avg: string | null;
	pitching_ip_raw: string | null;
	pitching_ip: number | null;
	pitching_er: number | null;
	pitching_r: number | null;
	pitching_so: number | null;
	pitching_bb: number | null;
	pitching_h: number | null;
	pitching_hr: number | null;
	pitching_bf: number | null;
	pitching_w: number | null;
	pitching_l: number | null;
	pitching_sv: number | null;
	pitching_era: string | null;
	_gr?: GameResult | null;
}

// ─── Page Data Types ──────────────────────────────────────────────────────────

export interface DashboardData {
	standings: Standing[];
	recentGames: GameResult[];
	knockoutGames: GameResult[];
}

export interface GamesData {
	games: GameResult[];
}

export interface PlayersData {
	batters: PlayerTournamentStat[];
	pitchers: PlayerTournamentStat[];
}

export interface PlayerDetailData {
	player: PlayerTournamentStat;
	tournamentStats: PlayerTournamentStat[];
	gameLogs: (PlayerGameStat & { _gr?: GameResult | null })[];
}

// ─── UI Types ─────────────────────────────────────────────────────────────────

export interface NavItem {
	href: string;
	label: string;
	icon: any;
}

export interface StatItem {
	label: string;
	value: string | number;
	color?: string;
}

export interface RadarStat {
	label: string;
	value: number;
	max: number;
}
