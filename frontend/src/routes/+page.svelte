<script lang="ts">
import { TrendingUp, Trophy, Zap, Flame, Activity, Swords, Rocket, Clock } from "lucide-svelte";
import EmptyState from "$lib/components/EmptyState.svelte";
import GameCard from "$lib/components/GameCard.svelte";
import SeasonTabs from "$lib/components/SeasonTabs.svelte";
import PoolStandings from "$lib/components/PoolStandings.svelte";
import type { PageData } from "./$types";

const { data }: { data: PageData } = $props();

// Season selector
let selectedSeason = $state<string | number>("");
let activeMobileTab = $state(0);

$effect(() => {
    if (data.seasons.length && !data.seasons.includes(selectedSeason)) {
        selectedSeason = data.seasons[0];
    }
});

// Auto adjust active tab when switching seasons so we never land on a non-existent tab
$effect(() => {
    // Ensure active tab is within the available rounds bounds
    if (activeMobileTab >= bracketRounds.length) {
        activeMobileTab = Math.max(0, bracketRounds.length - 1);
    }
});

// Reactive derived metrics - filter on selected season (Svelte 5 Runes)
const filteredGames = $derived(data.games.filter(g => g.season === selectedSeason));
const filteredFullGames = $derived(data.allGames.filter(g => g.season === selectedSeason));

const totalGames = $derived(filteredGames.length);
const oneRunGames = $derived(filteredGames.filter(g => g.is_one_run_game).length);
const mercyRulesCount = $derived(filteredGames.filter(g => g.is_mercy_rule).length);
const oneRunPercentage = $derived(totalGames > 0 ? Math.round((oneRunGames / totalGames) * 100) : 0);
const mercyRulePercentage = $derived(totalGames > 0 ? Math.round((mercyRulesCount / totalGames) * 100) : 0);
const highestScoringGame = $derived(filteredFullGames.length > 0 ? filteredFullGames.reduce((max, g) => {
    return (g.away_score + g.home_score) > (max.away_score + max.home_score) ? g : max;
}, filteredFullGames[0]) : null);

const highestTotalRuns = $derived(highestScoringGame ? (highestScoringGame.away_score + highestScoringGame.home_score) : 0);

// Pool standings - filtered for selected season
const pools = $derived(data.pools.get(selectedSeason) || new Map());

// Calculate best run differential across all teams
const bestRunDiff = $derived.by(() => {
    const allTeams = Array.from(pools.values()).flat();
    if (allTeams.length === 0) return null;
    
    return allTeams.reduce((best, team) => 
        team.pool_run_differential > best.pool_run_differential ? team : best
    );
});

// Top scoring teams across all pools
const topScoringTeams = $derived.by(() => {
    return Array.from(pools.values())
        .flat()
        .sort((a, b) => b.pool_runs_scored - a.pool_runs_scored)
        .slice(0, 5);
});
const bracket = $derived(data.brackets.get(selectedSeason) || { qf: [], sf: [], final: null });

// Dynamic mobile bracket rounds - only show tabs that actually exist for selected season
const bracketRounds = $derived(
    (() => {
        const rounds = [];
        if (bracket.qf.length > 0) rounds.push({ label: 'Quarterfinals', index: 0 });
        rounds.push({ label: 'Semifinals', index: 1 });
        rounds.push({ label: 'Championship', index: 2 });
        return rounds;
    })()
);

// Derive champion automatically from final game winner for selected season
const champion = $derived.by(() => {
    if (!bracket.final) return null;
    
    const final = bracket.final;
    return final.away_is_winner 
        ? { 
            team_abbreviation: final.away_team_abbreviation, 
            team_name: final.away_team_name 
          }
        : { 
            team_abbreviation: final.home_team_abbreviation, 
            team_name: final.home_team_name 
          };
});

const TBD_QF = { label: "TBD", classes: "bg-surface border border-[#333348] border-dashed rounded-xl px-3 py-4 text-center text-[#555570] text-xs" };
const TBD_SF = { label: "TBD", classes: "bg-surface border border-[#333348] border-dashed rounded-xl px-4 py-5 text-center text-[#555570] text-sm" };
const TBD_FINAL = { label: "TBD", classes: "bg-surface border border-gold/20 border-dashed rounded-xl px-4 py-8 text-center text-[#555570] text-sm" };
</script>

