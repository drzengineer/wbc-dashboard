<script lang="ts">
import { TrendingUp, Trophy, Swords, Clock } from "lucide-svelte";
import EmptyState from "$lib/components/EmptyState.svelte";
import GameCard from "$lib/components/GameCard.svelte";
import SeasonTabs from "$lib/components/SeasonTabs.svelte";
import PoolStandings from "$lib/components/PoolStandings.svelte";
import HeaderStats from "$lib/components/HeaderStats.svelte";
import type { MainPageData } from "$lib/types";

// ─── Component State & Props ─────────────────────────────────────────────────
let { data }: { data: MainPageData } = $props();

let selectedSeason = $state(0);
let activeMobileTab = $state(0);

// Default to most recent season if not set
$effect(() => {
    if (data.seasons.length && !data.seasons.includes(selectedSeason)) {
        selectedSeason = data.seasons[0];
    }
});

// ─── Derived UI Metrics ──────────────────────────────────────────────────────
const currentGames = $derived(data.allGames.filter(g => g.season === selectedSeason));
const totalGames = $derived(currentGames.length);

const oneRunGames = $derived(currentGames.filter(g => g.is_one_run_game).length);
const oneRunPercentage = $derived(totalGames > 0 ? Math.round((oneRunGames / totalGames) * 100) : 0);

const mercyRulesCount = $derived(currentGames.filter(g => g.is_mercy_rule).length);
const mercyRulePercentage = $derived(totalGames > 0 ? Math.round((mercyRulesCount / totalGames) * 100) : 0);

// ─── Derived Team Standings & Totals ─────────────────────────────────────────
const pools = $derived(data.pools[selectedSeason] || {});
const seasonTeams = $derived(Object.values(data.seasonTeamTotals[selectedSeason] || {}));

const bestRunDiff = $derived.by(() => {
    if (!seasonTeams.length) return null;
    return seasonTeams.reduce((best, team) => 
        team.total_run_differential > best.total_run_differential ? team : best
    );
});

const topScoringTeam = $derived.by(() => {
    if (!seasonTeams.length) return null;
    return seasonTeams.reduce((best, team) => 
        team.total_runs_scored > best.total_runs_scored ? team : best
    );
});

// ─── Derived Bracket Data ────────────────────────────────────────────────────
const bracket = $derived(data.brackets[selectedSeason] || { qf: [], sf: [], final: null });

// Only show tabs for rounds that actually exist
const mobileRounds = $derived([
    ...(bracket.qf.length > 0 ? [{ label: 'Quarterfinals', index: 0 }] : []),
    { label: 'Semifinals', index: 1 },
    { label: 'Championship', index: 2 }
]);

const champion = $derived.by(() => {
    if (!bracket.final) return null;
    const final = bracket.final;
    return final.away_is_winner 
        ? { abbr: final.away_team_abbreviation, name: final.away_team_name }
        : { abbr: final.home_team_abbreviation, name: final.home_team_name };
});

const TBD_CLASSES = "bg-surface border border-[#333348] border-dashed rounded-xl px-4 py-8 text-center text-[#555570] text-sm";
</script>

