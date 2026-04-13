<script lang="ts">
import { Check, ChevronDown } from "lucide-svelte";
import { onMount } from "svelte";
import Flag from "$lib/components/Flag.svelte";
import LoadingSpinner from "$lib/components/LoadingSpinner.svelte";
import SeasonTabs from "$lib/components/SeasonTabs.svelte";
import { fmtAvg, fmtIp, fmtNum } from "$lib/utils";
import GameDetailTableSection from "$lib/components/GameDetailTableSection.svelte";
import type { PageData } from "./$types";

const { data }: { data: PageData } = $props();

let isLeaderboardExpanded = $state(true);
function toggleLeaderboardExpansion() {
	isLeaderboardExpanded = !isLeaderboardExpanded;
}

type Tab = "Batting" | "Pitching";
let activeTab = $state<Tab>("Batting");

const batters = $derived(data.batters as any[]);
const pitchers = $derived(data.pitchers as any[]);

const seasons = $derived(
	[...new Set([...batters, ...pitchers].map((p: any) => p.season))].sort(
		(a, b) => Number(b) - Number(a),
	),
);
let selectedSeason = $state(seasons[0] ?? 2026);

// Sort keys
type BatStat =
	| "games_played"
	| "season_batting_ab"
	| "season_batting_avg"
	| "season_batting_hr"
	| "season_batting_rbi"
	| "season_batting_obp"
	| "season_batting_slg"
	| "season_batting_ops"
	| "season_batting_sb";
let batSortKey = $state<BatStat>("season_batting_ops");

type PitStat =
	| "games_played"
	| "season_pitching_era"
	| "season_pitching_ip"
	| "season_pitching_so"
	| "season_pitching_bb"
	| "season_pitching_w"
	| "season_pitching_l"
	| "season_pitching_sv";
let pitSortKey = $state<PitStat>("season_pitching_era");

// Team filter
let selectedTeams = $state<string[]>([]);
let teamDropdownOpen = $state(false);

const teams = $derived(
	[
		...new Set(
			[...batters, ...pitchers]
				.filter((p: any) => p.season === selectedSeason)
				.map((p: any) => p.team_abbreviation),
		),
	].sort(),
);

function toggleTeam(team: string) {
	if (selectedTeams.includes(team)) {
		selectedTeams = selectedTeams.filter((t) => t !== team);
	} else {
		selectedTeams = [...selectedTeams, team];
	}
}

function clearTeams() {
	selectedTeams = [];
}

// Sorting
const ascendingPitStats = new Set([
	"season_pitching_era",
	"season_pitching_bb",
	"season_pitching_l",
]);

const sortedBatters = $derived(
	batters
		.filter((p: any) => p.season === selectedSeason)
		.filter((p: any) => p.season_batting_ab > 0)
		.filter(
			(p: any) =>
				selectedTeams.length === 0 ||
				selectedTeams.includes(p.team_abbreviation),
		)
		.sort((a: any, b: any) => Number(b[batSortKey]) - Number(a[batSortKey])),
);

const sortedPitchers = $derived(
	pitchers
		.filter((p: any) => p.season === selectedSeason)
		.filter((p: any) => (p.season_pitching_ip ?? 0) > 0)
		.filter(
			(p: any) =>
				selectedTeams.length === 0 ||
				selectedTeams.includes(p.team_abbreviation),
		)
		.sort((a: any, b: any) => {
			const av = Number(a[pitSortKey]);
			const bv = Number(b[pitSortKey]);
			return ascendingPitStats.has(pitSortKey) ? av - bv : bv - av;
		}),
);

// Infinite scroll
let visibleCount = $state(30);
let sentinelRef = $state<HTMLElement | null>(null);

onMount(() => {
	const io = new IntersectionObserver(
		(entries) => {
			if (entries[0].isIntersecting) visibleCount += 30;
		},
		{ rootMargin: "200px" },
	);
	if (sentinelRef) io.observe(sentinelRef);
	return () => io.disconnect();
});

$effect(() => {
	selectedSeason;
	activeTab;
	batSortKey;
	pitSortKey;
	selectedTeams;
	visibleCount = 30;
});

const displayRows = $derived(
	(activeTab === "Batting" ? sortedBatters : sortedPitchers).slice(
		0,
		visibleCount,
	),
);
const totalRows = $derived(
	(activeTab === "Batting" ? sortedBatters : sortedPitchers).length,
);

function sortClass(key: string, currentKey: string) {
	return key === currentKey
		? "text-accent font-semibold"
		: "text-[#8888a0] hover:text-white";
}
</script>

