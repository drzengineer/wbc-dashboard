<script lang="ts">
import { ArrowLeft, Zap, Shield, Target, Trophy, Activity, Star } from "lucide-svelte";
import { onMount } from "svelte";
import Flag from "$lib/components/Flag.svelte";
import GaugeRing from "$lib/components/GaugeRing.svelte";
import LoadingSpinner from "$lib/components/LoadingSpinner.svelte";
import RadarChart from "$lib/components/RadarChart.svelte";
import { age, fmtAvg, fmtIp, fmtNum } from "$lib/utils";
import type { PageData } from "./$types";

const { data }: { data: PageData } = $props();

const player = $derived(data.player as any);
const allSeasons = $derived((data.tournamentStats as any[]) ?? []);
const allGameLogs = $derived((data.gameLogs as any[]) ?? []);
const maxStatsBySeason = $derived((data as any).maxStatsBySeason ?? {});
const isPitcher = $derived(player?.position_type === "Pitcher");

const seasons = $derived(
	[...new Set(allSeasons.map((s: any) => s.season))].sort(
		(a, b) => Number(b) - Number(a),
	),
);

let selectedSeason = $state<number>(0);

$effect(() => {
	if (selectedSeason === 0 && seasons.length > 0) {
		selectedSeason = seasons[0];
	}
});

const currentMaxStats = $derived(maxStatsBySeason[selectedSeason] ?? { batting: {}, pitching: {} });
const seasonRow = $derived(
	allSeasons.find((s: any) => s.season === selectedSeason) ?? allSeasons[0],
);

// Game log logic
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
const careerBatting = $derived((isPitcher || !hasMultipleSeasons) ? null : (data.careerBatting as any));
const careerPitching = $derived((!isPitcher || !hasMultipleSeasons) ? null : (data.careerPitching as any));

/**
 * RADAR CHART LOGIC
 * Solves NaN/Zero-Div issues and optimizes for WBC sample sizes
 */
const radarStats = $derived.by(() => {
	if (!seasonRow) return [];

	const n = (v: any) => (isFinite(Number(v)) ? Number(v) : 0);
	const pct = (v: any) => (isFinite(parseFloat(v)) ? parseFloat(v) : 0);
	const safe = (val: number) => Math.min(Math.max(val, 25), 100);

	// Normalization with division-by-zero protection and a power curve for distinct visuals
	const normalize = (val: number, maxVal: number, invert = false) => {
		const m = Math.max(maxVal, 0.0001) * 0.85; // 90% of season max becomes 100% on radar to stretch values
		const v = n(val);
		let ratio = v / m;
		if (invert) ratio = Math.max(0, 1 - ratio);
		// Power curve (0.55) makes the differences 
		// more "visible" for small tournament sample sizes
		return Math.max(15, Math.pow(Math.min(ratio, 1.0), 0.55) * 100);
	};

	if (isPitcher) {
		const pm = currentMaxStats.pitching || {};

		const bf = n(seasonRow.season_pitching_bf);
		const so = n(seasonRow.season_pitching_so);
		const bb = n(seasonRow.season_pitching_bb);
		const era = n(seasonRow.season_pitching_era);
		const ip = n(seasonRow.season_pitching_ip);
		const w = n(seasonRow.season_pitching_w);
		const sv = n(seasonRow.season_pitching_sv);
		const g = n(seasonRow.games_played);

		const maxBf = Math.max(n(pm.season_pitching_bf), 1);
		const maxSoRate = n(pm.season_pitching_so) / maxBf;
		const maxBbRate = n(pm.season_pitching_bb) / maxBf;
		const maxEra = Math.max(n(pm.season_pitching_era), 4.5);
		const maxIp = Math.max(n(pm.season_pitching_ip), 1);
		const maxWins = Math.max(n(pm.season_pitching_w), 1);
		const maxSaves = Math.max(n(pm.season_pitching_sv), 1);
		const maxG = Math.max(n(pm.games_played), 1);

		const dominance = normalize(bf > 0 ? so / bf : 0, maxSoRate);
		const control = normalize(bf > 0 ? bb / bf : 0, maxBbRate, true);
		const durability = normalize(ip, maxIp);
		const sharpness = normalize(Math.min(era, 15), maxEra, true);
		const clutch = normalize(w + sv * 0.7, maxWins + maxSaves * 0.7);
		const stamina = normalize(g, maxG);

		return [
			{ label: "Dominance", value: safe(dominance), max: 100 },
			{ label: "Control", value: safe(control), max: 100 },
			{ label: "Durability", value: safe(durability), max: 100 },
			{ label: "Sharpness", value: safe(sharpness), max: 100 },
			{ label: "Clutch", value: safe(clutch), max: 100 },
			{ label: "Stamina", value: safe(stamina), max: 100 },
		];
	}

	// Batter Stats
	const bm = currentMaxStats.batting || {};
	const ab = n(seasonRow.season_batting_ab);
	const bb = n(seasonRow.season_batting_bb);
	const pa = Math.max(ab + bb, 1);

	const avg = pct(seasonRow.season_batting_avg);
	const slg = pct(seasonRow.season_batting_slg);
	const hr = n(seasonRow.season_batting_hr);
	const sb = n(seasonRow.season_batting_sb);
	const rbi = n(seasonRow.season_batting_rbi);
	const r = n(seasonRow.season_batting_r);
	const so = n(seasonRow.season_batting_so);
	const h = n(seasonRow.season_batting_h);

	const powerScore = (normalize(slg, n(bm.season_batting_slg)) * 0.6) + (normalize(hr, n(bm.season_batting_hr)) * 0.4);
	const contactScore = normalize(avg, n(bm.season_batting_avg));
	const patienceScore = (normalize(bb / pa, n(bm.season_batting_bb) / Math.max(n(bm.season_batting_ab), 1)) * 0.5) + (normalize(so / pa, 0.3, true) * 0.5);
	const speedScore = normalize(sb, Math.max(n(bm.season_batting_sb), 1));
	const productionScore = normalize(rbi + r, n(bm.season_batting_rbi) + n(bm.season_batting_r));
	const consistencyScore = normalize(h / pa, n(bm.season_batting_h) / Math.max(n(bm.season_batting_ab), 1));

	return [
		{ label: "Power", value: safe(powerScore), max: 100 },
		{ label: "Contact", value: safe(contactScore), max: 100 },
		{ label: "Patience", value: safe(patienceScore), max: 100 },
		{ label: "Speed", value: safe(speedScore), max: 100 },
		{ label: "Consistency", value: safe(consistencyScore), max: 100 },
		{ label: "Production", value: safe(productionScore), max: 100 },
	];
});

