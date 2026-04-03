<script lang="ts">
import { ArrowLeft } from "lucide-svelte";
import { onMount } from "svelte";
import Flag from "$lib/components/Flag.svelte";
import GaugeRing from "$lib/components/GaugeRing.svelte";
import LoadingSpinner from "$lib/components/LoadingSpinner.svelte";
import RadarChart from "$lib/components/RadarChart.svelte";
import { age, fmtAvg, fmtIp, fmtNum } from "$lib/utils";
import type { PageData } from "./$types";

const { data }: { data: PageData } = $props();

const player = $derived(data.player as any);
const allSeasons = $derived(data.tournamentStats as any[]);
const allGameLogs = $derived(data.gameLogs as any[]);
const maxStatsBySeason = $derived((data as any).maxStatsBySeason ?? {});
const isPitcher = $derived(player?.position_type === "Pitcher");

const seasons = $derived(
	[...new Set(allSeasons.map((s: any) => s.season))].sort(
		(a, b) => Number(b) - Number(a),
	),
);
let selectedSeason = $state(seasons[0] ?? 2026);
const currentMaxStats = $derived(maxStatsBySeason[selectedSeason] ?? { batting: {}, pitching: {} });

const seasonRow = $derived(
	allSeasons.find((s: any) => s.season === selectedSeason) ?? allSeasons[0],
);

// Game log
const seasonLogs = $derived(
	allGameLogs.filter((g: any) => g.season === selectedSeason),
);
let visibleLogCount = $state(15);
let logSentinelRef = $state<HTMLElement | null>(null);

onMount(() => {
	const io = new IntersectionObserver(
		(entries) => {
			if (entries[0].isIntersecting) visibleLogCount += 15;
		},
		{ rootMargin: "200px" },
	);
	if (logSentinelRef) io.observe(logSentinelRef);
	return () => io.disconnect();
});

$effect(() => {
	selectedSeason;
	visibleLogCount = 15;
});
const visibleLogs = $derived(seasonLogs.slice(0, visibleLogCount));

// Career totals
const hasMultipleSeasons = $derived(allSeasons.length > 1);

const careerBatting = $derived(() => {
	if (isPitcher || !hasMultipleSeasons) return null;
	return {
		g: allSeasons.reduce((s: number, r: any) => s + (r.games_played ?? 0), 0),
		ab: allSeasons.reduce(
			(s: number, r: any) => s + (r.season_batting_ab ?? 0),
			0,
		),
		h: allSeasons.reduce(
			(s: number, r: any) => s + (r.season_batting_h ?? 0),
			0,
		),
		hr: allSeasons.reduce(
			(s: number, r: any) => s + (r.season_batting_hr ?? 0),
			0,
		),
		rbi: allSeasons.reduce(
			(s: number, r: any) => s + (r.season_batting_rbi ?? 0),
			0,
		),
		r: allSeasons.reduce(
			(s: number, r: any) => s + (r.season_batting_r ?? 0),
			0,
		),
		bb: allSeasons.reduce(
			(s: number, r: any) => s + (r.season_batting_bb ?? 0),
			0,
		),
		sb: allSeasons.reduce(
			(s: number, r: any) => s + (r.season_batting_sb ?? 0),
			0,
		),
	};
});

const careerPitching = $derived(() => {
	if (!isPitcher || !hasMultipleSeasons) return null;
	const totalIp = allSeasons.reduce(
		(s: number, r: any) => s + Number(r.season_pitching_ip ?? 0),
		0,
	);
	const totalEarnedRuns = allSeasons.reduce((s: number, r: any) => {
		const era = Number(r.season_pitching_era);
		const ip = Number(r.season_pitching_ip);
		return s + (Number.isNaN(era) || Number.isNaN(ip) ? 0 : (era * ip) / 9);
	}, 0);
	const careerEra =
		totalIp > 0 ? ((totalEarnedRuns / totalIp) * 9).toFixed(2) : "—";
	return {
		era: careerEra,
		ip: totalIp,
		w: allSeasons.reduce(
			(s: number, r: any) => s + (r.season_pitching_w ?? 0),
			0,
		),
		l: allSeasons.reduce(
			(s: number, r: any) => s + (r.season_pitching_l ?? 0),
			0,
		),
		sv: allSeasons.reduce(
			(s: number, r: any) => s + (r.season_pitching_sv ?? 0),
			0,
		),
		so: allSeasons.reduce(
			(s: number, r: any) => s + (r.season_pitching_so ?? 0),
			0,
		),
		bb: allSeasons.reduce(
			(s: number, r: any) => s + (r.season_pitching_bb ?? 0),
			0,
		),
	};
});