<div class="space-y-10 animate-fade-in pb-20">

    <div>
        <h1 class="text-2xl font-bold text-white tracking-tight">Dashboard</h1>
        <p class="text-sm text-[#8888a0] mt-1">World Baseball Classic Overview</p>
    </div>

    <SeasonTabs seasons={data.seasons} selected={selectedSeason} onSelect={(s) => selectedSeason = s} />

    <div class="grid grid-cols-2 md:grid-cols-4 gap-4 max-w-4xl mx-auto">

        <div class="bg-surface border border-border rounded-xl px-5 py-5 flex flex-col items-center justify-center hover:border-border-light transition-colors relative overflow-hidden">
            <Activity class="w-4 h-4 text-red-400 absolute top-4 right-4 opacity-50" />
            <span class="text-xs text-[#8888a0] font-medium mb-1 uppercase tracking-wider">1-Run Games</span>
            <span class="text-3xl font-bold text-red-400">{oneRunGames}</span>
            <span class="text-xs text-red-400 mt-2 bg-red-400/10 px-2 py-0.5 rounded-full font-bold tracking-wide">{oneRunPercentage}% of games</span>
        </div>

        <div class="bg-surface border border-border rounded-xl px-5 py-5 flex flex-col items-center justify-center hover:border-border-light transition-colors relative overflow-hidden">
            <Flame class="w-4 h-4 text-green-400 absolute top-4 right-4 opacity-50" />
            <span class="text-xs text-[#8888a0] font-medium mb-1 uppercase tracking-wider">Best Run Diff</span>
            <span class="text-3xl font-bold text-green-400">
                {bestRunDiff ? `+${bestRunDiff.pool_run_differential}` : '+0'}
            </span>
            <span class="text-xs text-green-400 mt-2 bg-green-400/10 px-2 py-0.5 rounded-full font-bold tracking-wide">
                {bestRunDiff ? bestRunDiff.team_abbreviation : 'N/A'}
            </span>
        </div>

        <div class="bg-surface border border-border rounded-xl px-5 py-5 flex flex-col items-center justify-center hover:border-border-light transition-colors relative overflow-hidden">
            <Rocket class="w-4 h-4 text-blue-400 absolute top-4 right-4 opacity-50" />
            <span class="text-xs text-[#8888a0] font-medium mb-1 uppercase tracking-wider">Top Scoring Team</span>
            <span class="text-3xl font-bold text-blue-400">{topScoringTeams[0]?.pool_runs_scored || 0}</span>
            <span class="text-xs text-blue-400 mt-2 bg-blue-400/10 px-2 py-0.5 rounded-full font-bold tracking-wide">
                {topScoringTeams[0] ? topScoringTeams[0].team_abbreviation : 'N/A'}
            </span>
        </div>

        <div class="bg-surface border border-border rounded-xl px-5 py-5 flex flex-col items-center justify-center hover:border-border-light transition-colors relative overflow-hidden">
            <Zap class="w-4 h-4 text-orange-400 absolute top-4 right-4 opacity-50" />
            <span class="text-xs text-[#8888a0] font-medium mb-1 uppercase tracking-wider">Mercy Rules</span>
            <span class="text-3xl font-bold text-orange-400">{mercyRulesCount}</span>
            <span class="text-xs text-orange-400 mt-2 bg-orange-400/10 px-2 py-0.5 rounded-full font-bold tracking-wide">{mercyRulePercentage}% of games</span>
        </div>
    </div>

    <section>
        <h2 class="text-lg font-semibold text-white mb-6 flex items-center gap-2">
            <Swords class="w-5 h-5 text-accent" />
            Knockout Bracket
        </h2>

            <div class="relative">

                <!-- DESKTOP BRACKET -->
                <div class="hidden md:block">
                    <div class="grid grid-cols-[auto_auto_auto] grid-rows-3 gap-5 py-6">

                        <!-- Row 1 -->
                        <div class="flex items-center">
                            <div class="w-full min-w-[200px] max-w-[275px]">
                                {#if bracket.qf[3]}
                                    <GameCard game={bracket.qf[3]} size="qf" />
                                {/if}
                            </div>
                        </div>
                        <div class="flex items-center justify-center">
                            {#if champion}
                                <div class="flex items-center gap-2 bg-gold/10 border border-gold/25 rounded-lg px-3 py-2">
                                    <Trophy class="w-4 h-4 text-gold" />
                                    <span class="text-sm font-semibold text-gold">
                                        {champion.team_abbreviation} — {selectedSeason} Champions
                                    </span>
                                </div>
                            {/if}
                        </div>
                        <div class="flex items-center justify-end">
                            <div class="w-full min-w-[200px] max-w-[275px]">
                                {#if bracket.qf[0]}
                                    <GameCard game={bracket.qf[0]} size="qf" />
                                {/if}
                            </div>
                        </div>

                        <!-- Row 2 -->
                        <div class="flex items-center justify-end">
                            <div class="w-full min-w-[200px] max-w-[300px]">
                                {#if bracket.sf[1]}
                                    <GameCard game={bracket.sf[1]} size="sf" />
                                {/if}
                            </div>
                        </div>
                        <div class="flex items-center justify-center">
                            <div class="w-full min-w-[200px] max-w-[350px]">
                                {#if bracket.final}
                                    <GameCard game={bracket.final} size="championship" />
                                {/if}
                            </div>
                        </div>
                        <div class="flex items-center">
                            <div class="w-full min-w-[200px] max-w-[300px]">
                                {#if bracket.sf[0]}
                                    <GameCard game={bracket.sf[0]} size="sf" />
                                {/if}
                            </div>
                        </div>

                        <!-- Row 3 -->
                        <div class="flex items-center">
                            <div class="w-full min-w-[200px] max-w-[275px]">
                                {#if bracket.qf[2]}
                                    <GameCard game={bracket.qf[2]} size="qf" />
                                {/if}
                            </div>
                        </div>
                        <div></div>
                        <div class="flex items-center justify-end">
                            <div class="w-full min-w-[200px] max-w-[275px]">
                                {#if bracket.qf[1]}
                                    <GameCard game={bracket.qf[1]} size="qf" />
                                {/if}
                            </div>
                        </div>

                    </div>

                    <svg viewBox="0 0 1000 400" preserveAspectRatio="none" class="absolute inset-0 w-full h-full pointer-events-none -z-10">
                        <style>
                            @keyframes draw-bracket-line {
                                from { stroke-dashoffset: 1000; }
                                to { stroke-dashoffset: 0; }
                            }
                            .bracket-line { 
                                stroke: #60a5fa; 
                                stroke-width: 3; 
                                fill: none; 
                                vector-effect: non-scaling-stroke;
                                stroke-dasharray: 1000;
                                stroke-dashoffset: 1000;
                                animation: draw-bracket-line 1000ms ease-out forwards;
                                filter: drop-shadow(0 0 8px rgba(96, 165, 250, 0.6));
                            }
                            /* 4 Quarter Final lines animate first together */
                            .bracket-qf { animation-delay: 100ms; }
                            /* 2 Semi Final lines animate after delay */
                            .bracket-sf { animation-delay: 265ms; }
                        </style>
                        
                        <!-- LEFT SIDE QUARTER FINALS -->
                        {#if bracket.qf.length > 0}
                        <path d="M 100 97 L 200 97 L 250 195" class="bracket-line bracket-qf" />
                        <path d="M 100 293 L 200 293 L 250 195" class="bracket-line bracket-qf" />
                        
                        <!-- RIGHT SIDE QUARTER FINALS -->
                        <path d="M 900 97 L 800 97 L 750 195" class="bracket-line bracket-qf" />
                        <path d="M 900 293 L 800 293 L 750 195" class="bracket-line bracket-qf" />
                        {/if}
                        
                        <!-- SEMI FINAL TO CHAMPIONSHIP LINES -->
                        <path d="M 250 195 L 500 195" class="bracket-line bracket-sf" />
                        <path d="M 750 195 L 500 195" class="bracket-line bracket-sf" />
                    </svg>
                </div>

                <!-- MOBILE BRACKET -->
                <div class="md:hidden">
                    <div class="flex bg-surface border border-border rounded-xl mb-4 overflow-hidden">
                        {#each bracketRounds as round, i}
                            <button
                                onclick={() => activeMobileTab = i}
                                class="flex-1 min-w-0 px-2 py-3 text-xs sm:text-sm font-medium transition-colors {activeMobileTab === i ? 'bg-accent/10 text-accent border-b-2 border-accent' : 'text-[#8888a0] hover:text-white'}"
                            >
                                {round.label}
                            </button>
                        {/each}
                    </div>

                    {#if bracketRounds[activeMobileTab].index === 0}
                        <div class="flex flex-col gap-4">
                            {#each bracket.qf as game}
                                <GameCard {game} size="qf" />
                            {/each}
                            {#if bracket.qf.length === 0}
                                <div class={TBD_QF.classes}>Quarterfinals TBD</div>
                            {/if}
                        </div>
                    {:else if bracketRounds[activeMobileTab].index === 1}
                        <div class="flex flex-col gap-4">
                            {#each bracket.sf as game}
                                <GameCard {game} size="sf" />
                            {/each}
                        </div>
                    {:else if bracketRounds[activeMobileTab].index === 2}
                        <div class="max-w-md mx-auto">
                            {#if bracket.final}
                                <GameCard game={bracket.final} size="championship" />
                            {:else}
                                <div class={TBD_FINAL.classes}>{TBD_FINAL.label}</div>
                            {/if}
                        </div>
                    {/if}
                </div>
            </div>
    </section>


    <section class="space-y-6">
        <h2 class="text-lg font-semibold text-white mb-6 flex items-center gap-2">
            <TrendingUp class="w-5 h-5 text-accent" />
            Pool Standings
        </h2>


         <div class="grid grid-cols-1 md:grid-cols-2 gap-5 max-w-7xl mx-auto">
            {#each Array.from(pools) as [poolName, teams]}
                <PoolStandings {poolName} {teams} />
            {/each}
        </div>
    </section>

    <section>
        <h2 class="text-lg font-semibold text-white mb-6 flex items-center gap-2">
            <Clock class="w-5 h-5 text-accent" />
            Recent Results
        </h2>
        {#if data.recentGames.length === 0}
            <EmptyState title="No completed games found" />
        {:else}
            <div class="flex flex-col gap-3">
                {#each data.recentGames as game}
                    <GameCard {game} />
                {/each}
            </div>
        {/if}
    </section>
</div>