/**
 * PLAYER ATTRIBUTE LOGIC
 */
const playerAttribute = $derived.by(() => {
	if (!radarStats.length) return { label: "Unknown", color: "text-[#555570]", icon: Activity };
	
	const statsMap: Record<string, number> = {};
	radarStats.forEach(s => statsMap[s.label] = s.value);

	if (isPitcher) {
		if (statsMap["Dominance"] > 80 && statsMap["Sharpness"] > 80) return { label: "Strikeout Artist", color: "text-accent", icon: Zap };
		if (statsMap["Stamina"] > 80 && statsMap["Durability"] > 80) return { label: "Innings Eater", color: "text-success", icon: Shield };
		if (statsMap["Control"] > 80) return { label: "Command Specialist", color: "text-info", icon: Target };
		if (statsMap["Clutch"] > 80 && statsMap["Stamina"] < 60) return { label: "Clutch Closer", color: "text-warning", icon: Trophy };
		return { label: "Reliable Arm", color: "text-white", icon: Star };
	} else {
		if (statsMap["Power"] > 80) return { label: "Power Hitter", color: "text-danger", icon: Zap };
		if (statsMap["Speed"] > 80) return { label: "Speedster", color: "text-success", icon: Activity };
		if (statsMap["Contact"] > 80 && statsMap["Consistency"] > 80) return { label: "Contact Specialist", color: "text-info", icon: Target };
		if (statsMap["Patience"] > 80) return { label: "Plate Discipline", color: "text-warning", icon: Shield };
		if (statsMap["Production"] > 80) return { label: "Run Producer", color: "text-accent", icon: Trophy };
		return { label: "Versatile Hitter", color: "text-white", icon: Star };
	}
});

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
	return myScore > oppScore ? "text-success" : myScore < oppScore ? "text-danger" : "text-[#8888a0]";
}
</script>