<div class="space-y-10 animate-fade-in pb-20">

    <div>
        <h1 class="text-2xl font-bold text-white tracking-tight">Dashboard</h1>
        <p class="text-sm text-[#8888a0] mt-1">World Baseball Classic Overview</p>
    </div>

    <SeasonTabs 
        seasons={data.seasons} 
        selected={selectedSeason} 
        onSelect={(s) => {
            selectedSeason = Number(s);
            activeMobileTab = 0;
        }} 
    />

    <HeaderStats 
        {oneRunGames} 
        {oneRunPercentage} 
        {mercyRulesCount} 
        {mercyRulePercentage} 
        {bestRunDiff} 
        {topScoringTeam} 
    />

    <section>
        <h2 class="text-lg font-semibold text-white mb-6 flex items-center gap-2">
            <Swords class="w-5 h-5 text-accent" />
            Knockout Bracket
        </h2>

        <div class="relative max-w-7xl mx-auto">
            <div class="hidden md:block">
                <div class="grid grid-cols-[auto_auto_auto] grid-rows-3 gap-5 py-6">

                    <div class="flex items-center">
                        <div class="w-full min-w-50 max-w-63">
                            {#if bracket.qf[3]}<GameCard game={bracket.qf[3]} size="qf" />{/if}
                        </div>
                    </div>
                    
                    <div class="flex items-center justify-center">
                        {#if champion}
                            <div class="flex items-center gap-2 bg-gold/10 border border-gold/25 rounded-lg px-3 py-2">
                                <Trophy class="w-4 h-4 text-gold" />
                                <span class="text-sm font-semibold text-gold">{champion.abbr} — {selectedSeason} Champions</span>
                            </div>
                        {/if}
                    </div>
                    
                    <div class="flex items-center justify-end">
                        <div class="w-full min-w-50 max-w-63">
                            {#if bracket.qf[0]}<GameCard game={bracket.qf[0]} size="qf" />{/if}
                        </div>
                    </div>

                    <div class="flex items-center justify-end">
                        <div class="w-full min-w-50 max-w-67">
                            {#if bracket.sf[1]}<GameCard game={bracket.sf[1]} size="sf" />{/if}
                        </div>
                    </div>

                    <div class="flex items-center justify-center">
                        <div class="w-full min-w-50 max-w-75">
                            {#if bracket.final}<GameCard game={bracket.final} size="championship" />{/if}
                        </div>
                    </div>
                    
                    <div class="flex items-center">
                        <div class="w-full min-w-50 max-w-67">
                            {#if bracket.sf[0]}<GameCard game={bracket.sf[0]} size="sf" />{/if}
                        </div>
                    </div>

                    <div class="flex items-center">
                        <div class="w-full min-w-50 max-w-63">
                            {#if bracket.qf[2]}<GameCard game={bracket.qf[2]} size="qf" />{/if}
                        </div>
                    </div>
                    
                    <div></div>
                    
                    <div class="flex items-center justify-end">
                        <div class="w-full min-w-50 max-w-63">
                            {#if bracket.qf[1]}<GameCard game={bracket.qf[1]} size="qf" />{/if}
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
                            stroke: #60a5fa; stroke-width: 3; fill: none; 
                            vector-effect: non-scaling-stroke;
                            stroke-dasharray: 1000; stroke-dashoffset: 1000;
                            animation: draw-bracket-line 1000ms ease-out forwards;
                            filter: drop-shadow(0 0 8px rgba(96, 165, 250, 0.6));
                        }
                        .bracket-qf { animation-delay: 100ms; }
                        .bracket-sf { animation-delay: 265ms; }
                    </style>
                    
                    {#if bracket.qf.length > 0}
                        <path d="M 100 97 L 200 97 L 250 195" class="bracket-line bracket-qf" />
                        <path d="M 100 293 L 200 293 L 250 195" class="bracket-line bracket-qf" />
                        <path d="M 900 97 L 800 97 L 750 195" class="bracket-line bracket-qf" />
                        <path d="M 900 293 L 800 293 L 750 195" class="bracket-line bracket-qf" />
                    {/if}
                    
                    <path d="M 250 195 L 500 195" class="bracket-line bracket-sf" />
                    <path d="M 750 195 L 500 195" class="bracket-line bracket-sf" />
                </svg>
            </div>

            <div class="md:hidden">
                <div class="flex bg-surface border border-border rounded-xl mb-4 overflow-hidden">
                    {#each mobileRounds as round, i}
                        <button
                            onclick={() => activeMobileTab = i}
                            class="flex-1 min-w-0 px-2 py-3 text-xs sm:text-sm font-medium transition-colors {activeMobileTab === i ? 'bg-accent/10 text-accent border-b-2 border-accent' : 'text-[#8888a0] hover:text-white'}"
                        >
                            {round.label}
                        </button>
                    {/each}
                </div>

                <div class="flex flex-col gap-4 max-w-md mx-auto">
                    {#if mobileRounds[activeMobileTab].index === 0}
                        {#each bracket.qf as game} <GameCard {game} size="qf" /> {/each}
                        {#if bracket.qf.length === 0} <div class={TBD_CLASSES}>Quarterfinals TBD</div> {/if}
                    
                    {:else if mobileRounds[activeMobileTab].index === 1}
                        {#each bracket.sf as game} <GameCard {game} size="sf" /> {/each}
                    
                    {:else if mobileRounds[activeMobileTab].index === 2}
                        {#if bracket.final} <GameCard game={bracket.final} size="championship" />
                        {:else} <div class={TBD_CLASSES}>TBD</div> {/if}
                    {/if}
                </div>
            </div>
        </div>
    </section>

    <section class="space-y-6">
        <h2 class="text-lg font-semibold text-white mb-6 flex items-center gap-2">
            <TrendingUp class="w-5 h-5 text-accent" />
            Pool Standings
        </h2>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-5 max-w-7xl mx-auto">
            {#each Object.entries(pools) as [poolName, teams]}
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
            <div class="flex flex-col gap-3 max-w-5xl mx-auto">
                {#each data.recentGames as game}
                    <GameCard {game} />
                {/each}
            </div>
        {/if}
    </section>
</div>