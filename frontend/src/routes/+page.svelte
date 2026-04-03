<script lang="ts">
import { Target, TrendingUp, Trophy, Zap } from "lucide-svelte";
import AnimatedCounter from "$lib/components/AnimatedCounter.svelte";
import EmptyState from "$lib/components/EmptyState.svelte";
import Flag from "$lib/components/Flag.svelte";
import GameCard from "$lib/components/GameCard.svelte";
import GaugeRing from "$lib/components/GaugeRing.svelte";
import SeasonTabs from "$lib/components/SeasonTabs.svelte";
import PoolStandings from "$lib/components/PoolStandings.svelte";
import { pct } from "$lib/utils";
import type { PageData } from "./$types";

const { data }: { data: PageData } = $props();

const seasons = $derived(
	[...new Set((data.standings as any[]).map((s: any) => s.season))].sort(
		(a: any, b: any) => Number(b) - Number(a),
	),
);

let selectedSeason = $state("");

$effect(() => {
	if (seasons.length && !seasons.includes(selectedSeason)) {
		selectedSeason = seasons[0] as string;
	}
});

// Bracket data
const bracket = $derived(() => {
	const games = (data.knockoutGames as any[]).filter(
		(g: any) => g.season === selectedSeason,
	);
	const isModern = selectedSeason >= "2023";
	const qf = isModern
		? games
				.filter((g: any) => g.game_type === "D")
				.sort((a: any, b: any) =>
					a.official_date.localeCompare(b.official_date),
				)
		: [];
	const sf = games
		.filter((g: any) => g.game_type === "L")
		.sort((a: any, b: any) => a.official_date.localeCompare(b.official_date));
	const final = games.find((g: any) => g.game_type === "W") ?? null;
	return { qf, sf, final };
});

// Pool standings
const pools = $derived(() => {
	const rows = (data.standings as any[]).filter(
		(s: any) => s.season === selectedSeason,
	);
	const map = new Map<string, any[]>();
	for (const row of rows) {
		const key = row.pool_display ?? "Other";
		if (!map.has(key)) map.set(key, []);
		map.get(key)?.push(row);
	}
	for (const [, teams] of map) {
		teams.sort((a: any, b: any) => {
			const wPct = Number(b.pool_win_pct) - Number(a.pool_win_pct);
			if (wPct !== 0) return wPct;
			const diff =
				Number(b.pool_run_differential) - Number(a.pool_run_differential);
			if (diff !== 0) return diff;
			return Number(b.pool_runs_scored) - Number(a.pool_runs_scored);
		});
	}
	return new Map(
		[...map.entries()].sort(([a], [b]) => {
			const aIsSecond =
				a.toLowerCase().includes("second") || a.toLowerCase().includes("super");
			const bIsSecond =
				b.toLowerCase().includes("second") || b.toLowerCase().includes("super");
			if (aIsSecond && !bIsSecond) return -1;
			if (!aIsSecond && bIsSecond) return 1;
			return a.localeCompare(b);
		}),
	);
});

// Season stats
const seasonStandings = $derived(
	(data.standings as any[]).filter((s: any) => s.season === selectedSeason),
);

const totalTeams = $derived(seasonStandings.length);
const champion = $derived(seasonStandings.find((s: any) => s.is_champion));

// Bracket helpers
function gameRows(game: any) {
	const away = {
		abbr: game.away_team_abbreviation,
		name: game.away_team_name,
		score: game.away_score,
		isWinner: !!game.away_is_winner,
	};
	const home = {
		abbr: game.home_team_abbreviation,
		name: game.home_team_name,
		score: game.home_score,
		isWinner: !!game.home_is_winner,
	};
	return away.isWinner || (!away.isWinner && !home.isWinner)
		? [away, home]
		: [home, away];
}

function fmtDate(d: string) {
	return new Date(`${d}T00:00:00`).toLocaleDateString("en-US", {
		month: "short",
		day: "numeric",
	});
}
</script>

