<script lang="ts">
import { fmtDate, fmtDateFull, roundBadgeClass, roundLabel } from "$lib/utils";
import Flag from "./Flag.svelte";

type CardSize = 'standard' | 'qf' | 'sf' | 'championship';

let {
	game,
	compact = false,
	showFullDate = false,
	size = 'standard' as CardSize,
}: {
	game: any;
	compact?: boolean;
	showFullDate?: boolean;
	size?: CardSize;
} = $props();

let isChamp = $derived(game.game_type === "W");
let label = $derived(roundLabel(game));
let awayWon = $derived(!!game.away_is_winner);
let homeWon = $derived(!!game.home_is_winner);
let hasInnings = $derived(game.away_innings && game.home_innings && game.away_innings.length > 0);

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

<div class="bg-surface border rounded-xl py-0 transition-all duration-200 hover:border-[#3a3a4a] overflow-hidden @container
	{isChamp ? 'border-gold/40 shadow-lg shadow-gold/5' : 'border-border'}
	{sizeClasses[size]}">
	
	<!-- Top Header Row -->
	<div class="flex items-center justify-center border-b border-border text-xs
		{size === 'qf' ? 'px-4 py-2' : size === 'sf' ? 'px-5 py-2.5' : size === 'championship' ? 'px-6 py-3' : 'px-5 py-3'}">
		<span class="text-[#8888a0] flex-1 text-left @max-[420px]:hidden">
			{showFullDate ? fmtDateFull(game.official_date) : fmtDate(game.official_date)}
		</span>

		<span class="border rounded px-2.5 py-0.5 font-medium text-center text-xs overflow-hidden whitespace-nowrap text-ellipsis {roundBadgeClass(label)} min-w-27.5 text-center mx-2">
			{label}
		</span>

		{#if game.venue_name}
			<span class="text-[#555570] truncate flex-1 text-right @max-[420px]:hidden">
				{game.venue_name}
			</span>
		{:else}
			<span class="flex-1"></span>
		{/if}
	</div>

	{#each rows as row, index}
	<div class="flex items-center w-full {row.isWinner ? 'bg-surface-hover' : ''}
		{index > 0 ? 'border-t border-border/50' : ''}
		{size === 'qf' ? 'px-4 py-2.5' : size === 'sf' ? 'px-5 py-3' : size === 'championship' ? 'px-6 py-4' : 'px-5 py-3'}">
		
		<!-- LEFT ZONE: Team Info - FIXED WIDTH (balanced symmetrically with right zone) -->
		<div class="flex items-center gap-3 shrink-0 min-w-60 @max-[600px]:min-w-0">
			<Flag country={row.abbr} size="lg" />
			<span class="text-sm font-semibold min-w-13 w-13 shrink-0 {row.isWinner ? 'text-white' : 'text-[#8888a0]'}">
				{row.abbr}
			</span>
			<span class="text-sm min-w-30 @max-[420px]:hidden {row.isWinner ? 'text-[#ccccdd]' : 'text-[#777790]'}">
				{row.fullName ?? row.name ?? ''}
			</span>
		</div>

		<!-- LEFT FLEX GAP: This space grows/shrinks (minimum safety width) -->
		<div class="grow"></div>

		<!-- MIDDLE ZONE: Innings columns - FIXED WIDTH -->
		{#if hasInnings}
		<div class="flex gap-2 items-center shrink-0">
			{#each (index === 0 ? game.away_innings : game.home_innings) as run}
			{@const runNum = Number(run)}
			<div class="w-7 text-sm tabular-nums text-center font-medium {runNum > 0 ? 'text-white' : 'text-[#555570]'} @max-[850px]:hidden">
				{runNum}
			</div>
			{/each}
		</div>
		{/if}

		<!-- RIGHT FLEX GAP: This space grows/shrinks (minimum safety width) -->
		<div class="grow"></div>

		<!-- RIGHT ZONE: RHE + Mercy + Score - FIXED WIDTH -->
		<div class="flex items-center gap-2 shrink-0 justify-end min-w-60 @max-[600px]:min-w-0">
			{#if hasInnings}
			<div class="flex items-center gap-2 shrink-0">
				<!-- RHE Totals -->
				<div class="w-7 text-sm tabular-nums text-center font-medium text-white @max-[600px]:hidden">
					{index === 0 ? game.away_r : game.home_r}
				</div>
				<div class="w-7 text-sm tabular-nums text-center font-medium text-[#ccccdd] @max-[600px]:hidden">
					{index === 0 ? game.away_h : game.home_h}
				</div>
				<div class="w-7 text-sm tabular-nums text-center font-medium text-[#ccccdd] @max-[600px]:hidden">
					{index === 0 ? game.away_e : game.home_e}
				</div>
			</div>
			{/if}

			<div class="min-w-14 text-right shrink-0">
			{#if row.isWinner && game.is_mercy_rule}
				<span class="text-[10px] font-medium bg-warning/15 text-warning border border-warning/25 rounded px-1.5 py-0.5">
					Mercy
				</span>
			{/if}
			</div>
			
			<span class="text-xl font-bold tabular-nums text-right min-w-8 w-8 shrink-0 flex items-center justify-end {row.isWinner
				? (isChamp ? 'text-gold' : 'text-white')
				: 'text-[#555570]'}">
				{row.score ?? '—'}
			</span>
		</div>
	</div>
	{/each}

</div>