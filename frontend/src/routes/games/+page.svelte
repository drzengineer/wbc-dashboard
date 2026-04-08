<script lang="ts">
import { Filter } from "lucide-svelte";
import EmptyState from "$lib/components/EmptyState.svelte";
import FilterPills from "$lib/components/FilterPills.svelte";
import GameCard from "$lib/components/GameCard.svelte";
import SeasonTabs from "$lib/components/SeasonTabs.svelte";
import StatCard from "$lib/components/StatCard.svelte";
import { roundLabel, roundOrder } from "$lib/utils";
import type { FullGame } from "$lib/types";
import type { PageData } from "./$types";

// ─── Component State & Props ─────────────────────────────────────────────────
let { data }: { data: PageData } = $props();

let selectedSeason = $state(0);
let selectedRound = $state("All");
let selectedPool = $state("All");

// Default to most recent season if not set
$effect(() => {
    if (data.seasons.length && !data.seasons.includes(selectedSeason)) {
        selectedSeason = data.seasons[0];
    }
});

// Reset filters when season changes
$effect(() => {
    selectedSeason;
    selectedRound = "All";
    selectedPool = "All";
});

// ─── Derived Values ──────────────────────────────────────────────────────────
const seasonGames = $derived(
    data.games.filter(g => g.season === selectedSeason)
);

const availableRounds = $derived.by(() => {
    const labels = [...new Set(seasonGames.map(roundLabel))];
    return labels.sort((a, b) => {
        const diff = roundOrder(a) - roundOrder(b);
        return diff !== 0 ? diff : a.localeCompare(b);
    });
});

const availablePools = $derived(data.pools[selectedSeason] || []);

const filteredGames = $derived(
    seasonGames
        .filter(g => selectedRound === "All" || roundLabel(g) === selectedRound)
        .filter(g => selectedPool === "All" || g.pool_group === selectedPool)
);

const sortedGames = $derived(
    [...filteredGames].sort((a, b) => {
        const ra = roundOrder(roundLabel(a));
        const rb = roundOrder(roundLabel(b));
        if (ra !== rb) return ra - rb;
        return b.official_date.localeCompare(a.official_date);
    })
);

// ─── Season Statistics ────────────────────────────────────────────────────────
const totalGames = $derived(seasonGames.length);
const knockoutCt = $derived(
    seasonGames.filter(g => ["W", "L", "D"].includes(g.game_type)).length
);
const mercyCt = $derived(seasonGames.filter(g => g.is_mercy_rule).length);
const totalRuns = $derived(
    seasonGames.reduce((sum: number, g: FullGame) =>
        sum + (Number(g.away_score) || 0) + (Number(g.home_score) || 0),
        0
    )
);
</script>

<div class="space-y-8 animate-fade-in pb-20">
    <!-- Header -->
    <div>
        <h1 class="text-2xl font-bold text-white tracking-tight">Games</h1>
        <p class="text-sm text-[#8888a0] mt-1">All tournament game results</p>
    </div>

    <!-- Season tabs -->
    <SeasonTabs 
        seasons={data.seasons} 
        selected={selectedSeason} 
        onSelect={(s) => {
            selectedSeason = Number(s);
        }} 
    />

    <!-- Season stat cards -->
    <div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatCard label="Games Played" value={totalGames} />
        <StatCard label="Knockout Games" value={knockoutCt} color="accent" />
        <StatCard label="Total Runs" value={totalRuns} />
        <StatCard label="Mercy Rule" value={mercyCt} color={mercyCt > 0 ? 'warning' : ''} />
    </div>

    <!-- Filters row -->
    <div class="flex flex-col gap-4">
        <!-- Round filter -->
        <div class="flex flex-col sm:flex-row sm:items-center gap-3">
            <div class="flex items-center gap-2 text-xs text-[#8888a0]">
                <Filter class="w-3.5 h-3.5" />
                <span>Round:</span>
            </div>
            <FilterPills items={availableRounds} selected={selectedRound} onSelect={(r) => selectedRound = r} />
        </div>

        <!-- Pool filter -->
        <div class="flex flex-col sm:flex-row sm:items-center gap-3">
            <div class="flex items-center gap-2 text-xs text-[#8888a0]">
                <Filter class="w-3.5 h-3.5" />
                <span>Pool:</span>
            </div>
            <FilterPills items={availablePools} selected={selectedPool} onSelect={(p) => selectedPool = p} />
        </div>
    </div>

    <!-- Result count -->
    <p class="text-xs text-[#555570]">
        {filteredGames.length} game{filteredGames.length === 1 ? '' : 's'}
        {selectedRound !== 'All' ? ` · ${selectedRound}` : ''}
        {selectedPool !== 'All' ? ` · ${selectedPool}` : ''}
        · {selectedSeason} WBC
    </p>

    <!-- Game cards -->
    {#if sortedGames.length === 0}
        <EmptyState title="No completed games for this selection" />
    {:else}
        <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 max-w-7xl mx-auto">
            {#each sortedGames as game}
                <GameCard {game} showFullDate />
            {/each}
        </div>
    {/if}
</div>