<div class="space-y-10 animate-fade-in">
	<!-- Header -->
	<div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
		<div>
			<h1 class="text-2xl font-bold text-white tracking-tight">Dashboard</h1>
			<p class="text-sm text-[#8888a0] mt-1">World Baseball Classic Overview</p>
		</div>
		{#if champion}
			<div class="flex items-center gap-2 bg-gold/10 border border-gold/25 rounded-lg px-3 py-2">
				<Trophy class="w-4 h-4 text-gold" />
				<span class="text-sm font-semibold text-gold">{champion.team_abbreviation} — {selectedSeason} Champions</span>
			</div>
		{/if}
	</div>

	<!-- Season tabs -->
	<SeasonTabs {seasons} selected={selectedSeason} onSelect={(s) => selectedSeason = s as string} />

	<!-- Hero stats -->
	<div class="grid grid-cols-2 md:grid-cols-4 gap-4">
		<div class="bg-surface border border-border rounded-xl px-5 py-6 text-center hover:border-border-light transition-colors">
			<AnimatedCounter value={totalTeams} label="Teams" />
		</div>
		<div class="bg-surface border border-border rounded-xl px-5 py-6 text-center hover:border-border-light transition-colors">
			<AnimatedCounter value={seasonStandings.reduce((s: number, t: any) => s + (t.pool_gp ?? 0), 0) / 2} label="Pool Games" />
		</div>
		<div class="bg-surface border border-border rounded-xl px-5 py-6 text-center hover:border-border-light transition-colors">
			<AnimatedCounter value={seasonStandings.reduce((s: number, t: any) => s + (t.pool_runs_scored ?? 0), 0)} label="Total Runs" color="accent" />
		</div>
		<div class="bg-surface border border-border rounded-xl px-5 py-6 text-center hover:border-border-light transition-colors">
			<AnimatedCounter value={bracket().qf.length + bracket().sf.length + (bracket().final ? 1 : 0)} label="Knockout Games" color="gold" />
		</div>
	</div>

	<!-- Bracket -->
	<section>
		<h2 class="text-lg font-semibold text-white mb-6 flex items-center gap-2">
			<Target class="w-5 h-5 text-accent" />
			Knockout Bracket
		</h2>

		{#if bracket().qf.length > 0 || selectedSeason >= '2023'}
			<div class="relative">
				<!-- Main Bracket Container - 5x3 Rigid Grid Layout -->
				<div class="grid grid-cols-1 lg:grid-cols-5 lg:grid-rows-[130px_130px_130px] gap-0 py-6">

					<!-- ROW 1 -->
					<div class="flex items-center">
						<div class="w-full max-w-[350px] mx-auto">
							{#if bracket().qf[0]}
<GameCard game={bracket().qf[0]} size="qf" />
							{:else}
								<div class="bg-surface border border-border border-dashed rounded-xl px-3 py-4 text-center text-[#555570] text-xs">TBD</div>
							{/if}
						</div>
					</div>
					<div></div>
					<div></div>
					<div></div>
					<div class="flex items-center">
						<div class="w-full max-w-[350px] mx-auto">
							{#if bracket().qf[2]}
<GameCard game={bracket().qf[2]} size="qf" />
							{:else}
								<div class="bg-surface border border-border border-dashed rounded-xl px-3 py-4 text-center text-[#555570] text-xs">TBD</div>
							{/if}
						</div>
					</div>

					<!-- ROW 2 -->
					<div></div>
					<div class="flex items-center">
						<div class="w-full max-w-[350px] mx-auto">
							{#if bracket().sf[0]}
<GameCard game={bracket().sf[0]} size="sf" />
							{:else}
								<div class="bg-surface border border-border border-dashed rounded-xl px-4 py-5 text-center text-[#555570] text-sm">TBD</div>
							{/if}
						</div>
					</div>
					<div class="flex items-center">
						<div class="w-full max-w-[350px] mx-auto">
							{#if bracket().final}
<GameCard game={bracket().final} size="championship" />
							{:else}
								<div class="bg-surface border border-gold/20 border-dashed rounded-xl px-4 py-8 text-center text-[#555570] text-sm">TBD</div>
							{/if}
						</div>
					</div>
					<div class="flex items-center">
						<div class="w-full max-w-[350px] mx-auto">
							{#if bracket().sf[1]}
<GameCard game={bracket().sf[1]} size="sf" />
							{:else}
								<div class="bg-surface border border-border border-dashed rounded-xl px-4 py-5 text-center text-[#555570] text-sm">TBD</div>
							{/if}
						</div>
					</div>
					<div></div>

					<!-- ROW 3 -->
					<div class="flex items-center">
						<div class="w-full max-w-[350px] mx-auto">
							{#if bracket().qf[1]}
<GameCard game={bracket().qf[1]} size="qf" />
							{:else}
								<div class="bg-surface border border-border border-dashed rounded-xl px-3 py-4 text-center text-[#555570] text-xs">TBD</div>
							{/if}
						</div>
					</div>
					<div></div>
					<div></div>
					<div></div>
					<div class="flex items-center">
						<div class="w-full max-w-[350px] mx-auto">
							{#if bracket().qf[3]}
<GameCard game={bracket().qf[3]} size="qf" />
							{:else}
								<div class="bg-surface border border-border border-dashed rounded-xl px-3 py-4 text-center text-[#555570] text-xs">TBD</div>
							{/if}
						</div>
					</div>
				</div>

				<!-- SVG Connector Lines (Desktop Only) -->
				<svg class="hidden lg:block absolute inset-0 w-full h-full pointer-events-none z-0">
					<style>
						.bracket-line {
							stroke: #333348;
							stroke-width: 2;
							fill: none;
						}
					</style>

					<!-- LEFT SIDE CONNECTORS -->
					<path d="M 20% 97 L 30% 97 L 30% 195 L 40% 195" class="bracket-line" />
					<path d="M 20% 293 L 30% 293 L 30% 195 L 40% 195" class="bracket-line" />

					<!-- CENTER CONNECTORS -->
					<path d="M 40% 195 L 60% 195" class="bracket-line" />

					<!-- RIGHT SIDE CONNECTORS -->
					<path d="M 80% 97 L 70% 97 L 70% 195 L 60% 195" class="bracket-line" />
					<path d="M 80% 293 L 70% 293 L 70% 195 L 60% 195" class="bracket-line" />
				</svg>
			</div>
		{:else}
			<!-- Legacy Bracket layout for older seasons without QF -->
			<div class="flex flex-col items-center gap-6">
				<div class="w-full max-w-lg">
					<p class="text-xs font-bold text-gold uppercase tracking-widest text-center mb-3">Championship</p>
					{#if bracket().final}
						<GameCard game={bracket().final} size="championship" />
					{:else}
						<div class="bg-surface border border-gold/20 border-dashed rounded-xl px-4 py-8 text-center text-[#555570] text-sm">TBD</div>
					{/if}
				</div>
				<div class="w-px h-6 bg-border-light"></div>
				<div class="w-full max-w-5xl">
					<p class="text-xs font-bold text-[#a78bfa] uppercase tracking-widest text-center mb-3">Semifinals</p>
					<div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
						{#each Array(2) as _, idx}
							{@const game = bracket().sf[idx]}
							{#if game}
								<GameCard {game} size="sf" />
							{:else}
								<div class="bg-surface border border-border border-dashed rounded-xl px-4 py-6 text-center text-[#555570] text-sm">TBD</div>
							{/if}
						{/each}
					</div>
				</div>
			</div>
		{/if}
	</section>

	<!-- Pool Standings -->
	<section>
		<h2 class="text-lg font-semibold text-white mb-6 flex items-center gap-2">
			<TrendingUp class="w-5 h-5 text-accent" />
			Pool Standings
		</h2>
		<div class="grid grid-cols-1 xl:grid-cols-2 gap-5 max-w-7xl m-auto">
			{#each [...pools().entries()] as [poolName, teams]}
				<PoolStandings {poolName} {teams} />
			{/each}
		</div>
	</section>

	<!-- Recent Results -->
	<section>
		<h2 class="text-lg font-semibold text-white mb-6 flex items-center gap-2">
			<Zap class="w-5 h-5 text-accent" />
			Recent Results
		</h2>
		{#if (data.recentGames as any[]).length === 0}
			<EmptyState title="No completed games found" />
		{:else}
			<div class="flex flex-col gap-3">
				{#each data.recentGames as game}
					<GameCard game={game as any} />
				{/each}
			</div>
		{/if}
	</section>
</div>