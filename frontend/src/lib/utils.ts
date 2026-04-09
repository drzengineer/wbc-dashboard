// ─── Number Formatting ────────────────────────────────────────────────────────

/** Format nullable number, returning '—' for null/undefined */
export function fmtNum(v: unknown): string {
	return v != null ? String(v) : "—";
}

/** Format batting average (strips leading zero) */
export function fmtAvg(v: unknown): string {
	if (!v) return "—";
	return String(v).replace(/^0/, "");
}

/** Format innings pitched (decimal to display) */
export function fmtIp(v: unknown): string {
	if (v == null) return "—";
	const full = Math.floor(Number(v));
	const frac = Math.round((Number(v) - full) * 3);
	return frac === 0 ? `${full}.0` : `${full}.${frac}`;
}

/** Format win percentage */
export function pct(val: unknown): string {
	const n = Number(val);
	if (Number.isNaN(n)) return "—";
	if (n === 1) return "1.000";
	if (n === 0) return ".000";
	return n.toFixed(3).replace("0.", ".");
}

// ─── Date Formatting ──────────────────────────────────────────────────────────

/** Format date string to 'Mon DD' */
export function fmtDate(d: string): string {
	return new Date(`${d}T00:00:00`).toLocaleDateString("en-US", {
		month: "short",
		day: "numeric",
	});
}

/** Format date string to 'Mon DD, YYYY' */
export function fmtDateFull(d: string): string {
	return new Date(`${d}T00:00:00`).toLocaleDateString("en-US", {
		month: "short",
		day: "numeric",
		year: "numeric",
	});
}

/** Calculate age from birth date */
export function age(birthDate: string): number | null {
	if (!birthDate) return null;
	const diff = Date.now() - new Date(birthDate).getTime();
	return Math.floor(diff / (365.25 * 24 * 3600 * 1000));
}

// ─── Baseball Helpers ─────────────────────────────────────────────────────────

/** Get round label from game */
export function roundLabel(game: {
	round_label?: string | null;
	game_type?: string;
	pool_display?: string | null;
}): string {
	if (game.round_label) return game.round_label;
	const type = game.game_type;
	if (type === "W") return "Championship";
	if (type === "L") return "Semifinals";
	if (type === "D") return "Quarterfinals";
	return game.pool_display ?? type ?? "—";
}

/** Round sort order (lower = later round) */
export function roundOrder(label: string): number {
	const order: Record<string, number> = {
		Championship: 0,
		Semifinals: 1,
		Quarterfinals: 2,
	};
	return label in order ? order[label] : 10;
}

/** Get badge class for round label */
export function roundBadgeClass(label: string): string {
	if (label === "Championship") return "badge-championship";
	if (label === "Semifinals") return "badge-semifinals";
	if (label === "Quarterfinals") return "badge-quarterfinals";
	return "badge-default";
}

/**
 * Builds TeamStats object from flat GameDetailRow
 */
import type { GameDetailRow, TeamStats } from './types';

export function buildTeamStats(row: GameDetailRow, side: 'away' | 'home'): TeamStats {
  const p = (k: string) => (row as any)[`${side}_${k}`] ?? 0;
  return {
    team_id: p('team_id'),
    team_name: side === 'away' ? row.away_team_name : row.home_team_name,
    team_abbreviation: side === 'away' ? row.away_team_abbreviation : row.home_team_abbreviation,
    score: side === 'away' ? row.away_score : row.home_score,
    is_winner: side === 'away' ? row.away_is_winner : row.home_is_winner,
    batting: {
      pa: p('batting_pa'), ab: p('batting_ab'), runs: p('batting_runs'),
      hits: p('batting_hits'), doubles: p('batting_doubles'), triples: p('batting_triples'),
      hr: p('batting_hr'), rbi: p('batting_rbi'), bb: p('batting_bb'),
      ibb: p('batting_ibb'), so: p('batting_so'), hbp: p('batting_hbp'),
      sac: p('batting_sac'), sf: p('batting_sf'), sb: p('batting_sb'),
      cs: p('batting_cs'), lob: p('batting_lob'), tb: p('batting_tb'),
      gidp: p('batting_gidp'),
    },
    pitching: {
      outs: p('pitching_outs'), total_pitches: p('pitching_total_pitches'),
      strikes: p('pitching_strikes'), balls: p('pitching_balls'),
      hits_allowed: p('pitching_hits_allowed'), runs_allowed: p('pitching_runs_allowed'),
      er: p('pitching_er'), hr_allowed: p('pitching_hr_allowed'),
      so: p('pitching_so'), bb: p('pitching_bb'), hbp: p('pitching_hbp'),
      wp: p('pitching_wp'), bk: p('pitching_bk'), bf: p('pitching_bf'),
    },
    fielding: {
      errors: p('fielding_errors'), assists: p('fielding_assists'),
      put_outs: p('fielding_put_outs'), chances: p('fielding_chances'),
      passed_balls: p('fielding_passed_balls'), pickoffs: p('fielding_pickoffs'),
    },
  };
}

// ─── CSS Class Helpers ────────────────────────────────────────────────────────

/** Conditional class joiner */
export function cn(...classes: (string | false | null | undefined)[]): string {
	return classes.filter(Boolean).join(" ");
}
