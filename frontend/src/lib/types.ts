// ─── WBC Dashboard Types ─────────────────────────────────────────────────────

export type Team = {
  team_id: number;
  team_name: string;
  team_abbreviation: string;
  division_id?: number;
  division_name?: string;
  league_name?: string;
};

export type Player = {
  player_id: number;
  full_name: string;
  use_name?: string;
  boxscore_name?: string;
  primary_number?: number;
  primary_position_code?: number;
  primary_position_name?: string;
  primary_position_abbreviation?: string;
  primary_position_type?: string;
  bat_side_code?: 'L' | 'R' | 'S';
  pitch_hand_code?: 'L' | 'R';
  height?: number;
  weight?: number;
  current_age?: number;
  birth_country?: string;
  mlb_debut_date?: string;
};

export type GameInning = {
  inning_num: number;
  ordinal_num: string;
  runs: number;
  hits: number;
  errors: number;
  left_on_base: number;
};

export type BattingStats = {
  plate_appearances: number;
  at_bats: number;
  runs: number;
  hits: number;
  doubles: number;
  triples: number;
  home_runs: number;
  rbi: number;
  walks: number;
  strikeouts: number;
  hit_by_pitch: number;
  sac_bunts: number;
  sac_flies: number;
  stolen_bases: number;
  caught_stealing: number;
  left_on_base: number;
  total_bases: number;
  gidp: number;
};

export type PitchingStats = {
  outs: number;
  hits_allowed: number;
  runs_allowed: number;
  earned_runs: number;
  home_runs_allowed: number;
  strikeouts: number;
  walks: number;
  hit_batsmen: number;
  wild_pitches: number;
  balks: number;
  total_pitches: number;
  strikes: number;
  balls: number;
  batters_faced: number;
  inherited_runners?: number;
  inherited_runners_scored?: number;
  wins?: number;
  losses?: number;
  saves?: number;
  holds?: number;
  blown_saves?: number;
  games_started?: number;
};

export type FieldingStats = {
  errors: number;
  assists: number;
  put_outs: number;
  chances: number;
  passed_balls: number;
  pickoffs: number;
};

export type GameTeamStats = {
  team_id: number;
  team_name: string;
  team_abbreviation: string;
  side: 'home' | 'away';
  is_winner: boolean;
  score: number;
  opponent_score: number;
  run_differential: number;
  batting: BattingStats;
  pitching: PitchingStats;
  fielding: FieldingStats;
  innings: GameInning[];
};

export type GamePlayerStats = {
  player_id: number;
  team_id: number;
  player: Player;
  batting_order?: number;
  is_on_bench: boolean;
  is_substitute: boolean;
  batting: Partial<BattingStats>;
  pitching?: Partial<PitchingStats>;
  fielding?: Partial<FieldingStats>;
};

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
  pool_standing?: number;
  is_qualified?: boolean;
};