<div class="space-y-8 animate-fade-in">
	<!-- Header -->
	<div>
		<h1 class="text-2xl font-bold text-white tracking-tight">Players</h1>
		<p class="text-sm text-[#8888a0] mt-1">Batting and pitching leaderboards</p>
	</div>

	<!-- Season tabs -->
	<SeasonTabs {seasons} selected={selectedSeason} onSelect={(s) => selectedSeason = s as number} />

	<!-- Batting/Pitching toggle + Team filter -->
	<div class="flex flex-wrap gap-3 items-center">
		<div class="flex gap-1 bg-surface border border-border rounded-lg p-1">
			{#each (['Batting', 'Pitching'] as Tab[]) as tab}
				<button
					type="button"
					onclick={() => activeTab = tab}
					class="px-4 py-1.5 rounded-md text-sm font-medium transition-all duration-200
						{activeTab === tab
							? 'bg-accent text-white shadow-lg shadow-accent/20'
							: 'text-[#8888a0] hover:text-white'}"
				>{tab}</button>
			{/each}
		</div>

		<!-- Team dropdown -->
		<div class="relative">
			<button
				type="button"
				onclick={() => teamDropdownOpen = !teamDropdownOpen}
				class="bg-surface border border-border text-[#f0f0f5] text-sm rounded-lg px-4 py-2 flex items-center gap-2 hover:border-border-light transition-colors"
			>
				<span>
					{#if selectedTeams.length === 0}All Teams
					{:else if selectedTeams.length === 1}{selectedTeams[0]}
					{:else}{selectedTeams.length} Teams{/if}
				</span>
				<ChevronDown class="w-4 h-4 transition-transform {teamDropdownOpen ? 'rotate-180' : ''}" />
			</button>
			{#if teamDropdownOpen}
				<div class="absolute z-50 mt-1 w-48 bg-surface border border-border rounded-lg shadow-xl overflow-hidden animate-fade-in">
					<div class="max-h-72 overflow-y-auto">
						<button
							type="button"
							onclick={() => clearTeams()}
							class="w-full px-4 py-2 text-left text-sm hover:bg-surface-hover transition-colors {selectedTeams.length === 0 ? 'text-accent' : 'text-[#f0f0f5]'}"
						>All Teams</button>
						{#each teams as team}
							<button
								type="button"
								onclick={() => toggleTeam(team)}
								class="w-full px-4 py-2 text-left text-sm hover:bg-surface-hover transition-colors flex items-center gap-2 {selectedTeams.includes(team) ? 'text-accent' : 'text-[#f0f0f5]'}"
							>
								<span class="w-4 h-4 border border-border-light rounded flex items-center justify-center {selectedTeams.includes(team) ? 'bg-accent border-accent' : ''}">
									{#if selectedTeams.includes(team)}
										<Check class="w-3 h-3 text-white" />
									{/if}
								</span>
								{team}
							</button>
						{/each}
					</div>
				</div>
			{/if}
		</div>
	</div>

	<!-- Leaderboard table -->
	<GameDetailTableSection 
		title={activeTab === 'Batting' ? 'Batting Leaderboard' : 'Pitching Leaderboard'}
		expanded={isLeaderboardExpanded}
		onToggle={toggleLeaderboardExpansion}
	>
		{#snippet children()}
			<table class="w-full text-sm min-w-max table-fixed">
				<thead class="text-xs text-[#8888a0] border-b border-zinc-800 bg-zinc-900/50">
					{#if activeTab === 'Batting'}
						<tr>
<th class="sticky-column text-left px-4 py-3 font-medium w-48 bg-zinc-900 z-10"># Player</th>
<th class="px-2 py-3 font-medium text-center w-24">Team</th>
<th class="px-2 py-3 font-medium text-center w-14">
	<button type="button" onclick={() => batSortKey = 'games_played'} class="w-full block transition-colors {sortClass('games_played', batSortKey)}">G</button>
</th>
<th class="px-2 py-3 font-medium text-center w-14">
	<button type="button" onclick={() => batSortKey = 'season_batting_ab'} class="w-full block transition-colors {sortClass('season_batting_ab', batSortKey)}">AB</button>
</th>
<th class="px-2 py-3 font-medium text-center w-14">
	<button type="button" onclick={() => batSortKey = 'season_batting_avg'} class="w-full block transition-colors {sortClass('season_batting_avg', batSortKey)}">AVG</button>
</th>
<th class="px-2 py-3 font-medium text-center w-14">
	<button type="button" onclick={() => batSortKey = 'season_batting_hr'} class="w-full block transition-colors {sortClass('season_batting_hr', batSortKey)}">HR</button>
</th>
<th class="px-2 py-3 font-medium text-center w-14">
	<button type="button" onclick={() => batSortKey = 'season_batting_rbi'} class="w-full block transition-colors {sortClass('season_batting_rbi', batSortKey)}">RBI</button>
</th>
<th class="px-2 py-3 font-medium text-center w-14">
	<button type="button" onclick={() => batSortKey = 'season_batting_obp'} class="w-full block transition-colors {sortClass('season_batting_obp', batSortKey)}">OBP</button>
</th>
<th class="px-2 py-3 font-medium text-center w-14">
	<button type="button" onclick={() => batSortKey = 'season_batting_slg'} class="w-full block transition-colors {sortClass('season_batting_slg', batSortKey)}">SLG</button>
</th>
<th class="px-2 py-3 font-medium text-center w-14">
	<button type="button" onclick={() => batSortKey = 'season_batting_ops'} class="w-full block transition-colors {sortClass('season_batting_ops', batSortKey)}">OPS</button>
</th>
<th class="px-2 py-3 font-medium text-center w-14">
	<button type="button" onclick={() => batSortKey = 'season_batting_sb'} class="w-full block transition-colors {sortClass('season_batting_sb', batSortKey)}">SB</button>
</th>
						</tr>
					{:else}
						<tr>
<th class="sticky-column text-left px-4 py-3 font-medium w-48 bg-zinc-900 z-10"># Player</th>
<th class="px-2 py-3 font-medium text-center w-24">Team</th>
<th class="px-2 py-3 font-medium text-center w-14">
	<button type="button" onclick={() => pitSortKey = 'games_played'} class="w-full block transition-colors {sortClass('games_played', pitSortKey)}">G</button>
</th>
<th class="px-2 py-3 font-medium text-center w-14">
	<button type="button" onclick={() => pitSortKey = 'season_pitching_era'} class="w-full block transition-colors {sortClass('season_pitching_era', pitSortKey)}">ERA</button>
</th>
<th class="px-2 py-3 font-medium text-center w-14">
	<button type="button" onclick={() => pitSortKey = 'season_pitching_ip'} class="w-full block transition-colors {sortClass('season_pitching_ip', pitSortKey)}">IP</button>
</th>
<th class="px-2 py-3 font-medium text-center w-14">
	<button type="button" onclick={() => pitSortKey = 'season_pitching_so'} class="w-full block transition-colors {sortClass('season_pitching_so', pitSortKey)}">K</button>
</th>
<th class="px-2 py-3 font-medium text-center w-14">
	<button type="button" onclick={() => pitSortKey = 'season_pitching_bb'} class="w-full block transition-colors {sortClass('season_pitching_bb', pitSortKey)}">BB</button>
</th>
<th class="px-2 py-3 font-medium text-center w-14">
	<button type="button" onclick={() => pitSortKey = 'season_pitching_w'} class="w-full block transition-colors {sortClass('season_pitching_w', pitSortKey)}">W</button>
</th>
<th class="px-2 py-3 font-medium text-center w-14">
	<button type="button" onclick={() => pitSortKey = 'season_pitching_l'} class="w-full block transition-colors {sortClass('season_pitching_l', pitSortKey)}">L</button>
</th>
<th class="px-2 py-3 font-medium text-center w-14">
	<button type="button" onclick={() => pitSortKey = 'season_pitching_sv'} class="w-full block transition-colors {sortClass('season_pitching_sv', pitSortKey)}">SV</button>
</th>
						</tr>
					{/if}
				</thead>
				<tbody>
					{#each displayRows as row, i (row.person_id + '_' + row.season)}
						<tr class="border-b border-zinc-800/50 last:border-0 hover:bg-zinc-800/30 transition-colors">
							{#if activeTab === 'Batting'}
<td class="sticky-column px-4 py-2.5 bg-zinc-900 z-10">
	<div class="flex items-center gap-3">
		<span class="text-[#555570] text-xs w-4">{i + 1}</span>
		<a href="/players/{row.person_id}" class="font-medium text-white hover:text-accent transition-colors truncate">{row.full_name}</a>
	</div>
</td>
<td class="px-2 py-2.5 text-center">
	<div class="flex items-center justify-center gap-2">
		<Flag country={row.team_abbreviation} size="md" />
		<span class="text-[#8888a0]">{row.team_abbreviation}</span>
	</div>
</td>
								<td class="px-2 py-2.5 text-center tabular-nums {batSortKey === 'games_played' ? 'text-accent font-semibold' : 'text-[#8888a0]'}">{fmtNum(row.games_played)}</td>
								<td class="px-2 py-2.5 text-center tabular-nums {batSortKey === 'season_batting_ab' ? 'text-accent font-semibold' : 'text-[#8888a0]'}">{fmtNum(row.season_batting_ab)}</td>
								<td class="px-2 py-2.5 text-center tabular-nums font-mono {batSortKey === 'season_batting_avg' ? 'text-accent font-semibold' : 'text-[#f0f0f5]'}">{fmtAvg(row.season_batting_avg)}</td>
								<td class="px-2 py-2.5 text-center tabular-nums {batSortKey === 'season_batting_hr' ? 'text-accent font-semibold' : 'text-[#f0f0f5]'}">{fmtNum(row.season_batting_hr)}</td>
								<td class="px-2 py-2.5 text-center tabular-nums {batSortKey === 'season_batting_rbi' ? 'text-accent font-semibold' : 'text-[#f0f0f5]'}">{fmtNum(row.season_batting_rbi)}</td>
								<td class="px-2 py-2.5 text-center tabular-nums font-mono {batSortKey === 'season_batting_obp' ? 'text-accent font-semibold' : 'text-[#8888a0]'}">{fmtNum(row.season_batting_obp)}</td>
								<td class="px-2 py-2.5 text-center tabular-nums font-mono {batSortKey === 'season_batting_slg' ? 'text-accent font-semibold' : 'text-[#8888a0]'}">{fmtNum(row.season_batting_slg)}</td>
								<td class="px-2 py-2.5 text-center tabular-nums font-mono {batSortKey === 'season_batting_ops' ? 'text-accent font-semibold' : 'text-[#f0f0f5]'}">{fmtAvg(row.season_batting_ops)}</td>
								<td class="px-2 py-2.5 text-center tabular-nums {batSortKey === 'season_batting_sb' ? 'text-accent font-semibold' : 'text-[#8888a0]'}">{fmtNum(row.season_batting_sb)}</td>
							{:else}
<td class="sticky-column px-4 py-2.5 bg-zinc-900 z-10">
	<div class="flex items-center gap-3">
		<span class="text-[#555570] text-xs w-4">{i + 1}</span>
		<a href="/players/{row.person_id}" class="font-medium text-white hover:text-accent transition-colors truncate">{row.full_name}</a>
	</div>
</td>
<td class="px-2 py-2.5 text-center">
	<div class="flex items-center justify-center gap-2">
		<Flag country={row.team_abbreviation} size="md" />
		<span class="text-[#8888a0]">{row.team_abbreviation}</span>
	</div>
</td>
								<td class="px-2 py-2.5 text-center tabular-nums {pitSortKey === 'games_played' ? 'text-accent font-semibold' : 'text-[#8888a0]'}">{fmtNum(row.games_played)}</td>
								<td class="px-2 py-2.5 text-center tabular-nums font-mono {pitSortKey === 'season_pitching_era' ? 'text-accent font-semibold' : 'text-[#f0f0f5]'}">{fmtNum(row.season_pitching_era)}</td>
								<td class="px-2 py-2.5 text-center tabular-nums font-mono {pitSortKey === 'season_pitching_ip' ? 'text-accent font-semibold' : 'text-[#f0f0f5]'}">{fmtIp(row.season_pitching_ip)}</td>
								<td class="px-2 py-2.5 text-center tabular-nums {pitSortKey === 'season_pitching_so' ? 'text-accent font-semibold' : 'text-[#f0f0f5]'}">{fmtNum(row.season_pitching_so)}</td>
								<td class="px-2 py-2.5 text-center tabular-nums {pitSortKey === 'season_pitching_bb' ? 'text-accent font-semibold' : 'text-[#8888a0]'}">{fmtNum(row.season_pitching_bb)}</td>
								<td class="px-2 py-2.5 text-center tabular-nums {pitSortKey === 'season_pitching_w' ? 'text-accent font-semibold' : 'text-[#f0f0f5]'}">{fmtNum(row.season_pitching_w)}</td>
								<td class="px-2 py-2.5 text-center tabular-nums {pitSortKey === 'season_pitching_l' ? 'text-accent font-semibold' : 'text-[#8888a0]'}">{fmtNum(row.season_pitching_l)}</td>
								<td class="px-2 py-2.5 text-center tabular-nums {pitSortKey === 'season_pitching_sv' ? 'text-accent font-semibold' : 'text-[#8888a0]'}">{fmtNum(row.season_pitching_sv)}</td>
							{/if}
						</tr>
					{/each}
				</tbody>
			</table>
		{/snippet}
	</GameDetailTableSection>

	<!-- Count -->
	<p class="text-xs text-[#555570]">Showing {Math.min(visibleCount, totalRows)} of {totalRows} players</p>

	<!-- Infinite scroll sentinel -->
	{#if visibleCount < totalRows}
		<div bind:this={sentinelRef} class="mt-4 flex justify-center">
			<LoadingSpinner />
		</div>
	{/if}
</div>