// Radar chart data
const radarStats = $derived(() => {
	if (!seasonRow) return [];
	if (isPitcher) {
		const so = Number(seasonRow.season_pitching_so) || 0;
		const ip = Number(seasonRow.season_pitching_ip) || 0;
		const w = Number(seasonRow.season_pitching_w) || 0;
		const sv = Number(seasonRow.season_pitching_sv) || 0;
		const g = Number(seasonRow.games_played) || 0;
		const bf = Number(seasonRow.season_pitching_bf) || 0;
		const pm = currentMaxStats.pitching;
		return [
			{ label: "K", value: so, max: Math.max(Number(pm.season_pitching_so), 1) },
			{ label: "IP", value: Math.round(ip * 10), max: Math.max(Math.round(Number(pm.season_pitching_ip) * 10), 1) },
			{ label: "W", value: w, max: Math.max(Number(pm.season_pitching_w), 1) },
			{ label: "SV", value: sv, max: Math.max(Number(pm.season_pitching_sv), 1) },
			{ label: "G", value: g, max: Math.max(Number(pm.games_played), 1) },
			{ label: "BF", value: bf, max: Math.max(Number(pm.season_pitching_bf), 1) },
		];
	}
	const avg = parseFloat(seasonRow.season_batting_avg || "0") * 1000;
	const obp = parseFloat(seasonRow.season_batting_obp || "0") * 100;
	const slg = parseFloat(seasonRow.season_batting_slg || "0") * 100;
	const hr = Number(seasonRow.season_batting_hr) || 0;
	const rbi = Number(seasonRow.season_batting_rbi) || 0;
	const sb = Number(seasonRow.season_batting_sb) || 0;
	const bm = currentMaxStats.batting;
	return [
		{ label: "AVG", value: Math.round(avg), max: Math.max(Math.round(parseFloat(bm.season_batting_avg) * 1000), 1) },
		{ label: "OBP", value: Math.round(obp), max: Math.max(Math.round(parseFloat(bm.season_batting_obp) * 100), 1) },
		{ label: "SLG", value: Math.round(slg), max: Math.max(Math.round(parseFloat(bm.season_batting_slg) * 100), 1) },
		{ label: "HR", value: hr, max: Math.max(Number(bm.season_batting_hr), 1) },
		{ label: "RBI", value: rbi, max: Math.max(Number(bm.season_batting_rbi), 1) },
		{ label: "SB", value: sb, max: Math.max(Number(bm.season_batting_sb), 1) },
	];
});

// Game log helpers
function gameResult(log: any) {
	const gr = log._gr;
	if (!gr || gr.away_score == null) return "—";
	const myAbbr = log.team_abbreviation;
	const iAway = gr.away_team_abbreviation === myAbbr;
	const myScore = iAway ? gr.away_score : gr.home_score;
	const oppScore = iAway ? gr.home_score : gr.away_score;
	const oppAbbr = iAway ? gr.home_team_abbreviation : gr.away_team_abbreviation;
	const result = myScore > oppScore ? "W" : myScore < oppScore ? "L" : "T";
	return `${result} ${myScore}–${oppScore} vs ${oppAbbr}`;
}

