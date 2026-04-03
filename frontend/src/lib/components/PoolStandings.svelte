<script lang="ts">
	import Flag from "$lib/components/Flag.svelte";
	import { pct } from "$lib/utils";

	const { poolName, teams }: { poolName: string; teams: any[] } = $props();
</script>

<div class="bg-surface border border-border rounded-xl overflow-hidden">
	<div class="px-4 py-3 border-b border-border flex items-center gap-2">
		<span class="text-sm font-semibold text-white">{poolName}</span>
		<span class="text-xs text-[#555570]">{teams.length} teams</span>
	</div>
	<div class="overflow-x-auto">
		<table class="w-full text-sm">
			<thead>
				<tr class="text-xs text-[#8888a0] uppercase tracking-wider border-b border-border">
					<th class="w-5 pl-4 py-2"></th>
					<th class="w-8 py-2"></th>
					<th class="py-2 text-left font-medium pr-2">Team</th>
					<th class="w-10 py-2 text-center font-medium">W</th>
					<th class="w-10 py-2 text-center font-medium">L</th>
					<th class="w-14 py-2 text-center font-medium">RS</th>
					<th class="w-14 py-2 text-center font-medium">RA</th>
					<th class="w-14 py-2 text-center font-medium">DIFF</th>
					<th class="w-14 pr-4 py-2 text-center font-medium">WIN%</th>
				</tr>
			</thead>
			<tbody>
				{#each teams as team, i}
					<tr class="border-b border-border/50 last:border-0 hover:bg-surface-hover/50 transition-colors">
						<td class="w-5 p-4 py-2.5">
							{#if i === 0}
								<span class="text-success text-xs leading-none">●</span>
							{:else if i === 1}
								<span class="text-success/50 text-xs leading-none">●</span>
							{/if}
						</td>
						<td class="">
							<Flag country={team.team_abbreviation} size="lg" />
						</td>
						<td class="py-2.5 px-3">
							<span class="font-semibold text-white whitespace-nowrap">{team.team_abbreviation}</span>
						</td>
						<td class="py-2.5 text-center tabular-nums text-[#f0f0f5]">{team.pool_wins}</td>
						<td class="py-2.5 text-center tabular-nums text-[#8888a0]">{team.pool_losses}</td>
						<td class="py-2.5 text-center tabular-nums text-[#f0f0f5]">{team.pool_runs_scored ?? '—'}</td>
						<td class="py-2.5 text-center tabular-nums text-[#8888a0]">{team.pool_runs_allowed ?? '—'}</td>
						<td class="py-2.5 text-center tabular-nums font-mono
							{Number(team.pool_run_differential) > 0 ? 'text-success' : Number(team.pool_run_differential) < 0 ? 'text-danger' : 'text-[#8888a0]'}">
							{Number(team.pool_run_differential) > 0 ? '+' : ''}{team.pool_run_differential ?? '—'}
						</td>
						<td class="py-2.5 text-center tabular-nums font-mono pr-4 text-[#f0f0f5]">
							{pct(team.pool_win_pct)}
						</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>
</div>