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

// Extract unique seasons and sort descending
const seasons = $derived(
    [...new Set((data.standings as any[]).map((s: any) => s.season))]
        .sort((a: any, b: any) => Number(b) - Number(a))
);

let selectedSeason = $state<string | number>("");
let activeMobileTab = $state(0);

// Default to latest season on load
$effect(() => {
    if (seasons.length && !seasons.includes(selectedSeason)) {
        selectedSeason = seasons[0];
    }
});

// Bracket data - Using .by for complex logic
const bracket = $derived.by(() => {
    const games = (data.knockoutGames as any[]).filter(
        (g: any) => g.season == selectedSeason
    );
    
    const isModern = Number(selectedSeason) >= 2023;
    
    const qf = isModern
        ? games
            .filter((g: any) => g.game_type === "D")
            .sort((a: any, b: any) => a.official_date.localeCompare(b.official_date))
        : [];
        
    const sf = games
        .filter((g: any) => g.game_type === "L")
        .sort((a: any, b: any) => a.official_date.localeCompare(b.official_date));
        
    const final = games.find((g: any) => g.game_type === "W") ?? null;
    
    return { qf, sf, final };
});

// Pool standings - Using .by for complex logic
const pools = $derived.by(() => {
    const rows = (data.standings as any[]).filter(
        (s: any) => s.season == selectedSeason
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
            const diff = Number(b.pool_run_differential) - Number(a.pool_run_differential);
            if (diff !== 0) return diff;
            return Number(b.pool_runs_scored) - Number(a.pool_runs_scored);
        });
    }
    
    return new Map(
        [...map.entries()].sort(([a], [b]) => {
            const aIsSecond = a.toLowerCase().includes("second") || a.toLowerCase().includes("super");
            const bIsSecond = b.toLowerCase().includes("second") || b.toLowerCase().includes("super");
            if (aIsSecond && !bIsSecond) return -1;
            if (!aIsSecond && bIsSecond) return 1;
            return a.localeCompare(b);
        })
    );
});

// Season stats
const seasonStandings = $derived(
    (data.standings as any[]).filter((s: any) => s.season == selectedSeason)
);

const totalTeams = $derived(seasonStandings.length);
const champion = $derived(seasonStandings.find((s: any) => s.is_champion));

function fmtDate(d: string) {
    return new Date(`${d}T00:00:00`).toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
    });
}
</script>

