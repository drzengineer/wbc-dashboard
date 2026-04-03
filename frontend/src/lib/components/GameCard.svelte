<script lang="ts">
import type { GameResult } from "$lib/types";
import { fmtDate, fmtDateFull, roundBadgeClass, roundLabel } from "$lib/utils";
import Flag from "./Flag.svelte";

let {
	game,
	compact = false,
	showFullDate = false,
}: {
	game: GameResult;
	compact?: boolean;
	showFullDate?: boolean;
} = $props();

let isChamp = $derived(game.game_type === "W");
let label = $derived(roundLabel(game));
let awayWon = $derived(!!game.away_is_winner);
let homeWon = $derived(!!game.home_is_winner);

function teamRow(
	abbr: string | null,
	name: string | null,
	score: number | null,
	isWinner: boolean,
	side: string,
) {
	return { abbr: abbr ?? name ?? "—", name, score, isWinner, side };
}

let rows = $derived([
	teamRow(
		game.away_team_abbreviation,
		game.away_team_name,
		game.away_score,
		awayWon,
		"Away",
	),
	teamRow(
		game.home_team_abbreviation,
		game.home_team_name,
		game.home_score,
		homeWon,
		"Home",
	),
]);
</script>

<div class="bg-surface border rounded-xl px-5 py-4 transition-all duration-200 hover:border-[#3a3a4a]
	{isChamp ? 'border-gold/40 shadow-lg shadow-gold/5' : 'border-border'}">
	
	<!-- Primary Row - Teams Only -->
	<div class="flex items-center gap-x-3 w-full">
		
		<!-- Away Team - FIXED WIDTH - NEVER SHRINKS -->
		<div class="flex items-center gap-3 flex-shrink-0">
			<Flag country={rows[0].abbr} size="lg" />
			<span class="text-sm font-semibold min-w-[48px] w-[48px] flex-shrink-0 {rows[0].isWinner ? 'text-white' : 'text-[#8888a0]'}">
				{rows[0].abbr}
			</span>
			<span class="text-xl font-bold tabular-nums text-right min-w-[42px] w-[42px] flex-shrink-0 {rows[0].isWinner
				? (isChamp ? 'text-gold' : 'text-white')
				: 'text-[#555570]'}">
				{rows[0].score ?? '—'}
			</span>
		</div>

		<!-- Score Separator - FIXED WIDTH -->
		<div class="flex-shrink-0 px-2">
			<span class="text-[#555570] text-lg font-light select-none">–</span>
		</div>

		<!-- Home Team - FIXED WIDTH - NEVER SHRINKS -->
		<div class="flex items-center justify-end gap-3 flex-shrink-0">
			<span class="text-xl font-bold tabular-nums text-left min-w-[42px] w-[42px] flex-shrink-0 {rows[1].isWinner
				? (isChamp ? 'text-gold' : 'text-white')
				: 'text-[#555570]'}">
				{rows[1].score ?? '—'}
			</span>
			<span class="text-sm font-semibold text-right min-w-[48px] w-[48px] flex-shrink-0 {rows[1].isWinner ? 'text-white' : 'text-[#8888a0]'}">
				{rows[1].abbr}
			</span>
			<Flag country={rows[1].abbr} size="lg" />
		</div>

	</div>

	<!-- Secondary Meta Row -->
	<div class="flex items-center justify-between mt-2.5 pt-2.5 border-t border-border/30 text-xs">
		<!-- Left Side: Date + Location -->
		<div class="flex items-center gap-x-3">
			<span class="text-[#8888a0]">
				{showFullDate ? fmtDateFull(game.official_date) : fmtDate(game.official_date)}
			</span>
			{#if game.venue_name}
				<span class="text-[#555570] truncate">
					{game.venue_name}
				</span>
			{/if}
		</div>

		<!-- Right Side: Game Badges, right justified -->
		<div class="flex items-center gap-x-2">
			{#if game.is_mercy_rule}
				<span class="text-[10px] font-medium bg-warning/15 text-warning border border-warning/25 rounded px-1.5 py-0.5 text-center">
					Mercy
				</span>
			{/if}
			<span class="border rounded px-2.5 py-0.5 font-medium text-center text-xs overflow-hidden whitespace-nowrap text-ellipsis {roundBadgeClass(label)}">
				{label}
			</span>
		</div>
	</div>

</div>