<script lang="ts">
import { tick } from "svelte";
import { Filter } from "lucide-svelte";
import EmptyState from "$lib/components/EmptyState.svelte";
import FilterPills from "$lib/components/FilterPills.svelte";
import GameCard from "$lib/components/GameCard.svelte";
import SeasonTabs from "$lib/components/SeasonTabs.svelte";

import GameDetailPanel from "$lib/components/GameDetailPanel.svelte";
import type { PageData } from "./$types";
import type { FullGame, GameSummary } from "$lib/types";

// ─── Props & State ────────────────────────────────────────────────────────────
let { data }: { data: PageData } = $props();

let selectedSeason = $state(0);
let selectedPool   = $state("All");
let selectedGame   = $state<GameSummary | null>(null);
let loadingGame    = $state<number | null>(null);
let detailContainer = $state<HTMLElement | null>(null);

// Default to most recent season
$effect(() => {
    if (data.seasons.length && !data.seasons.includes(selectedSeason)) {
        selectedSeason = data.seasons[0];
    }
});

// Reset filters on season change
$effect(() => {
    selectedSeason.valueOf();
    selectedPool = "All";
    selectedGame = null;
});

// ─── Derived ──────────────────────────────────────────────────────────────────
const seasonGames = $derived(
    data.games.filter((g: FullGame) => g.season === selectedSeason)
);

const availablePools = $derived(data.pools[selectedSeason] || []);

const filteredGames = $derived(
    seasonGames.filter((g: FullGame) =>
        selectedPool === "All" || g.pool_group === selectedPool
    )
);

function roundPriority(pool_group: string): number {
    const lower = pool_group.toLowerCase();
    if (lower.includes('final') || lower.includes('championship')) return 0;
    if (lower.includes('semi')) return 1;
    if (lower.includes('quarter')) return 2;
    if (lower.includes('pool')) return 3;
    return 4;
}

const sortedGames = $derived(
    [...filteredGames].sort((a: FullGame, b: FullGame) => {
        const pa = roundPriority(a.pool_group);
        const pb = roundPriority(b.pool_group);
        
        if (pa !== pb) return pa - pb;
        return b.official_date.localeCompare(a.official_date);
    })
);

// ─── Game Click Handler ───────────────────────────────────────────────────────
async function openGame(game: FullGame) {
    if (loadingGame !== null) return;
    loadingGame = game.game_pk;
    
    try {
        const res = await fetch(`/api/games/${game.game_pk}`);
        selectedGame = await res.json();
        
        await tick();
        detailContainer?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } catch (e) {
        console.error('Failed to load game details', e);
    } finally {
        loadingGame = null;
    }
}


</script>

<div class="space-y-8 animate-fade-in pb-20">
    <!-- Header -->
    <div>
        <h1 class="text-2xl font-bold text-white tracking-tight">Games</h1>
    </div>

    <!-- Season tabs -->
    <SeasonTabs 
        seasons={data.seasons} 
        selected={selectedSeason} 
        onSelect={(s) => {
            selectedSeason = Number(s);
        }} 
    />



    <!-- Selected Game Detail Panel -->
    <div bind:this={detailContainer}>
        {#if selectedGame}
            <GameDetailPanel game={selectedGame} onclose={() => (selectedGame = null)} />
        {/if}
    </div>

    <!-- Pool filter -->
    <div class="flex flex-col sm:flex-row sm:items-center gap-3">
        <div class="flex items-center gap-2 text-xs text-[#8888a0]">
            <Filter class="w-3.5 h-3.5" />
            <span>Pool:</span>
        </div>
        <FilterPills
            items={availablePools}
            selected={selectedPool}
            onSelect={(p: string) => (selectedPool = p)}
        />
    </div>

    <!-- Result count -->
    <p class="text-xs text-[#555570]">
        {filteredGames.length} game{filteredGames.length === 1 ? '' : 's'}
        {selectedPool !== 'All' ? ` · ${selectedPool}` : ''}
        · {selectedSeason} WBC
    </p>

    <!-- Game cards -->
    {#if sortedGames.length === 0}
        <EmptyState title="No completed games for this selection" />
    {:else}
        <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 max-w-7xl mx-auto">
            {#each sortedGames as game (game.game_pk)}
                <button
                    type="button"
                    onclick={() => openGame(game)}
                    class="cursor-pointer transition-transform hover:scale-[1.02] bg-transparent border-none p-0 m-0 {selectedGame?.game_pk === game.game_pk ? 'ring-1 ring-white/20 rounded-xl' : ''} {loadingGame === game.game_pk ? 'opacity-50 pointer-events-none' : ''}"
                >
                    <GameCard {game} showFullDate />
                </button>
            {/each}
        </div>
    {/if}
</div>