function resultColor(log: any) {
	const gr = log._gr;
	if (!gr || gr.away_score == null) return "text-[#8888a0]";
	const myAbbr = log.team_abbreviation;
	const iAway = gr.away_team_abbreviation === myAbbr;
	const myScore = iAway ? gr.away_score : gr.home_score;
	const oppScore = iAway ? gr.home_score : gr.away_score;
	return myScore > oppScore
		? "text-success"
		: myScore < oppScore
			? "text-danger"
			: "text-[#8888a0]";
}
</script>

<div class="space-y-8 animate-fade-in">
	<!-- Back link -->
	<a href="/players" class="inline-flex items-center gap-1.5 text-sm text-[#8888a0] hover:text-accent transition-colors">
		<ArrowLeft class="w-4 h-4" />
		Players
	</a>

	<!-- Player header card -->
	<div class="bg-surface border border-border rounded-xl p-5 md:p-6">
		<div class="flex flex-col sm:flex-row sm:items-start gap-4">
			<div class="flex-1 min-w-0">
				<div class="flex items-center gap-3 flex-wrap">
					<h1 class="text-xl md:text-2xl font-bold text-white">{player?.full_name}</h1>
					<Flag country={player?.team_abbreviation} size="lg" />
				</div>
				<div class="flex flex-wrap items-center gap-2 mt-2">
					<span class="text-sm text-[#8888a0]">{player?.represented_country}</span>
					<span class="text-xs px-2 py-0.5 rounded-full bg-accent/15 text-accent border border-accent/25 font-medium">
						{player?.position_abbreviation}
					</span>
					{#if allSeasons.length > 1}
						<span class="text-xs px-2 py-0.5 rounded-full bg-surface-hover text-[#8888a0]">{allSeasons.length} WBC seasons</span>
					{/if}
				</div>
			</div>
			<div class="text-sm text-[#8888a0] space-y-1 shrink-0">
				{#if player?.birth_date}<div>Age {age(player.birth_date)}</div>{/if}
				{#if player?.height}<div>{player.height} / {player.weight} lb</div>{/if}
				{#if player?.bat_side && !isPitcher}<div>Bats {player.bat_side}</div>{/if}
				{#if player?.pitch_hand && isPitcher}<div>Throws {player.pitch_hand}</div>{/if}
			</div>
		</div>
	</div>

	<!-- Radar chart + Season stats side by side -->
	<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
		<!-- Radar chart -->
		<div class="bg-surface border border-border rounded-xl p-6">
			<h2 class="text-sm font-semibold uppercase tracking-widest text-[#8888a0] mb-4">
				{selectedSeason} Skill Profile
			</h2>
			<RadarChart
				stats={radarStats()}
				color={isPitcher ? '#a78bfa' : '#3b82f6'}
				size={260}
			/>
		</div>

		<!-- Season gauges -->
		<div class="bg-surface border border-border rounded-xl p-6">
			<h2 class="text-sm font-semibold uppercase tracking-widest text-[#8888a0] mb-4">
				{selectedSeason} Key Stats
			</h2>
			{#if seasonRow}
				{#if !isPitcher}
					<div class="grid grid-cols-3 gap-4">
						<GaugeRing
							value={parseFloat(seasonRow.season_batting_avg || '0')}
							max={currentMaxStats.batting.season_batting_avg}
							label="AVG"
							color="#3b82f6"
							formatValue={(v) => fmtAvg(v.toFixed(3))}
						/>
						<GaugeRing
							value={parseFloat(seasonRow.season_batting_ops || '0')}
							max={currentMaxStats.batting.season_batting_ops}
							label="OPS"
							color="#22c55e"
							formatValue={(v) => fmtAvg(v.toFixed(3))}
						/>
						<GaugeRing
							value={Number(seasonRow.season_batting_hr) || 0}
							max={currentMaxStats.batting.season_batting_hr}
							label="HR"
							color="#eab308"
						/>
					</div>
					<div class="grid grid-cols-4 gap-3 mt-6">
						<div class="text-center">
							<div class="text-lg font-bold text-white tabular-nums">{fmtNum(seasonRow.games_played)}</div>
							<div class="text-xs text-[#8888a0]">G</div>
						</div>
						<div class="text-center">
							<div class="text-lg font-bold text-white tabular-nums">{fmtNum(seasonRow.season_batting_rbi)}</div>
							<div class="text-xs text-[#8888a0]">RBI</div>
						</div>
						<div class="text-center">
							<div class="text-lg font-bold text-white tabular-nums">{fmtNum(seasonRow.season_batting_r)}</div>
							<div class="text-xs text-[#8888a0]">R</div>
						</div>
						<div class="text-center">
							<div class="text-lg font-bold text-white tabular-nums">{fmtNum(seasonRow.season_batting_sb)}</div>
							<div class="text-xs text-[#8888a0]">SB</div>
						</div>
					</div>
				{:else}
					<div class="grid grid-cols-3 gap-4">
						<GaugeRing
							value={Number(seasonRow.season_pitching_era) || 0}
							max={10}
							label="ERA"
							color="#a78bfa"
							formatValue={(v) => v.toFixed(2)}
						/>
						<GaugeRing
							value={Number(seasonRow.season_pitching_so) || 0}
							max={currentMaxStats.pitching.season_pitching_so}
							label="K"
							color="#22c55e"
						/>
						<GaugeRing
							value={Number(seasonRow.season_pitching_ip) || 0}
							max={currentMaxStats.pitching.season_pitching_ip}
							label="IP"
							color="#3b82f6"
							formatValue={(v) => fmtIp(v)}
						/>
					</div>
					<div class="grid grid-cols-4 gap-3 mt-6">
						<div class="text-center">
							<div class="text-lg font-bold text-white tabular-nums">{seasonRow.season_pitching_w ?? 0}</div>
							<div class="text-xs text-[#8888a0]">W</div>
						</div>
						<div class="text-center">
							<div class="text-lg font-bold text-white tabular-nums">{seasonRow.season_pitching_l ?? 0}</div>
							<div class="text-xs text-[#8888a0]">L</div>
						</div>
						<div class="text-center">
							<div class="text-lg font-bold text-white tabular-nums">{seasonRow.season_pitching_sv ?? 0}</div>
							<div class="text-xs text-[#8888a0]">SV</div>
						</div>
						<div class="text-center">
							<div class="text-lg font-bold text-white tabular-nums">{fmtNum(seasonRow.games_played)}</div>
							<div class="text-xs text-[#8888a0]">G</div>
						</div>
					</div>
				{/if}
			{/if}
		</div>
	</div>

	<!-- Career totals (multi-season only) -->
	{#if hasMultipleSeasons && (careerBatting() || careerPitching())}
		<section>
			<h2 class="text-sm font-semibold uppercase tracking-widest text-[#8888a0] mb-3">Career WBC Totals</h2>
			<div class="grid grid-cols-4 sm:grid-cols-8 gap-3">
				{#if careerBatting()}
					{@const cb = careerBatting()!}
					{#each [
						{ label: 'G', value: cb.g }, { label: 'AB', value: cb.ab },
						{ label: 'H', value: cb.h }, { label: 'HR', value: cb.hr },
						{ label: 'RBI', value: cb.rbi }, { label: 'R', value: cb.r },
						{ label: 'BB', value: cb.bb }, { label: 'SB', value: cb.sb }
					] as stat}
						<div class="bg-surface border border-border rounded-lg px-3 py-3 text-center hover:border-border-light transition-colors">
							<div class="text-lg font-bold text-white tabular-nums">{stat.value}</div>
							<div class="text-xs text-[#8888a0]">{stat.label}</div>
						</div>
					{/each}
				{/if}
				{#if careerPitching()}
					{@const cp = careerPitching()!}
					{#each [
						{ label: 'ERA', value: cp.era }, { label: 'IP', value: fmtIp(cp.ip) },
						{ label: 'W', value: cp.w }, { label: 'L', value: cp.l },
						{ label: 'SV', value: cp.sv }, { label: 'K', value: cp.so },
						{ label: 'BB', value: cp.bb }
					] as stat}
						<div class="bg-surface border border-border rounded-lg px-3 py-3 text-center hover:border-border-light transition-colors">
							<div class="text-lg font-bold text-white tabular-nums">{stat.value}</div>
							<div class="text-xs text-[#8888a0]">{stat.label}</div>
						</div>
					{/each}
				{/if}
			</div>
		</section>
	{/if}

	<!-- By-season table -->
	<section>
		<h2 class="text-sm font-semibold uppercase tracking-widest text-[#8888a0] mb-3">By Season</h2>
		<div class="bg-surface border border-border rounded-xl overflow-hidden">
			<div class="overflow-x-auto">
				<table class="w-full text-sm">
					<thead class="text-xs text-[#8888a0] border-b border-border bg-surface-hover/50">
						{#if !isPitcher}
							<tr>
								<th class="text-left px-4 py-2.5 font-medium">Year</th>
								<th class="w-8 py-2.5"></th>
								<th class="px-2 py-2.5 font-medium text-center hidden sm:table-cell">Team</th>
								<th class="px-2 py-2.5 font-medium text-center">G</th>
								<th class="px-2 py-2.5 font-medium text-center">AB</th>
								<th class="px-2 py-2.5 font-medium text-center">AVG</th>
								<th class="px-2 py-2.5 font-medium text-center">HR</th>
								<th class="px-2 py-2.5 font-medium text-center">RBI</th>
								<th class="px-2 py-2.5 font-medium text-center hidden sm:table-cell">OBP</th>
								<th class="px-2 py-2.5 font-medium text-center hidden sm:table-cell">SLG</th>
								<th class="px-3 py-2.5 font-medium text-center">OPS</th>
							</tr>
						{:else}
							<tr>
								<th class="text-left px-4 py-2.5 font-medium">Year</th>
								<th class="w-8 py-2.5"></th>
								<th class="px-2 py-2.5 font-medium text-center hidden sm:table-cell">Team</th>
								<th class="px-2 py-2.5 font-medium text-center">G</th>
								<th class="px-2 py-2.5 font-medium text-center">ERA</th>
								<th class="px-2 py-2.5 font-medium text-center">IP</th>
								<th class="px-2 py-2.5 font-medium text-center">W</th>
								<th class="px-2 py-2.5 font-medium text-center">L</th>
								<th class="px-2 py-2.5 font-medium text-center hidden sm:table-cell">SV</th>
								<th class="px-2 py-2.5 font-medium text-center hidden sm:table-cell">K</th>
								<th class="px-3 py-2.5 font-medium text-center hidden sm:table-cell">BB</th>
							</tr>
						{/if}
					</thead>
					<tbody>
						{#each allSeasons as row}
							<tr
								class="border-b border-border/50 last:border-0 hover:bg-surface-hover/50 transition-colors cursor-pointer
									{row.season === selectedSeason ? 'border-l-2 border-l-accent' : ''}"
								onclick={() => selectedSeason = row.season}
							>
							<td class="px-4 py-2.5 font-medium {row.season === selectedSeason ? 'text-accent' : 'text-white'}">{row.season}</td>
							<td class="w-8 py-2.5 pr-1"><Flag country={row.team_abbreviation} size="sm" /></td>
							<td class="px-2 py-2.5 text-center text-[#8888a0] hidden sm:table-cell">{row.team_abbreviation}</td>
								{#if !isPitcher}
									<td class="px-2 py-2.5 text-center text-[#8888a0] tabular-nums">{fmtNum(row.games_played)}</td>
									<td class="px-2 py-2.5 text-center text-[#8888a0] tabular-nums">{fmtNum(row.season_batting_ab)}</td>
									<td class="px-2 py-2.5 text-center font-mono text-[#f0f0f5] tabular-nums">{fmtAvg(row.season_batting_avg)}</td>
									<td class="px-2 py-2.5 text-center text-[#f0f0f5] tabular-nums">{fmtNum(row.season_batting_hr)}</td>
									<td class="px-2 py-2.5 text-center text-[#f0f0f5] tabular-nums">{fmtNum(row.season_batting_rbi)}</td>
									<td class="px-2 py-2.5 text-center font-mono text-[#8888a0] tabular-nums hidden sm:table-cell">{fmtAvg(row.season_batting_obp)}</td>
									<td class="px-2 py-2.5 text-center font-mono text-[#8888a0] tabular-nums hidden sm:table-cell">{fmtAvg(row.season_batting_slg)}</td>
									<td class="px-3 py-2.5 text-center font-mono text-[#f0f0f5] tabular-nums">{fmtAvg(row.season_batting_ops)}</td>
								{:else}
									<td class="px-2 py-2.5 text-center text-[#8888a0] tabular-nums">{fmtNum(row.games_played)}</td>
									<td class="px-2 py-2.5 text-center font-mono text-[#f0f0f5] tabular-nums">{fmtNum(row.season_pitching_era)}</td>
									<td class="px-2 py-2.5 text-center font-mono text-[#f0f0f5] tabular-nums">{fmtIp(row.season_pitching_ip)}</td>
									<td class="px-2 py-2.5 text-center text-[#f0f0f5] tabular-nums">{fmtNum(row.season_pitching_w)}</td>
									<td class="px-2 py-2.5 text-center text-[#8888a0] tabular-nums">{fmtNum(row.season_pitching_l)}</td>
									<td class="px-2 py-2.5 text-center text-[#8888a0] tabular-nums hidden sm:table-cell">{fmtNum(row.season_pitching_sv)}</td>
									<td class="px-2 py-2.5 text-center text-[#f0f0f5] tabular-nums hidden sm:table-cell">{fmtNum(row.season_pitching_so)}</td>
									<td class="px-3 py-2.5 text-center text-[#8888a0] tabular-nums hidden sm:table-cell">{fmtNum(row.season_pitching_bb)}</td>
								{/if}
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		</div>
	</section>

	<!-- Game log -->
	<section>
		<div class="flex items-center gap-3 mb-4">
			<h2 class="text-sm font-semibold uppercase tracking-widest text-[#8888a0]">Game Log</h2>
			<div class="flex gap-1">
				{#each seasons as s}
					<button
						type="button"
						onclick={() => selectedSeason = s}
						class="px-2.5 py-0.5 rounded-full text-xs font-medium transition-colors
							{selectedSeason === s ? 'bg-accent text-white' : 'bg-surface-hover text-[#8888a0] hover:text-white'}"
					>{s}</button>
				{/each}
			</div>
		</div>

		<div class="bg-surface border border-border rounded-xl overflow-hidden">
			<div class="overflow-x-auto">
				<table class="w-full text-sm">
					<thead class="text-xs text-[#8888a0] border-b border-border bg-surface-hover/50">
						{#if !isPitcher}
							<tr>
								<th class="text-left px-4 py-2.5 font-medium">Date</th>
								<th class="text-left px-2 py-2.5 font-medium hidden sm:table-cell">Round</th>
								<th class="text-left px-2 py-2.5 font-medium">Result</th>
								<th class="px-2 py-2.5 font-medium text-center">AB</th>
								<th class="px-2 py-2.5 font-medium text-center">H</th>
								<th class="px-2 py-2.5 font-medium text-center hidden sm:table-cell">HR</th>
								<th class="px-2 py-2.5 font-medium text-center hidden sm:table-cell">RBI</th>
								<th class="px-2 py-2.5 font-medium text-center hidden md:table-cell">BB</th>
								<th class="px-3 py-2.5 font-medium text-center hidden md:table-cell">SO</th>
							</tr>
						{:else}
							<tr>
								<th class="text-left px-4 py-2.5 font-medium">Date</th>
								<th class="text-left px-2 py-2.5 font-medium hidden sm:table-cell">Round</th>
								<th class="text-left px-2 py-2.5 font-medium">Result</th>
								<th class="px-2 py-2.5 font-medium text-center">IP</th>
								<th class="px-2 py-2.5 font-medium text-center">ER</th>
								<th class="px-2 py-2.5 font-medium text-center hidden sm:table-cell">K</th>
								<th class="px-2 py-2.5 font-medium text-center hidden sm:table-cell">BB</th>
								<th class="px-2 py-2.5 font-medium text-center hidden md:table-cell">H</th>
								<th class="px-3 py-2.5 font-medium text-center hidden md:table-cell">Dec</th>
							</tr>
						{/if}
					</thead>
					<tbody>
						{#each visibleLogs as log, i (log.game_pk + '_' + i)}
							<tr class="border-b border-border/50 last:border-0 hover:bg-surface-hover/50 transition-colors">
								{#if !isPitcher}
									<td class="px-4 py-2 text-[#8888a0] whitespace-nowrap">{log.official_date}</td>
									<td class="px-2 py-2 text-[#555570] text-xs hidden sm:table-cell">{log._gr?.round_label ?? '—'}</td>
									<td class="px-2 py-2 text-xs {resultColor(log)} whitespace-nowrap">{gameResult(log)}</td>
									<td class="px-2 py-2 text-center text-[#8888a0] tabular-nums">{fmtNum(log.batting_ab)}</td>
									<td class="px-2 py-2 text-center text-[#f0f0f5] tabular-nums">{fmtNum(log.batting_h)}</td>
									<td class="px-2 py-2 text-center text-[#f0f0f5] tabular-nums hidden sm:table-cell">{fmtNum(log.batting_hr)}</td>
									<td class="px-2 py-2 text-center text-[#f0f0f5] tabular-nums hidden sm:table-cell">{fmtNum(log.batting_rbi)}</td>
									<td class="px-2 py-2 text-center text-[#8888a0] tabular-nums hidden md:table-cell">{fmtNum(log.batting_bb)}</td>
									<td class="px-3 py-2 text-center text-[#8888a0] tabular-nums hidden md:table-cell">{fmtNum(log.batting_so)}</td>
								{:else}
									<td class="px-4 py-2 text-[#8888a0] whitespace-nowrap">{log.official_date}</td>
									<td class="px-2 py-2 text-[#555570] text-xs hidden sm:table-cell">{log._gr?.round_label ?? '—'}</td>
									<td class="px-2 py-2 text-xs {resultColor(log)} whitespace-nowrap">{gameResult(log)}</td>
									<td class="px-2 py-2 text-center font-mono text-[#f0f0f5] tabular-nums">{fmtIp(log.pitching_ip)}</td>
									<td class="px-2 py-2 text-center text-[#8888a0] tabular-nums">{fmtNum(log.pitching_er)}</td>
									<td class="px-2 py-2 text-center text-[#f0f0f5] tabular-nums hidden sm:table-cell">{fmtNum(log.pitching_so)}</td>
									<td class="px-2 py-2 text-center text-[#8888a0] tabular-nums hidden sm:table-cell">{fmtNum(log.pitching_bb)}</td>
									<td class="px-2 py-2 text-center text-[#8888a0] tabular-nums hidden md:table-cell">{fmtNum(log.pitching_h)}</td>
									<td class="px-3 py-2 text-center text-xs hidden md:table-cell">
										{#if log.pitching_w}<span class="text-success font-medium">W</span>
										{:else if log.pitching_l}<span class="text-danger font-medium">L</span>
										{:else if log.pitching_sv}<span class="text-accent font-medium">SV</span>
										{:else}<span class="text-[#555570]">—</span>{/if}
									</td>
								{/if}
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		</div>

		{#if seasonLogs.length === 0}
			<p class="text-[#8888a0] text-sm mt-3">No game log data for {selectedSeason}.</p>
		{/if}

		{#if visibleLogCount < seasonLogs.length}
			<div bind:this={logSentinelRef} class="mt-4 flex justify-center">
				<LoadingSpinner />
			</div>
		{/if}
	</section>
</div>