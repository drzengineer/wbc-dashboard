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

// ─── CSS Class Helpers ────────────────────────────────────────────────────────

/** Conditional class joiner */
export function cn(...classes: (string | false | null | undefined)[]): string {
	return classes.filter(Boolean).join(" ");
}
