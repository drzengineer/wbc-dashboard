<script lang="ts">
import { Target, TrendingUp, Trophy, Zap, Flame, Activity, Swords, Hash, Rocket, Clock } from "lucide-svelte";
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

// Reactive derived metrics - filter on selected season (Svelte 5 Runes)
const filteredGames = $derived(data.games.filter(g => g.season === selectedSeason));
const totalGames = $derived(filteredGames.length);
const oneRunGames = $derived(filteredGames.filter(g => g.is_one_run_game).length);
const mercyRulesCount = $derived(filteredGames.filter(g => g.is_mercy_rule).length);
const oneRunPercentage = $derived(totalGames > 0 ? Math.round((oneRunGames / totalGames) * 100) : 0);
const mercyRulePercentage = $derived(totalGames > 0 ? Math.round((mercyRulesCount / totalGames) * 100) : 0);
const highestScoringGame = $derived(filteredGames.reduce((max, g) => Math.max(max, g.total_runs), 0));

// ALL PLACEHOLDERS - WILL IMPLEMENT PROPERLY FROM DIM/FCT TABLES
const bestRunDiff = null;
const highestScoringGameObj = null;
const champion = null;
const bracket = { qf: [], sf: [], final: null };
const pools = new Map();
const topOffenses = [];
const maxRuns = 1;

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
            <span class="text-3xl font-bold text-green-400">+0</span>
            <span class="text-xs text-green-400 mt-2 bg-green-400/10 px-2 py-0.5 rounded-full font-bold tracking-wide">
                N/A
            </span>
        </div>

        <div class="bg-surface border border-border rounded-xl px-5 py-5 flex flex-col items-center justify-center hover:border-border-light transition-colors relative overflow-hidden">
            <Rocket class="w-4 h-4 text-blue-400 absolute top-4 right-4 opacity-50" />
            <span class="text-xs text-[#8888a0] font-medium mb-1 uppercase tracking-wider">Top-scoring game</span>
            <span class="text-3xl font-bold text-blue-400">{highestScoringGame}</span>
            <span class="text-xs text-blue-400 mt-2 bg-blue-400/10 px-2 py-0.5 rounded-full font-bold tracking-wide">
                TBD vs TBD
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

        <div class="flex flex-col items-center gap-6">
            <div class="w-full max-w-lg">
                <div class={TBD_FINAL.classes}>{TBD_FINAL.label}</div>
            </div>
            <div class="w-full max-w-5xl grid grid-cols-1 sm:grid-cols-2 gap-4">
                {#each Array(2) as _, idx}
                    <div class={TBD_SF.classes}>{TBD_SF.label}</div>
                {/each}
            </div>
        </div>
    </section>


    <section class="space-y-6">
        <h2 class="text-lg font-semibold text-white mb-6 flex items-center gap-2">
            <TrendingUp class="w-5 h-5 text-accent" />
            Pool Standings
        </h2>

        <section class="bg-surface border border-border rounded-xl p-5 max-w-2xl mx-auto">
            <h3 class="text-sm font-semibold text-white mb-4">Top Scoring Teams</h3>
            <div class="text-center text-[#8888a0] py-4">
                Data will load here
            </div>
        </section>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-5 max-w-7xl mx-auto">
            <EmptyState title="Pool standings will appear here" />
        </div>
    </section>

    <section>
        <h2 class="text-lg font-semibold text-white mb-6 flex items-center gap-2">
            <Clock class="w-5 h-5 text-accent" />
            Recent Results
        </h2>
        <EmptyState title="No completed games found" />
    </section>
</div>