<div class="space-y-10 animate-fade-in">
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
            <h1 class="text-2xl font-bold text-white tracking-tight">Dashboard</h1>
            <p class="text-sm text-[#8888a0] mt-1">World Baseball Classic Overview</p>
        </div>
        {#if champion}
            <div class="flex items-center gap-2 bg-gold/10 border border-gold/25 rounded-lg px-3 py-2">
                <Trophy class="w-4 h-4 text-gold" />
                <span class="text-sm font-semibold text-gold">
                    {champion.team_abbreviation} — {selectedSeason} Champions
                </span>
            </div>
        {/if}
    </div>

    <SeasonTabs {seasons} selected={selectedSeason} onSelect={(s) => selectedSeason = s} />

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
            <AnimatedCounter value={bracket.qf.length + bracket.sf.length + (bracket.final ? 1 : 0)} label="Knockout Games" color="gold" />
        </div>
    </div>

    <section>
        <h2 class="text-lg font-semibold text-white mb-6 flex items-center gap-2">
            <Target class="w-5 h-5 text-accent" />
            Knockout Bracket
        </h2>

        {#if bracket.qf.length > 0 || Number(selectedSeason) >= 2023}
            <div class="relative">

                <!-- DESKTOP LAYOUT (>1024px) -->
                <div class="hidden md:block">
                    <div class="grid grid-cols-[auto_auto_auto] grid-rows-3 gap-5 py-6">
                        <div class="flex items-center ">
                            <div class="w-full min-w-[200px] max-w-[275px]  mr-auto">
                                {#if bracket.qf[0]} <GameCard game={bracket.qf[0]} size="qf" /> 
                                {:else} <div class="bg-surface border border-border border-dashed rounded-xl px-3 py-4 text-center text-[#555570] text-xs">TBD</div> {/if}
                            </div>
                        </div>
                        <div></div>
                        <div class="flex items-center ">
                            <div class="w-full min-w-[200px] max-w-[275px] ml-auto">
                                {#if bracket.qf[2]} <GameCard game={bracket.qf[2]} size="qf" /> 
                                {:else} <div class="bg-surface border border-border border-dashed rounded-xl px-3 py-4 text-center text-[#555570] text-xs">TBD</div> {/if}
                            </div>
                        </div>
                        <div class="flex items-center">
                            <div class="w-full min-w-[200px] max-w-[300px] ml-auto">
                                {#if bracket.sf[0]} <GameCard game={bracket.sf[0]} size="sf" /> 
                                {:else} <div class="bg-surface border border-border border-dashed rounded-xl px-4 py-5 text-center text-[#555570] text-sm">TBD</div> {/if}
                            </div>
                        </div>
                        <div class="flex items-center">
                            <div class="w-full min-w-[200px] max-w-[350px] m-auto">
                                {#if bracket.final} <GameCard game={bracket.final} size="championship" /> 
                                {:else} <div class="bg-surface border border-gold/20 border-dashed rounded-xl px-4 py-8 text-center text-[#555570] text-sm">TBD</div> {/if}
                            </div>
                        </div>
                        <div class="flex items-center">
                            <div class="w-full min-w-[200px] max-w-[300px] mr-auto">
                                {#if bracket.sf[1]} <GameCard game={bracket.sf[1]} size="sf" /> 
                                {:else} <div class="bg-surface border border-border border-dashed rounded-xl px-4 py-5 text-center text-[#555570] text-sm">TBD</div> {/if}
                            </div>
                        </div>
                        <div class="flex items-center ">
                            <div class="w-full min-w-[200px] max-w-[275px] mr-auto">
                                {#if bracket.qf[1]} <GameCard game={bracket.qf[1]} size="qf" /> 
                                {:else} <div class="bg-surface border border-border border-dashed rounded-xl px-3 py-4 text-center text-[#555570] text-xs">TBD</div> {/if}
                            </div>
                        </div>
                        <div></div>
                        <div class="flex items-center ">
                            <div class="w-full min-w-[200px] max-w-[275px] ml-auto">
                                {#if bracket.qf[3]} <GameCard game={bracket.qf[3]} size="qf" /> 
                                {:else} <div class="bg-surface border border-border border-dashed rounded-xl px-3 py-4 text-center text-[#555570] text-xs">TBD</div> {/if}
                            </div>
                        </div>
                    </div>

                    <svg 
                        viewBox="0 0 1000 400" 
                        preserveAspectRatio="none" 
                        class="absolute inset-0 w-full h-full pointer-events-none -z-1"
                    >
                        <style>
                            /* Changed stroke to a lighter color for visibility check; 
                            Adjust #666680 to your preferred line color */
                            .bracket-line { 
                                stroke: #666680; 
                                stroke-width: 2; 
                                fill: none; 
                                vector-effect: non-scaling-stroke; 
                            }
                        </style>

                        <path d="M 100 97 L 200 97 L 250 195 L 400 195" class="bracket-line" />
                        <path d="M 100 293 L 200 293 L 250 195 L 400 195" class="bracket-line" />

                        <path d="M 400 195 L 600 195" class="bracket-line" />

                        <path d="M 900 97 L 800 97 L 750 195 L 600 195" class="bracket-line" />
                        <path d="M 900 293 L 800 293 L 750 195 L 600 195" class="bracket-line" />
                    </svg>
                </div>

                <!-- MOBILE LAYOUT (<768px) - Tabbed Rounds -->
                <div class="md:hidden">
                    <div class="flex bg-surface border border-border rounded-xl mb-4 overflow-hidden">
{#each ['Quarterfinals', 'Semifinals', 'Championship'] as round, i}
                            <button 
                                onclick={() => activeMobileTab = i}
                                class="flex-1 shrink min-w-0 px-2 py-3 text-xs sm:text-sm font-medium transition-colors {activeMobileTab === i ? 'bg-accent/10 text-accent border-b-2 border-accent' : 'text-[#8888a0] hover:text-white'}"
                            >
                                {round}
                            </button>
                        {/each}
                    </div>

                    <div class="animate-fade-in">
                        {#if activeMobileTab === 0}
                            <div class="flex flex-col gap-4">
                                {#each bracket.qf as game, idx}
                                    <GameCard {game} size="qf" />
                                {/each}
                                {#if bracket.qf.length === 0}
                                    <div class="bg-surface border border-border border-dashed rounded-xl px-3 py-4 text-center text-[#555570] text-xs">Quarterfinals TBD</div>
                                {/if}
                            </div>
                        {:else if activeMobileTab === 1}
                            <div class="flex flex-col gap-4">
                                {#each bracket.sf as game}
                                    <GameCard {game} size="sf" />
                                {/each}
                            </div>
                        {:else if activeMobileTab === 2}
                            <div class="max-w-md mx-auto">
                                {#if bracket.final}
                                    <GameCard game={bracket.final} size="championship" />
                                {:else}
                                    <div class="bg-surface border border-gold/20 border-dashed rounded-xl px-4 py-8 text-center text-[#555570] text-sm">Championship TBD</div>
                                {/if}
                            </div>
                        {/if}
                    </div>
                </div>
            </div>
        {:else}
            <div class="flex flex-col items-center gap-6">
                <div class="w-full max-w-lg">
                    {#if bracket.final}
                        <GameCard game={bracket.final} size="championship" />
                    {:else}
                        <div class="bg-surface border border-gold/20 border-dashed rounded-xl px-4 py-8 text-center text-[#555570] text-sm">TBD</div>
                    {/if}
                </div>
                <div class="w-full max-w-5xl">
                    <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        {#each Array(2) as _, idx}
                            {@const game = bracket.sf[idx]}
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

    <section>
        <h2 class="text-lg font-semibold text-white mb-6 flex items-center gap-2">
            <TrendingUp class="w-5 h-5 text-accent" />
            Pool Standings
        </h2>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-5 max-w-7xl m-auto">
            {#each [...pools.entries()] as [poolName, teams]}
                <PoolStandings {poolName} {teams} />
            {/each}
        </div>
    </section>

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