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
type BatSortKey = BatStat | `-${BatStat}`;
let batSortKey = $state<BatSortKey>("season_batting_avg");

type PitStat =
	| "games_played"
	| "season_pitching_era"
	| "season_pitching_ip"
	| "season_pitching_so"
	| "season_pitching_bb"
	| "season_pitching_w"
	| "season_pitching_l"
	| "season_pitching_sv";
type PitSortKey = PitStat | `-${PitStat}`;
let pitSortKey = $state<PitSortKey>("season_pitching_era");

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
		.sort((a: any, b: any) => {
			const isAsc = batSortKey.startsWith('-');
			const key = isAsc ? batSortKey.slice(1) : batSortKey;
			return (Number(b[key]) - Number(a[key])) * (isAsc ? -1 : 1);
		}),
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
			const isAsc = pitSortKey.startsWith('-');
			const key = isAsc ? pitSortKey.slice(1) : pitSortKey;
			const av = Number(a[key]);
			const bv = Number(b[key]);
			const base = ascendingPitStats.has(key) ? av - bv : bv - av;
			return base * (isAsc ? -1 : 1);
		}),
);

// Pagination
let currentPage = $state(1);
let itemsPerPage = $state(20);

$effect(() => {
	selectedSeason;
	activeTab;
	batSortKey;
	pitSortKey;
	selectedTeams;
	currentPage = 1;
});

const totalRows = $derived(
	(activeTab === "Batting" ? sortedBatters : sortedPitchers).length,
);
const totalPages = $derived(Math.ceil(totalRows / itemsPerPage));
const startIndex = $derived((currentPage - 1) * itemsPerPage);
const endIndex = $derived(Math.min(currentPage * itemsPerPage, totalRows));

const displayRows = $derived(
	(activeTab === "Batting" ? sortedBatters : sortedPitchers).slice(
		startIndex,
		endIndex,
	),
);

function goToPage(page: number) {
	if (page >= 1 && page <= totalPages) {
		currentPage = page;
		window.scrollTo({ top: 0, behavior: 'smooth' });
	}
}

function getVisiblePageNumbers() {
	const pages: (number | string)[] = [];
	const maxVisible = 5;
	
	if (totalPages <= maxVisible) {
		for (let i = 1; i <= totalPages; i++) pages.push(i);
	} else {
		pages.push(1);
		
		if (currentPage > 3) pages.push('...');
		
		const start = Math.max(2, currentPage - 1);
		const end = Math.min(totalPages - 1, currentPage + 1);
		
		for (let i = start; i <= end; i++) pages.push(i);
		
		if (currentPage < totalPages - 2) pages.push('...');
		
		pages.push(totalPages);
	}
	
	return pages;
}

function toggleBatSort(key: BatStat) {
	batSortKey = batSortKey === key ? `-${key}` as BatSortKey : batSortKey === `-${key}` ? key : key;
}

function togglePitSort(key: PitStat) {
	pitSortKey = pitSortKey === key ? `-${key}` as PitSortKey : pitSortKey === `-${key}` ? key : key;
}

function sortClass(key: string, currentKey: string) {
	if (currentKey === key) return "text-accent font-semibold";
	if (currentKey === `-${key}`) return "text-red-400 font-semibold";
	return "text-[#8888a0] hover:text-white";
}

function valueClass(key: string, currentKey: string) {
	if (currentKey === key) return "text-accent font-semibold";
	if (currentKey === `-${key}`) return "text-red-400 font-semibold";
	return "text-[#f0f0f5]";
}
</script>