<div class="grid grid-cols-1 md:grid-cols-12 gap-5 md:gap-6 animate-fade-in">
	
	<section class="col-span-1 md:col-span-12 lg:col-span-8 bg-surface border border-border rounded-2xl p-6 md:p-8 shadow-xl shadow-black/20 flex flex-col gap-8">
	
		<a href="/players" class="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-[0.2em] text-[#555570] hover:text-white transition-colors group w-max">
			<ArrowLeft class="w-3.5 h-3.5 group-hover:-translate-x-1 transition-transform" />
			Back to Players
		</a>

		<div class="flex flex-col items-center text-center gap-4">
			<h1 class="text-4xl md:text-6xl font-black text-white tracking-tighter leading-none">
				{player?.full_name}
			</h1>
			
			<div class="flex flex-wrap items-center justify-center gap-3 md:gap-4">
				{#if player?.jersey_number}
					<span class="text-2xl md:text-3xl font-black text-accent tabular-nums">#{player.jersey_number}</span>
					<span class="hidden md:block text-[#2e2e48] text-2xl">•</span>
				{/if}
				
				<span class="text-lg md:text-xl font-bold text-white uppercase tracking-wide">
					{player?.position_type}
				</span>
				
				<span class="hidden md:block text-[#2e2e48] text-2xl">•</span>
				
				<div class="flex items-center gap-2 bg-surface-hover px-3 py-1 rounded-full border border-border">
					<Flag country={player?.team_abbreviation} size="md" />
					<span class="text-sm font-black text-white">{player?.represented_country}</span>
				</div>
			</div>
		</div>

		<div class="h-px bg-linear-to-r from-transparent via-border to-transparent opacity-50"></div>

		<div class="grid grid-cols-2 md:grid-cols-4 gap-8">
			<div class="flex flex-col items-center text-center gap-1">
				<span class="text-[10px] font-black uppercase tracking-[0.2em] text-[#555570]">Height</span>
				<span class="text-2xl font-black text-white tabular-nums">{player?.height || '—'}</span>
			</div>
			<div class="flex flex-col items-center text-center gap-1">
				<span class="text-[10px] font-black uppercase tracking-[0.2em] text-[#555570]">Weight</span>
				<span class="text-2xl font-black text-white tabular-nums">{player?.weight || '—'}<span class="text-xs ml-1 text-[#555570]">LB</span></span>
			</div>
			<div class="flex flex-col items-center text-center gap-1">
				<span class="text-[10px] font-black uppercase tracking-[0.2em] text-[#555570]">Bats</span>
				<span class="text-2xl font-black text-white">{player?.bat_side || '—'}</span>
			</div>
			<div class="flex flex-col items-center text-center gap-1">
				<span class="text-[10px] font-black uppercase tracking-[0.2em] text-[#555570]">Throws</span>
				<span class="text-2xl font-black text-white">{player?.pitch_hand || '—'}</span>
			</div>
		</div>

		<div class="h-px bg-linear-to-r from-transparent via-border to-transparent opacity-50"></div>

		<div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-8">
			<div class="flex flex-col items-center text-center gap-1">
				<span class="text-[10px] font-black uppercase tracking-[0.2em] text-[#555570]">Age</span>
				<span class="text-xl font-bold text-white tabular-nums">{player?.current_age || '—'}</span>
			</div>
			<div class="flex flex-col items-center text-center gap-1">
				<span class="text-[10px] font-black uppercase tracking-[0.2em] text-[#555570]">Birth Date</span>
				<span class="text-sm font-bold text-white">
					{player?.birth_date ? new Date(player.birth_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : '—'}
				</span>
			</div>
			<div class="flex flex-col items-center text-center gap-1">
				<span class="text-[10px] font-black uppercase tracking-[0.2em] text-[#555570]">Hometown</span>
				<span class="text-sm font-bold text-white leading-tight whitespace-normal wrap-break-word">
					{player?.birth_city}, {player?.birth_country}
				</span>
			</div>
			<div class="flex flex-col items-center text-center gap-1">
				<span class="text-[10px] font-black uppercase tracking-[0.2em] text-[#555570]">MLB Debut</span>
				<span class="text-sm font-bold text-white">
					{player?.mlb_debut_date ? new Date(player.mlb_debut_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : 'N/A'}
				</span>
			</div>
		</div>
	</section>

	<div class="col-span-1 md:col-span-12 lg:col-span-4 bg-surface border border-border rounded-2xl p-6 relative overflow-hidden group flex flex-col">
		<div class="absolute top-0 right-0 w-32 h-32 bg-accent/5 blur-3xl rounded-full -mr-16 -mt-16 group-hover:bg-accent/10 transition-colors"></div>
		
		<div class="flex items-start justify-between relative z-10 mb-2">
			<h2 class="text-xs font-black uppercase tracking-[0.2em] text-[#8888a0]">
				<span class="text-accent mr-1">{selectedSeason}</span> Profile
			</h2>
			
			<div class="inline-flex items-center gap-1 px-2 py-0.5 md:gap-1.5 md:px-3 md:py-1 rounded-full bg-surface-hover border border-border mb-2">
				{#if playerAttribute.icon === Zap}
				<Zap class="w-2.5 h-2.5 md:w-3 md:h-3 {playerAttribute.color}" />
				{:else if playerAttribute.icon === Shield}
				<Shield class="w-2.5 h-2.5 md:w-3 md:h-3 {playerAttribute.color}" />
				{:else if playerAttribute.icon === Target}
				<Target class="w-2.5 h-2.5 md:w-3 md:h-3 {playerAttribute.color}" />
				{:else if playerAttribute.icon === Trophy}
				<Trophy class="w-2.5 h-2.5 md:w-3 md:h-3 {playerAttribute.color}" />
				{:else if playerAttribute.icon === Activity}
				<Activity class="w-2.5 h-2.5 md:w-3 md:h-3 {playerAttribute.color}" />
				{:else}
				<Star class="w-2.5 h-2.5 md:w-3 md:h-3 {playerAttribute.color}" />
				{/if}
				<span class="text-[9px] md:text-[10px] font-black uppercase tracking-widest {playerAttribute.color}">
					{playerAttribute.label}
				</span>
			</div>
		</div>

		<div class="grow flex justify-center items-center">
			<RadarChart stats={radarStats} color={isPitcher ? '#a78bfa' : '#3b82f6'} size={310} />
		</div>
	</div>

	<div class="col-span-1 md:col-span-12 bg-surface border border-border rounded-2xl p-6 md:p-8 relative overflow-hidden group">
		<div class="absolute top-0 right-0 w-32 h-32 bg-success/5 blur-3xl rounded-full -mr-16 -mt-16 group-hover:bg-success/10 transition-colors"></div>
		<h2 class="text-xs font-black uppercase tracking-[0.2em] text-[#8888a0] mb-6 relative z-10">
			<span class="text-success mr-1">{selectedSeason}</span> Performance
		</h2>
		
		{#if seasonRow}
			<div class="flex flex-wrap justify-center gap-6 lg:gap-8 relative z-10">
				{#if !isPitcher}
					<GaugeRing
						value={parseFloat(seasonRow.season_batting_avg || '0')}
						max={parseFloat(currentMaxStats.batting.season_batting_avg || '1')}
						label="AVG" color="#3b82f6" size={100}
						formatValue={(v) => fmtAvg(v.toFixed(3))}
					/>
					<GaugeRing
						value={parseFloat(seasonRow.season_batting_obp || '0')}
						max={parseFloat(currentMaxStats.batting.season_batting_obp || '1')}
						label="OBP" color="#06b6d4" size={100}
						formatValue={(v) => fmtAvg(v.toFixed(3))}
					/>
					<GaugeRing
						value={parseFloat(seasonRow.season_batting_slg || '0')}
						max={parseFloat(currentMaxStats.batting.season_batting_slg || '1')}
						label="SLG" color="#84cc16" size={100}
						formatValue={(v) => fmtAvg(v.toFixed(3))}
					/>
					<GaugeRing
						value={parseFloat(seasonRow.season_batting_ops || '0')}
						max={parseFloat(currentMaxStats.batting.season_batting_ops || '1')}
						label="OPS" color="#22c55e" size={100}
						formatValue={(v) => fmtAvg(v.toFixed(3))}
					/>
					<GaugeRing
						value={Number(seasonRow.season_batting_h) || 0}
						max={Number(currentMaxStats.batting.season_batting_h) || 1}
						label="H" color="#14b8a6" size={100}
					/>
					<GaugeRing
						value={Number(seasonRow.season_batting_r) || 0}
						max={Number(currentMaxStats.batting.season_batting_r) || 1}
						label="R" color="#8b5cf6" size={100}
					/>
					<GaugeRing
						value={Number(seasonRow.season_batting_rbi) || 0}
						max={Number(currentMaxStats.batting.season_batting_rbi) || 1}
						label="RBI" color="#f97316" size={100}
					/>
					<GaugeRing
						value={Number(seasonRow.season_batting_hr) || 0}
						max={Number(currentMaxStats.batting.season_batting_hr) || 1}
						label="HR" color="#eab308" size={100}
					/>
					<GaugeRing
						value={Number(seasonRow.season_batting_bb) || 0}
						max={Number(currentMaxStats.batting.season_batting_bb) || 1}
						label="BB" color="#f43f5e" size={100}
					/>
					<GaugeRing
						value={Number(seasonRow.season_batting_so) || 0}
						max={Number(currentMaxStats.batting.season_batting_so) || 1}
						label="SO" color="#ef4444" size={100}
					/>
					<GaugeRing
						value={Number(seasonRow.season_batting_sb) || 0}
						max={Number(currentMaxStats.batting.season_batting_sb) || 1}
						label="SB" color="#ec4899" size={100}
					/>
				{:else}
					<GaugeRing
						value={10 - Math.min(Number(seasonRow.season_pitching_era) || 0, 10)}
						max={10} label="ERA" color="#a78bfa" size={100}
						formatValue={() => (Number(seasonRow.season_pitching_era) || 0).toFixed(2)}
					/>
					<GaugeRing
						value={Number(seasonRow.season_pitching_w) || 0}
						max={Number(currentMaxStats.pitching.season_pitching_w) || 1}
						label="W" color="#10b981" size={100}
					/>
					<GaugeRing
						value={Math.max(0, (Number(currentMaxStats.pitching.season_pitching_l) || 1) - Number(seasonRow.season_pitching_l || 0))}
						max={Number(currentMaxStats.pitching.season_pitching_l) || 1}
						label="L" color="#ef4444" size={100} formatValue={() => String(Number(seasonRow.season_pitching_l || 0))}
					/>
					<GaugeRing
						value={Number(seasonRow.season_pitching_sv) || 0}
						max={Number(currentMaxStats.pitching.season_pitching_sv) || 1}
						label="SV" color="#f59e0b" size={100}
					/>
					<GaugeRing
						value={Number(seasonRow.season_pitching_ip) || 0}
						max={Number(currentMaxStats.pitching.season_pitching_ip) || 1}
						label="IP" color="#3b82f6" size={100}
						formatValue={(v) => fmtIp(v)}
					/>
					<GaugeRing
						value={Math.max(0, (Number(currentMaxStats.pitching.season_pitching_h) || 1) - Number(seasonRow.season_pitching_h || 0))}
						max={Number(currentMaxStats.pitching.season_pitching_h) || 1}
						label="H" color="#f43f5e" size={100} formatValue={() => String(Number(seasonRow.season_pitching_h || 0))}
					/>
					<GaugeRing
						value={Math.max(0, (Number(currentMaxStats.pitching.season_pitching_bb) || 1) - Number(seasonRow.season_pitching_bb || 0))}
						max={Number(currentMaxStats.pitching.season_pitching_bb) || 1}
						label="BB" color="#f97316" size={100} formatValue={() => String(Number(seasonRow.season_pitching_bb || 0))}
					/>
					<GaugeRing
						value={Number(seasonRow.season_pitching_so) || 0}
						max={Number(currentMaxStats.pitching.season_pitching_so) || 1}
						label="K" color="#22c55e" size={100}
					/>
				{/if}
			</div>
		{/if}
	</div>

	{#if hasMultipleSeasons && (careerBatting || careerPitching)}
		<section class="col-span-1 md:col-span-12">
			<h2 class="text-xs font-bold uppercase tracking-widest text-[#8888a0] mb-3 ml-1">Career WBC Totals</h2>
			<div class="grid grid-cols-4 sm:grid-cols-8 gap-3">
				{#if careerBatting}
					{@const cb = careerBatting}
					{#each [
						{ label: 'G', value: cb.g }, { label: 'AB', value: cb.ab },
						{ label: 'H', value: cb.h }, { label: 'HR', value: cb.hr },
						{ label: 'RBI', value: cb.rbi }, { label: 'R', value: cb.r },
						{ label: 'BB', value: cb.bb }, { label: 'SB', value: cb.sb }
					] as stat}
						<div class="bg-surface border border-border rounded-xl p-3 flex flex-col items-center justify-center shadow-sm hover:border-border-light transition-colors group">
							<div class="text-[10px] uppercase font-bold text-[#555570] group-hover:text-[#8888a0] transition-colors">{stat.label}</div>
							<div class="text-xl font-black text-white tabular-nums mt-1">{stat.value}</div>
						</div>
					{/each}
				{/if}
				{#if careerPitching}
					{@const cp = careerPitching}
					{#each [
						{ label: 'ERA', value: cp.era ?? '—' }, { label: 'IP', value: fmtIp(cp.ip) },
						{ label: 'W', value: cp.w }, { label: 'L', value: cp.l },
						{ label: 'SV', value: cp.sv }, { label: 'K', value: cp.so },
						{ label: 'BB', value: cp.bb }
					] as stat}
						<div class="bg-surface border border-border rounded-xl p-3 flex flex-col items-center justify-center shadow-sm hover:border-border-light transition-colors group">
							<div class="text-[10px] uppercase font-bold text-[#555570] group-hover:text-[#8888a0] transition-colors">{stat.label}</div>
							<div class="text-xl font-black text-white tabular-nums mt-1">{stat.value}</div>
						</div>
					{/each}
				{/if}
			</div>
		</section>
	{/if}

	<section class="col-span-1 md:col-span-12">
		<h2 class="text-xs font-bold uppercase tracking-widest text-[#8888a0] mb-3 ml-1">By Season</h2>
		<div class="bg-surface border border-border rounded-2xl overflow-hidden shadow-sm">
			<div class="overflow-x-auto">
				<table class="w-full text-sm border-collapse">
					<thead class="text-[11px] uppercase tracking-wider text-[#8888a0] border-b border-border bg-surface-hover/30">
						{#if !isPitcher}
							<tr>
								<th class="text-left px-5 py-3.5 font-semibold w-24">Year</th>
								<th class="w-10 py-3.5"></th>
								<th class="text-left px-3 py-3.5 font-semibold w-24 hidden sm:table-cell">Team</th>
								<th class="px-3 py-3.5 font-semibold text-center">G</th>
								<th class="px-3 py-3.5 font-semibold text-center">AB</th>
								<th class="px-3 py-3.5 font-semibold text-center">AVG</th>
								<th class="px-3 py-3.5 font-semibold text-center">HR</th>
								<th class="px-3 py-3.5 font-semibold text-center">RBI</th>
								<th class="px-3 py-3.5 font-semibold text-center hidden sm:table-cell">OBP</th>
								<th class="px-3 py-3.5 font-semibold text-center hidden sm:table-cell">SLG</th>
								<th class="px-4 py-3.5 font-semibold text-center text-white">OPS</th>
							</tr>
						{:else}
							<tr>
								<th class="text-left px-5 py-3.5 font-semibold w-24">Year</th>
								<th class="w-10 py-3.5"></th>
								<th class="text-left px-3 py-3.5 font-semibold w-24 hidden sm:table-cell">Team</th>
								<th class="px-3 py-3.5 font-semibold text-center">G</th>
								<th class="px-3 py-3.5 font-semibold text-center">ERA</th>
								<th class="px-3 py-3.5 font-semibold text-center">IP</th>
								<th class="px-3 py-3.5 font-semibold text-center">W</th>
								<th class="px-3 py-3.5 font-semibold text-center">L</th>
								<th class="px-3 py-3.5 font-semibold text-center hidden sm:table-cell">SV</th>
								<th class="px-3 py-3.5 font-semibold text-center hidden sm:table-cell">K</th>
								<th class="px-4 py-3.5 font-semibold text-center hidden sm:table-cell">BB</th>
							</tr>
						{/if}
					</thead>
					<tbody class="divide-y divide-border/50">
						{#each allSeasons as row}
							<tr
								class="last:border-0 hover:bg-surface-hover/40 transition-colors cursor-pointer {row.season === selectedSeason ? 'bg-surface-hover/20' : ''}"
								onclick={() => selectedSeason = row.season}
							>
								<td class="px-5 py-3.5 font-bold relative {row.season === selectedSeason ? 'text-accent' : 'text-white'}">
									{#if row.season === selectedSeason}
										<div class="absolute left-0 top-0 bottom-0 w-1 bg-accent rounded-r-full"></div>
									{/if}
									{row.season}
								</td>
								<td class="w-10 py-3.5"><Flag country={row.team_abbreviation} size="sm" /></td>
								<td class="text-left px-3 py-3.5 text-[#8888a0] text-xs font-semibold hidden sm:table-cell">{row.team_abbreviation}</td>
								
								{#if !isPitcher}
									<td class="px-3 py-3.5 text-center text-[#8888a0] tabular-nums">{fmtNum(row.games_played)}</td>
									<td class="px-3 py-3.5 text-center text-[#8888a0] tabular-nums">{fmtNum(row.season_batting_ab)}</td>
									<td class="px-3 py-3.5 text-center font-mono font-medium text-white tabular-nums">{fmtAvg(row.season_batting_avg)}</td>
									<td class="px-3 py-3.5 text-center text-white tabular-nums">{fmtNum(row.season_batting_hr)}</td>
									<td class="px-3 py-3.5 text-center text-white tabular-nums">{fmtNum(row.season_batting_rbi)}</td>
									<td class="px-3 py-3.5 text-center font-mono text-[#8888a0] tabular-nums hidden sm:table-cell">{fmtAvg(row.season_batting_obp)}</td>
									<td class="px-3 py-3.5 text-center font-mono text-[#8888a0] tabular-nums hidden sm:table-cell">{fmtAvg(row.season_batting_slg)}</td>
									<td class="px-4 py-3.5 text-center font-mono font-bold text-accent-light tabular-nums">{fmtAvg(row.season_batting_ops)}</td>
								{:else}
									<td class="px-3 py-3.5 text-center text-[#8888a0] tabular-nums">{fmtNum(row.games_played)}</td>
									<td class="px-3 py-3.5 text-center font-mono font-medium text-white tabular-nums">{fmtNum(row.season_pitching_era)}</td>
									<td class="px-3 py-3.5 text-center font-mono text-white tabular-nums">{fmtIp(row.season_pitching_ip)}</td>
									<td class="px-3 py-3.5 text-center text-white tabular-nums">{fmtNum(row.season_pitching_w)}</td>
									<td class="px-3 py-3.5 text-center text-[#8888a0] tabular-nums">{fmtNum(row.season_pitching_l)}</td>
									<td class="px-3 py-3.5 text-center text-[#8888a0] tabular-nums hidden sm:table-cell">{fmtNum(row.season_pitching_sv)}</td>
									<td class="px-3 py-3.5 text-center font-medium text-white tabular-nums hidden sm:table-cell">{fmtNum(row.season_pitching_so)}</td>
									<td class="px-4 py-3.5 text-center text-[#8888a0] tabular-nums hidden sm:table-cell">{fmtNum(row.season_pitching_bb)}</td>
								{/if}
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		</div>
	</section>

	<section class="col-span-1 md:col-span-12">
		<div class="flex items-center justify-between mb-3 px-1">
			<h2 class="text-xs font-bold uppercase tracking-widest text-[#8888a0]">Game Log</h2>
			<div class="flex gap-1.5 p-1 bg-surface border border-border rounded-lg shadow-sm">
				{#each seasons as s}
					<button
						type="button"
						onclick={() => selectedSeason = s}
						class="px-3 py-1 rounded-md text-xs font-bold transition-all
							{selectedSeason === s ? 'bg-accent/20 text-accent border border-accent/30' : 'bg-transparent text-[#555570] hover:text-[#8888a0]'}"
					>{s}</button>
				{/each}
			</div>
		</div>

		<div class="bg-surface border border-border rounded-2xl overflow-hidden shadow-sm">
			<div class="overflow-x-auto">
				<table class="w-full text-sm">
					<thead class="text-[11px] uppercase tracking-wider text-[#8888a0] border-b border-border bg-surface-hover/30">
						{#if !isPitcher}
							<tr>
								<th class="text-left px-5 py-3 font-semibold">Date</th>
								<th class="text-left px-3 py-3 font-semibold hidden sm:table-cell">Round</th>
								<th class="text-left px-3 py-3 font-semibold">Result</th>
								<th class="px-3 py-3 font-semibold text-center">AB</th>
								<th class="px-3 py-3 font-semibold text-center">H</th>
								<th class="px-3 py-3 font-semibold text-center hidden sm:table-cell">HR</th>
								<th class="px-3 py-3 font-semibold text-center hidden sm:table-cell">RBI</th>
								<th class="px-3 py-3 font-semibold text-center hidden md:table-cell">BB</th>
								<th class="px-4 py-3 font-semibold text-center hidden md:table-cell">SO</th>
							</tr>
						{:else}
							<tr>
								<th class="text-left px-5 py-3 font-semibold">Date</th>
								<th class="text-left px-3 py-3 font-semibold hidden sm:table-cell">Round</th>
								<th class="text-left px-3 py-3 font-semibold">Result</th>
								<th class="px-3 py-3 font-semibold text-center">IP</th>
								<th class="px-3 py-3 font-semibold text-center">ER</th>
								<th class="px-3 py-3 font-semibold text-center hidden sm:table-cell">K</th>
								<th class="px-3 py-3 font-semibold text-center hidden sm:table-cell">BB</th>
								<th class="px-3 py-3 font-semibold text-center hidden md:table-cell">H</th>
								<th class="px-4 py-3 font-semibold text-center hidden md:table-cell">Dec</th>
							</tr>
						{/if}
					</thead>
					<tbody class="divide-y divide-border/50">
						{#each visibleLogs as log, i (log.game_pk + '_' + i)}
							<tr class="hover:bg-surface-hover/30 transition-colors">
								{#if !isPitcher}
									<td class="px-5 py-3 text-[#8888a0] text-xs whitespace-nowrap">{log.official_date}</td>
									<td class="px-3 py-3 text-[#555570] text-[11px] uppercase tracking-wide hidden sm:table-cell">{log._gr?.round_label ?? '—'}</td>
									<td class="px-3 py-3 text-xs font-semibold {resultColor(log)} whitespace-nowrap">{gameResult(log)}</td>
									<td class="px-3 py-3 text-center text-[#8888a0] tabular-nums">{fmtNum(log.batting_ab)}</td>
									<td class="px-3 py-3 text-center text-white tabular-nums font-medium">{fmtNum(log.batting_h)}</td>
									<td class="px-3 py-3 text-center text-white tabular-nums hidden sm:table-cell">{fmtNum(log.batting_hr)}</td>
									<td class="px-3 py-3 text-center text-white tabular-nums hidden sm:table-cell">{fmtNum(log.batting_rbi)}</td>
									<td class="px-3 py-3 text-center text-[#8888a0] tabular-nums hidden md:table-cell">{fmtNum(log.batting_bb)}</td>
									<td class="px-4 py-3 text-center text-[#8888a0] tabular-nums hidden md:table-cell">{fmtNum(log.batting_so)}</td>
								{:else}
									<td class="px-5 py-3 text-[#8888a0] text-xs whitespace-nowrap">{log.official_date}</td>
									<td class="px-3 py-3 text-[#555570] text-[11px] uppercase tracking-wide hidden sm:table-cell">{log._gr?.round_label ?? '—'}</td>
									<td class="px-3 py-3 text-xs font-semibold {resultColor(log)} whitespace-nowrap">{gameResult(log)}</td>
									<td class="px-3 py-3 text-center font-mono text-white tabular-nums">{fmtIp(log.pitching_ip)}</td>
									<td class="px-3 py-3 text-center text-[#8888a0] tabular-nums">{fmtNum(log.pitching_er)}</td>
									<td class="px-3 py-3 text-center text-white tabular-nums font-medium hidden sm:table-cell">{fmtNum(log.pitching_so)}</td>
									<td class="px-3 py-3 text-center text-[#8888a0] tabular-nums hidden sm:table-cell">{fmtNum(log.pitching_bb)}</td>
									<td class="px-3 py-3 text-center text-[#8888a0] tabular-nums hidden md:table-cell">{fmtNum(log.pitching_h)}</td>
									<td class="px-4 py-3 text-center text-[10px] uppercase font-black hidden md:table-cell">
										{#if log.pitching_w}<span class="text-success bg-success/10 px-2 py-0.5 rounded border border-success/20">W</span>
										{:else if log.pitching_l}<span class="text-danger bg-danger/10 px-2 py-0.5 rounded border border-danger/20">L</span>
										{:else if log.pitching_sv}<span class="text-accent bg-accent/10 px-2 py-0.5 rounded border border-accent/20">SV</span>
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
			<div class="text-center py-8 text-[#555570] text-sm bg-surface/50 border border-border/50 rounded-2xl mt-3">
				No game log data available for {selectedSeason}.
			</div>
		{/if}

		{#if visibleLogCount < seasonLogs.length}
			<div bind:this={logSentinelRef} class="mt-6 flex justify-center">
				<LoadingSpinner />
			</div>
		{/if}
	</section>
</div>