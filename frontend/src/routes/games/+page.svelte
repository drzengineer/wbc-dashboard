<script lang="ts">
import { Filter } from "lucide-svelte";
import EmptyState from "$lib/components/EmptyState.svelte";
import FilterPills from "$lib/components/FilterPills.svelte";
import GameCard from "$lib/components/GameCard.svelte";
import SeasonTabs from "$lib/components/SeasonTabs.svelte";
import StatCard from "$lib/components/StatCard.svelte";
import { roundLabel, roundOrder } from "$lib/utils";
import type { PageData } from "./$types";

const { data }: { data: PageData } = $props();

const allGames = data.games as any[];

const seasons = $derived(
	[...new Set(allGames.map((g) => g.season))].sort(
		(a, b) => Number(b) - Number(a),
	),
);

let selectedSeason = $state("");
let selectedRound = $state("All");

$effect(() => {
	if (seasons.length && !seasons.includes(selectedSeason)) {
		selectedSeason = seasons[0] as string;
	}
});

$effect(() => {
	selectedSeason;
	selectedRound = "All";
});

const seasonGames = $derived(
	allGames.filter((g) => g.season === selectedSeason),
);

const availableRounds = $derived(() => {
	const labels = [...new Set(seasonGames.map(roundLabel))] as string[];
	return labels.sort((a, b) => {
		const diff = roundOrder(a) - roundOrder(b);
		return diff !== 0 ? diff : a.localeCompare(b);
	});
});

const filteredGames = $derived(
	selectedRound === "All"
		? seasonGames
		: seasonGames.filter((g) => roundLabel(g) === selectedRound),
);

const sortedGames = $derived(
	[...filteredGames].sort((a, b) => {
		const ra = roundOrder(roundLabel(a));
		const rb = roundOrder(roundLabel(b));
		if (ra !== rb) return ra - rb;
		return b.official_date.localeCompare(a.official_date);
	}),
);

// Stats
const totalGames = $derived(seasonGames.length);
const knockoutCt = $derived(
	seasonGames.filter((g) => ["W", "L", "D"].includes(g.game_type)).length,
);
const mercyCt = $derived(seasonGames.filter((g) => g.is_mercy_rule).length);
const totalRuns = $derived(
	seasonGames.reduce(
		(sum: number, g: any) =>
			sum + (Number(g.away_score) || 0) + (Number(g.home_score) || 0),
		0,
	),
);
</script>

<div class="space-y-8 animate-fade-in">
	<!-- Header -->
	<div>
		<h1 class="text-2xl font-bold text-white tracking-tight">Games</h1>
		<p class="text-sm text-[#8888a0] mt-1">All tournament game results</p>
	</div>

	<!-- Season tabs -->
	<SeasonTabs {seasons} selected={selectedSeason} onSelect={(s) => selectedSeason = s as string} />

	<!-- Season stat cards -->
	<div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
		<StatCard label="Games Played" value={totalGames} />
		<StatCard label="Knockout Games" value={knockoutCt} color="accent" />
		<StatCard label="Total Runs" value={totalRuns} />
		<StatCard label="Mercy Rule" value={mercyCt} color={mercyCt > 0 ? 'warning' : ''} />
	</div>

	<!-- Round filter -->
	<div class="flex flex-col sm:flex-row sm:items-center gap-3">
		<div class="flex items-center gap-2 text-xs text-[#8888a0]">
			<Filter class="w-3.5 h-3.5" />
			<span>Round:</span>
		</div>
		<FilterPills items={availableRounds()} selected={selectedRound} onSelect={(r) => selectedRound = r} />
	</div>

	<!-- Result count -->
	<p class="text-xs text-[#555570]">
		{filteredGames.length} game{filteredGames.length === 1 ? '' : 's'}
		{selectedRound !== 'All' ? `· ${selectedRound}` : ''}
		· {selectedSeason} WBC
	</p>

	<!-- Game cards -->
	{#if sortedGames.length === 0}
		<EmptyState title="No completed games for this selection" />
	{:else}
		<div class="flex flex-col gap-3">
			{#each sortedGames as game}
				<GameCard {game} showFullDate />
			{/each}
		</div>
	{/if}
</div>