<div class="space-y-8 animate-fade-in">
	<!-- Header -->
	<div>
		<h1 class="text-2xl font-bold text-white tracking-tight">Players</h1>
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
		expanded={true}
		collapsible={false}
		onToggle={() => {}}
	>
		{#snippet children()}
			<table class="w-full text-sm min-w-max table-fixed">
				<thead class="bg-zinc-950/50 text-zinc-400 uppercase tracking-wider text-xs sm:text-sm font-medium border-b border-zinc-800">
					{#if activeTab === 'Batting'}
						<tr>
<th class="sticky-column text-left py-3 px-4 w-62.5 bg-[#111113] z-10"># Player</th>
<th class="px-2 py-3 font-medium text-center w-22">Team</th>
<th class="px-2 py-3 font-medium text-center w-14">
	<button type="button" onclick={() => toggleBatSort('games_played')} class="w-full block transition-colors {sortClass('games_played', batSortKey)}">G</button>
</th>
<th class="px-2 py-3 font-medium text-center w-14">
	<button type="button" onclick={() => toggleBatSort('season_batting_ab')} class="w-full block transition-colors {sortClass('season_batting_ab', batSortKey)}">AB</button>
</th>
<th class="px-2 py-3 font-medium text-center w-14">
	<button type="button" onclick={() => toggleBatSort('season_batting_avg')} class="w-full block transition-colors {sortClass('season_batting_avg', batSortKey)}">AVG</button>
</th>
<th class="px-2 py-3 font-medium text-center w-14">
	<button type="button" onclick={() => toggleBatSort('season_batting_hr')} class="w-full block transition-colors {sortClass('season_batting_hr', batSortKey)}">HR</button>
</th>
<th class="px-2 py-3 font-medium text-center w-14">
	<button type="button" onclick={() => toggleBatSort('season_batting_rbi')} class="w-full block transition-colors {sortClass('season_batting_rbi', batSortKey)}">RBI</button>
</th>
<th class="px-2 py-3 font-medium text-center w-14">
	<button type="button" onclick={() => toggleBatSort('season_batting_sb')} class="w-full block transition-colors {sortClass('season_batting_sb', batSortKey)}">SB</button>
</th>
<th class="px-2 py-3 font-medium text-center w-14">
	<button type="button" onclick={() => toggleBatSort('season_batting_obp')} class="w-full block transition-colors {sortClass('season_batting_obp', batSortKey)}">OBP</button>
</th>
<th class="px-2 py-3 font-medium text-center w-14">
	<button type="button" onclick={() => toggleBatSort('season_batting_slg')} class="w-full block transition-colors {sortClass('season_batting_slg', batSortKey)}">SLG</button>
</th>
<th class="px-2 py-3 font-medium text-center w-14">
	<button type="button" onclick={() => toggleBatSort('season_batting_ops')} class="w-full block transition-colors {sortClass('season_batting_ops', batSortKey)}">OPS</button>
</th>
						</tr>
					{:else}
						<tr>
<th class="sticky-column text-left py-3 px-4 w-62.5 bg-[#111113] z-10"># Player</th>
<th class="px-2 py-3 font-medium text-center w-22">Team</th>
<th class="px-2 py-3 font-medium text-center w-14">
	<button type="button" onclick={() => togglePitSort('games_played')} class="w-full block transition-colors {sortClass('games_played', pitSortKey)}">G</button>
</th>
<th class="px-2 py-3 font-medium text-center w-14">
	<button type="button" onclick={() => togglePitSort('season_pitching_era')} class="w-full block transition-colors {sortClass('season_pitching_era', pitSortKey)}">ERA</button>
</th>
<th class="px-2 py-3 font-medium text-center w-14">
	<button type="button" onclick={() => togglePitSort('season_pitching_ip')} class="w-full block transition-colors {sortClass('season_pitching_ip', pitSortKey)}">IP</button>
</th>
<th class="px-2 py-3 font-medium text-center w-14">
	<button type="button" onclick={() => togglePitSort('season_pitching_so')} class="w-full block transition-colors {sortClass('season_pitching_so', pitSortKey)}">K</button>
</th>
<th class="px-2 py-3 font-medium text-center w-14">
	<button type="button" onclick={() => togglePitSort('season_pitching_bb')} class="w-full block transition-colors {sortClass('season_pitching_bb', pitSortKey)}">BB</button>
</th>
<th class="px-2 py-3 font-medium text-center w-14">
	<button type="button" onclick={() => togglePitSort('season_pitching_w')} class="w-full block transition-colors {sortClass('season_pitching_w', pitSortKey)}">W</button>
</th>
<th class="px-2 py-3 font-medium text-center w-14">
	<button type="button" onclick={() => togglePitSort('season_pitching_l')} class="w-full block transition-colors {sortClass('season_pitching_l', pitSortKey)}">L</button>
</th>
<th class="px-2 py-3 font-medium text-center w-14">
	<button type="button" onclick={() => togglePitSort('season_pitching_sv')} class="w-full block transition-colors {sortClass('season_pitching_sv', pitSortKey)}">SV</button>
</th>
						</tr>
					{/if}
				</thead>
				<tbody>
					{#each displayRows as row, i (row.person_id + '_' + row.season)}
						<tr class="border-b border-zinc-800/50 last:border-0 hover:bg-zinc-800/30 transition-colors">
							{#if activeTab === 'Batting'}
<td class="sticky-column px-4 py-2.5 z-10">
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
								<td class="px-2 py-2.5 text-center tabular-nums {valueClass('games_played', batSortKey)}">{fmtNum(row.games_played)}</td>
								<td class="px-2 py-2.5 text-center tabular-nums {valueClass('season_batting_ab', batSortKey)}">{fmtNum(row.season_batting_ab)}</td>
								<td class="px-2 py-2.5 text-center tabular-nums {valueClass('season_batting_avg', batSortKey)}">{fmtAvg(row.season_batting_avg)}</td>
								<td class="px-2 py-2.5 text-center tabular-nums {valueClass('season_batting_hr', batSortKey)}">{fmtNum(row.season_batting_hr)}</td>
								<td class="px-2 py-2.5 text-center tabular-nums {valueClass('season_batting_rbi', batSortKey)}">{fmtNum(row.season_batting_rbi)}</td>
								<td class="px-2 py-2.5 text-center tabular-nums {valueClass('season_batting_sb', batSortKey)}">{fmtNum(row.season_batting_sb)}</td>
								<td class="px-2 py-2.5 text-center tabular-nums {valueClass('season_batting_obp', batSortKey)}">{fmtNum(row.season_batting_obp)}</td>
								<td class="px-2 py-2.5 text-center tabular-nums {valueClass('season_batting_slg', batSortKey)}">{fmtNum(row.season_batting_slg)}</td>
								<td class="px-2 py-2.5 text-center tabular-nums {valueClass('season_batting_ops', batSortKey)}">{fmtAvg(row.season_batting_ops)}</td>
							{:else}
<td class="sticky-column px-4 py-2.5 z-10">
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
								<td class="px-2 py-2.5 text-center tabular-nums {valueClass('games_played', pitSortKey)}">{fmtNum(row.games_played)}</td>
								<td class="px-2 py-2.5 text-center tabular-nums {valueClass('season_pitching_era', pitSortKey)}">{fmtNum(row.season_pitching_era)}</td>
								<td class="px-2 py-2.5 text-center tabular-nums {valueClass('season_pitching_ip', pitSortKey)}">{fmtIp(row.season_pitching_ip)}</td>
								<td class="px-2 py-2.5 text-center tabular-nums {valueClass('season_pitching_so', pitSortKey)}">{fmtNum(row.season_pitching_so)}</td>
								<td class="px-2 py-2.5 text-center tabular-nums {valueClass('season_pitching_bb', pitSortKey)}">{fmtNum(row.season_pitching_bb)}</td>
								<td class="px-2 py-2.5 text-center tabular-nums {valueClass('season_pitching_w', pitSortKey)}">{fmtNum(row.season_pitching_w)}</td>
								<td class="px-2 py-2.5 text-center tabular-nums {valueClass('season_pitching_l', pitSortKey)}">{fmtNum(row.season_pitching_l)}</td>
								<td class="px-2 py-2.5 text-center tabular-nums {valueClass('season_pitching_sv', pitSortKey)}">{fmtNum(row.season_pitching_sv)}</td>
							{/if}
						</tr>
					{/each}
				</tbody>
			</table>
		{/snippet}
	</GameDetailTableSection>

	<!-- Pagination Controls -->
	<div class="flex flex-col sm:flex-row justify-center items-center gap-4 mt-6">
		<p class="text-xs text-[#555570]">
			Showing {startIndex + 1} - {endIndex} of {totalRows} players
			<span class="text-[#666680]"> | Page {currentPage} of {totalPages}</span>
		</p>

		<div class="flex items-center gap-2">
			<!-- Items per page selector -->
			<div class="flex items-center gap-2 mr-4">
				<span class="text-xs text-[#8888a0]">Show:</span>
				<select
					value={itemsPerPage}
					onchange={(e) => {
						const target = e.target as HTMLSelectElement;
						itemsPerPage = Number(target.value);
						currentPage = 1;
					}}
					class="bg-surface border border-border rounded px-2 py-1 text-sm text-[#f0f0f5] outline-none focus:border-accent cursor-pointer"
				>
					<option value={20}>20</option>
					<option value={50}>50</option>
					<option value={100}>100</option>
				</select>
			</div>

			<!-- Previous button -->
			<button
				type="button"
				onclick={() => goToPage(currentPage - 1)}
				disabled={currentPage === 1}
				class="px-3 py-1.5 text-sm rounded-md bg-surface border border-border disabled:opacity-40 disabled:cursor-not-allowed hover:border-border-light transition-colors text-[#f0f0f5]"
			>
				← Previous
			</button>

			<!-- Page numbers -->
			<div class="flex gap-1">
				{#each getVisiblePageNumbers() as page}
					{#if page === '...'}
						<span class="px-2 py-1 text-[#8888a0]">...</span>
					{:else}
						<button
							type="button"
							onclick={() => goToPage(page as number)}
							class="w-8 h-8 text-sm rounded-md transition-all duration-150
								{currentPage === page
									? 'bg-accent text-white shadow-lg shadow-accent/20'
									: 'bg-surface border border-border hover:border-border-light text-[#f0f0f5]'}"
						>{page}</button>
					{/if}
				{/each}
			</div>

			<!-- Next button -->
			<button
				type="button"
				onclick={() => goToPage(currentPage + 1)}
				disabled={currentPage === totalPages}
				class="px-3 py-1.5 text-sm rounded-md bg-surface border border-border disabled:opacity-40 disabled:cursor-not-allowed hover:border-border-light transition-colors text-[#f0f0f5]"
			>
				Next →
			</button>
		</div>
	</div>
</div>