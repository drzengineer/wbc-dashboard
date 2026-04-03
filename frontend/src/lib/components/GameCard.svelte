<script lang="ts">
import type { GameResult } from "$lib/types";
import { fmtDate, fmtDateFull, roundBadgeClass, roundLabel } from "$lib/utils";
import Flag from "./Flag.svelte";

type CardSize = 'standard' | 'qf' | 'sf' | 'championship';

let {
	game,
	compact = false,
	showFullDate = false,
	size = 'standard' as CardSize,
}: {
	game: GameResult;
	compact?: boolean;
	showFullDate?: boolean;
	size?: CardSize;
} = $props();

let isChamp = $derived(game.game_type === "W");
let label = $derived(roundLabel(game));
let awayWon = $derived(!!game.away_is_winner);
let homeWon = $derived(!!game.home_is_winner);

function teamRow(
	abbr: string | null,
	name: string | null,
	fullName: string | null,
	score: number | null,
	isWinner: boolean,
	side: string,
) {
	return { abbr: abbr ?? name ?? "—", name, fullName, score, isWinner, side };
}

let rows = $derived([
	teamRow(
		game.away_team_abbreviation,
		game.away_team_name,
		game.away_team_name,
		game.away_score,
		awayWon,
		"Away",
	),
	teamRow(
		game.home_team_abbreviation,
		game.home_team_name,
		game.home_team_name,
		game.home_score,
		homeWon,
		"Home",
	),
]);

// Sizing classes based on round level
const sizeClasses = $derived({
	standard: '',
	qf: 'text-xs',
	sf: 'text-sm',
	championship: ''
});
</script>

<div class="bg-surface border rounded-xl py-0 transition-all duration-200 hover:border-[#3a3a4a] overflow-hidden
	{isChamp ? 'border-gold/40 shadow-lg shadow-gold/5' : 'border-border'}
	{sizeClasses[size]}">
	
	<!-- Top Header Row -->
	<div class="flex items-center justify-between border-b border-border text-xs
		{size === 'qf' ? 'px-4 py-2' : size === 'sf' ? 'px-5 py-2.5' : size === 'championship' ? 'px-6 py-3' : 'px-5 py-3'}">
		<span class="text-[#8888a0] flex-1 text-left">
			{showFullDate ? fmtDateFull(game.official_date) : fmtDate(game.official_date)}
		</span>

		<span class="border rounded px-2.5 py-0.5 font-medium text-center text-xs overflow-hidden whitespace-nowrap text-ellipsis {roundBadgeClass(label)} min-w-[110px] text-center mx-2">
			{label}
		</span>

		{#if game.venue_name}
			<span class="text-[#555570] truncate flex-1 text-right">
				{game.venue_name}
			</span>
		{:else}
			<span class="flex-1"></span>
		{/if}
	</div>

	{#each rows as row, index}
	<div class="flex items-center justify-between w-full gap-2 {row.isWinner ? 'bg-surface-hover' : ''}
		{index > 0 ? 'border-t border-border/50' : ''}
		{size === 'qf' ? 'px-4 py-2.5' : size === 'sf' ? 'px-5 py-3' : size === 'championship' ? 'px-6 py-4' : 'px-5 py-3'}">
		<div class="flex items-center gap-3">
			<Flag country={row.abbr} size="lg" />
			<span class="text-sm font-semibold min-w-[52px] w-[52px] flex-shrink-0 {row.isWinner ? 'text-white' : 'text-[#8888a0]'}">
				{row.abbr}
			</span>
			<span class="text-sm min-w-[120px] {row.isWinner ? 'text-[#ccccdd]' : 'text-[#777790]'}">
				{row.fullName ?? row.name ?? ''}
			</span>
		</div>

		<div class="flex-grow"></div>

		{#if row.isWinner && game.is_mercy_rule}
			<span class="text-[10px] font-medium bg-warning/15 text-warning border border-warning/25 rounded px-1.5 py-0.5">
				Mercy
			</span>
		{/if}
		<span class="text-xl font-bold tabular-nums text-right min-w-[32px] w-[32px] flex-shrink-0 flex items-center justify-end {row.isWinner
			? (isChamp ? 'text-gold' : 'text-white')
			: 'text-[#555570]'}">
			{row.score ?? '—'}
		</span>
	</div>
	{/each}


</div>