export type FullGame = {
  game_pk: number;
  season: number;
  official_date: string;
  game_date?: string;
  game_type: string;
  tournament_round: string;
  pool_group: string;
  series_description?: string;
  series_game_number?: number;
  games_in_series?: number;
  venue_name: string;
  venue_id?: number;
  day_night?: 'day' | 'night';
  is_tie?: boolean;
  double_header?: boolean;
  tiebreaker?: boolean;
  is_mercy_rule: boolean;
  is_one_run_game: boolean;
  run_margin: number;
  total_runs: number;
  away_team_id: number;
  away_team_name: string;
  away_team_abbreviation: string;
  away_score: number;
  away_is_winner: boolean;
  home_team_id: number;
  home_team_name: string;
  home_team_abbreviation: string;
  home_score: number;
  home_is_winner: boolean;
  away_innings: number[];
  home_innings: number[];
  away_r: number;
  away_h: number;
  away_e: number;
  home_r: number;
  home_h: number;
  home_e: number;
  away_stats?: GameTeamStats;
  home_stats?: GameTeamStats;
  players?: GamePlayerStats[];
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

export type GameDetailRow = {
  // grain keys
  game_pk: number;
  player_id: number;
  team_id: number;

  // game header
  season: number;
  official_date: string;
  game_type: string;
  round_label: string;
  round_order: number;
  venue_name: string;
  pool_group: string;
  is_mercy_rule: boolean;
  is_one_run_game: boolean;
  run_margin: number;
  total_runs: number;

  // away team identity
  away_team_id: number;
  away_team_name: string;
  away_team_abbreviation: string;
  away_score: number;
  away_is_winner: boolean;

  // home team identity
  home_team_id: number;
  home_team_name: string;
  home_team_abbreviation: string;
  home_score: number;
  home_is_winner: boolean;

  // inning arrays & RHE
  away_innings: number[];
  home_innings: number[];
  away_r: number;  away_h: number;  away_e: number;
  home_r: number;  home_h: number;  home_e: number;

  // away team batting totals
  away_batting_pa: number; away_batting_ab: number; away_batting_runs: number;
  away_batting_hits: number; away_batting_doubles: number; away_batting_triples: number;
  away_batting_hr: number; away_batting_rbi: number; away_batting_bb: number;
  away_batting_ibb: number; away_batting_so: number; away_batting_hbp: number;
  away_batting_sac: number; away_batting_sf: number; away_batting_sb: number;
  away_batting_cs: number; away_batting_lob: number; away_batting_tb: number;
  away_batting_gidp: number;

  // away team pitching totals
  away_pitching_outs: number; away_pitching_total_pitches: number;
  away_pitching_strikes: number; away_pitching_balls: number;
  away_pitching_hits_allowed: number; away_pitching_runs_allowed: number;
  away_pitching_er: number; away_pitching_hr_allowed: number;
  away_pitching_so: number; away_pitching_bb: number; away_pitching_hbp: number;
  away_pitching_wp: number; away_pitching_bk: number; away_pitching_bf: number;

  // away fielding totals
  away_fielding_errors: number; away_fielding_assists: number;
  away_fielding_put_outs: number; away_fielding_chances: number;
  away_fielding_passed_balls: number; away_fielding_pickoffs: number;

  // home team batting totals (same shape)
  home_batting_pa: number; home_batting_ab: number; home_batting_runs: number;
  home_batting_hits: number; home_batting_doubles: number; home_batting_triples: number;
  home_batting_hr: number; home_batting_rbi: number; home_batting_bb: number;
  home_batting_ibb: number; home_batting_so: number; home_batting_hbp: number;
  home_batting_sac: number; home_batting_sf: number; home_batting_sb: number;
  home_batting_cs: number; home_batting_lob: number; home_batting_tb: number;
  home_batting_gidp: number;

  // home team pitching totals
  home_pitching_outs: number; home_pitching_total_pitches: number;
  home_pitching_strikes: number; home_pitching_balls: number;
  home_pitching_hits_allowed: number; home_pitching_runs_allowed: number;
  home_pitching_er: number; home_pitching_hr_allowed: number;
  home_pitching_so: number; home_pitching_bb: number; home_pitching_hbp: number;
  home_pitching_wp: number; home_pitching_bk: number; home_pitching_bf: number;

  // home fielding totals
  home_fielding_errors: number; home_fielding_assists: number;
  home_fielding_put_outs: number; home_fielding_chances: number;
  home_fielding_passed_balls: number; home_fielding_pickoffs: number;

  // player bio
  full_name: string | null;
  first_name: string | null;
  last_name: string | null;
  use_name: string | null;
  boxscore_name: string | null;
  birth_date: string | null;
  birth_city: string | null;
  birth_country: string | null;
  current_age: number | null;
  height: number | null;
  weight: number | null;
  bat_side_code: string | null;
  pitch_hand_code: string | null;
  primary_number: string | null;
  primary_position_code: string | null;
  primary_position_name: string | null;
  primary_position_type: string | null;
  primary_position_abbreviation: string | null;
  mlb_debut_date: string | null;

  // player game role
  batting_order: number | null;
  is_on_bench: boolean;
  is_substitute: boolean;
  is_current_batter: boolean;
  is_current_pitcher: boolean;

  // player batting
  player_batting_pa: number; player_batting_ab: number; player_batting_runs: number;
  player_batting_hits: number; player_batting_doubles: number; player_batting_triples: number;
  player_batting_hr: number; player_batting_rbi: number; player_batting_bb: number;
  player_batting_ibb: number; player_batting_so: number; player_batting_hbp: number;
  player_batting_sac: number; player_batting_sf: number; player_batting_sb: number;
  player_batting_cs: number; player_batting_lob: number; player_batting_tb: number;
  player_batting_gidp: number;

  // player pitching
  player_pitching_outs: number | null; player_pitching_total_pitches: number | null;
  player_pitching_strikes: number | null; player_pitching_balls: number | null;
  player_pitching_hits_allowed: number | null; player_pitching_runs_allowed: number | null;
  player_pitching_er: number | null; player_pitching_hr_allowed: number | null;
  player_pitching_so: number | null; player_pitching_bb: number | null;
  player_pitching_ibb: number | null; player_pitching_hbp: number | null;
  player_pitching_wp: number | null; player_pitching_bk: number | null;
  player_pitching_bf: number | null; player_pitching_ir: number | null;
  player_pitching_irs: number | null; player_pitching_wins: number | null;
  player_pitching_losses: number | null; player_pitching_saves: number | null;
  player_pitching_holds: number | null; player_pitching_bs: number | null;
  player_pitching_gs: number | null;

  // player fielding
  player_fielding_errors: number; player_fielding_assists: number;
  player_fielding_put_outs: number; player_fielding_chances: number;
  player_fielding_passed_balls: number; player_fielding_pickoffs: number;
};

export type GameSummary = {
  game_pk: number;
  season: number;
  official_date: string;
  round_label: string;
  round_order: number;
  game_type: string;
  pool_group: string;
  is_mercy_rule: boolean;
  is_one_run_game: boolean;
  run_margin: number;
  total_runs: number;
  venue_name: string;
  away_team_id: number;
  away_team_name: string;
  away_team_abbreviation: string;
  away_score: number;
  away_is_winner: boolean;
  home_team_id: number;
  home_team_name: string;
  home_team_abbreviation: string;
  home_score: number;
  home_is_winner: boolean;
  away_innings: number[];
  home_innings: number[];
  away_r: number; away_h: number; away_e: number;
  home_r: number; home_h: number; home_e: number;
  // team stats blobs
  away_team: TeamStats;
  home_team: TeamStats;
  // players grouped
  players: GameDetailRow[];
};

export type TeamStats = {
  team_id: number;
  team_name: string;
  team_abbreviation: string;
  score: number;
  is_winner: boolean;
  batting: {
    pa: number; ab: number; runs: number; hits: number; doubles: number; triples: number;
    hr: number; rbi: number; bb: number; ibb: number; so: number; hbp: number;
    sac: number; sf: number; sb: number; cs: number; lob: number; tb: number; gidp: number;
  };
  pitching: {
    outs: number; total_pitches: number; strikes: number; balls: number;
    hits_allowed: number; runs_allowed: number; er: number; hr_allowed: number;
    so: number; bb: number; hbp: number; wp: number; bk: number; bf: number;
  };
  fielding: {
    errors: number; assists: number; put_outs: number;
    chances: number; passed_balls: number; pickoffs: number;
  };
};

export type MainPageData = {
  seasons: number[];
  pools: Record<string, Record<string, PoolTeam[]>>;
  brackets: Record<string, Bracket>;
  recentGames: FullGame[];
  allGames: FullGame[];
  seasonTeamTotals: Record<string, Record<string, SeasonTeamTotal>>;
};