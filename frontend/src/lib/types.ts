// ─── WBC Dashboard Types ─────────────────────────────────────────────────────

export type PoolTeam = {
  season: number;
  pool_group: string;
  team_id: number;
  team_name: string;
  team_abbreviation: string;
  pool_wins: number;
  pool_losses: number;
  pool_win_pct: number;
  pool_run_differential: number;
  pool_runs_scored: number;
  pool_runs_allowed: number;
};

export type FullGame = {
  game_pk: number;
  season: number;
  official_date: string;
  game_type: string;
  round_label: string;
  round_order: number;
  away_team_name: string;
  away_team_abbreviation: string;
  away_score: number;
  away_is_winner: boolean;
  home_team_name: string;
  home_team_abbreviation: string;
  home_score: number;
  home_is_winner: boolean;
  is_mercy_rule: boolean;
  venue_name: string;
  away_innings: number[];
  home_innings: number[];
  away_r: number;
  away_h: number;
  away_e: number;
  home_r: number;
  home_h: number;
  home_e: number;
  pool_group: string | null;
  is_one_run_game: boolean;
  run_margin: number;
  total_runs: number;
};

export type Bracket = {
  qf: FullGame[];
  sf: FullGame[];
  final: FullGame | null;
};

export type SeasonTeamTotal = {
  team_name: string;
  team_abbreviation: string;
  total_runs_scored: number;
  total_runs_allowed: number;
  total_run_differential: number;
};

export type MainPageData = {
  seasons: number[];
  pools: Record<string, Record<string, PoolTeam[]>>;
  brackets: Record<string, Bracket>;
  recentGames: FullGame[];
  allGames: FullGame[];
  seasonTeamTotals: Record<string, Record<string, SeasonTeamTotal>>;
};