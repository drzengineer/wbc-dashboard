<script lang="ts">
	import { Activity, Flame, Rocket, Zap } from "lucide-svelte";
	import type { SeasonTeamTotal } from "$lib/types";

	type Props = {
		oneRunGames: number;
		oneRunPercentage: number;
		mercyRulesCount: number;
		mercyRulePercentage: number;
		bestRunDiff: SeasonTeamTotal | null;
		topScoringTeam: SeasonTeamTotal | null;
	};

	let {
		oneRunGames,
		oneRunPercentage,
		mercyRulesCount,
		mercyRulePercentage,
		bestRunDiff,
		topScoringTeam
	}: Props = $props();
</script>

<div class="grid grid-cols-2 md:grid-cols-4 gap-4 max-w-4xl mx-auto">
	<div class="bg-surface border border-border rounded-xl px-5 py-5 flex flex-col items-center justify-center relative overflow-hidden">
		<Activity class="w-4 h-4 text-red-400 absolute top-4 right-4 opacity-50" />
		<span class="text-xs text-[#8888a0] font-medium mb-1 uppercase tracking-wider">1-Run Games</span>
		<span class="text-3xl font-bold text-red-400">{oneRunGames}</span>
		<span class="text-xs text-red-400 mt-2 bg-red-400/10 px-2 py-0.5 rounded-full font-bold tracking-wide">{oneRunPercentage}% of games</span>
	</div>

	<div class="bg-surface border border-border rounded-xl px-5 py-5 flex flex-col items-center justify-center relative overflow-hidden">
		<Flame class="w-4 h-4 text-green-400 absolute top-4 right-4 opacity-50" />
		<span class="text-xs text-[#8888a0] font-medium mb-1 uppercase tracking-wider">Best Run Diff</span>
		<span class="text-3xl font-bold text-green-400">{bestRunDiff ? `+${bestRunDiff.total_run_differential}` : '+0'}</span>
		<span class="text-xs text-green-400 mt-2 bg-green-400/10 px-2 py-0.5 rounded-full font-bold tracking-wide">
			{bestRunDiff ? bestRunDiff.team_abbreviation : 'N/A'}
		</span>
	</div>

	<div class="bg-surface border border-border rounded-xl px-5 py-5 flex flex-col items-center justify-center relative overflow-hidden">
		<Rocket class="w-4 h-4 text-blue-400 absolute top-4 right-4 opacity-50" />
		<span class="text-xs text-[#8888a0] font-medium mb-1 uppercase tracking-wider">Top Scoring Team</span>
		<span class="text-3xl font-bold text-blue-400">{topScoringTeam?.total_runs_scored || 0}</span>
		<span class="text-xs text-blue-400 mt-2 bg-blue-400/10 px-2 py-0.5 rounded-full font-bold tracking-wide">
			{topScoringTeam ? topScoringTeam.team_abbreviation : 'N/A'}
		</span>
	</div>

	<div class="bg-surface border border-border rounded-xl px-5 py-5 flex flex-col items-center justify-center relative overflow-hidden">
		<Zap class="w-4 h-4 text-orange-400 absolute top-4 right-4 opacity-50" />
		<span class="text-xs text-[#8888a0] font-medium mb-1 uppercase tracking-wider">Mercy Rules</span>
		<span class="text-3xl font-bold text-orange-400">{mercyRulesCount}</span>
		<span class="text-xs text-orange-400 mt-2 bg-orange-400/10 px-2 py-0.5 rounded-full font-bold tracking-wide">{mercyRulePercentage}% of games</span>
	</div>
</div>