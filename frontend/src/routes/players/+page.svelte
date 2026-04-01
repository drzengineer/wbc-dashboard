<script lang="ts">
  import { onMount } from 'svelte';
  import { flagHtml } from '$lib/flags';

  const { data } = $props();

  type Tab = 'Batting' | 'Pitching';
  let activeTab = $state<Tab>('Batting');

  const batters  = $derived(data.batters as any[]);
  const pitchers = $derived(data.pitchers as any[]);

  const seasons = $derived(
    [...new Set([...batters, ...pitchers].map((p: any) => p.season))].sort((a, b) => b - a)
  );
  let selectedSeason = $state(seasons[0] ?? 2026);

  // ─── Batting sort ────────────────────────────────────────────────────────────
  type BatStat = 'games_played' | 'season_batting_ab' | 'season_batting_avg' | 'season_batting_hr' | 'season_batting_rbi' | 'season_batting_obp' |'season_batting_slg' | 'season_batting_ops' | 'season_batting_sb';
  let batSortKey = $state<BatStat>('season_batting_avg');

  // ─── Pitching sort ───────────────────────────────────────────────────────────
  type PitStat = 'games_played' | 'season_pitching_era' | 'season_pitching_ip' | 'season_pitching_so' | 'season_pitching_bb' | 'season_pitching_w' | 'season_pitching_l' | 'season_pitching_sv';
  let pitSortKey = $state<PitStat>('season_pitching_era');

  // ─── Team filter ──────────────────────────────────────────────────────────────
  let selectedTeams = $state<string[]>([]);
  let teamDropdownOpen = $state(false);

  const teams = $derived(
    [...new Set([...batters, ...pitchers]
      .filter((p: any) => p.season === selectedSeason)
      .map((p: any) => p.team_abbreviation)
    )].sort()
  );

  function toggleTeam(team: string) {
    if (selectedTeams.includes(team)) {
      selectedTeams = selectedTeams.filter(t => t !== team);
    } else {
      selectedTeams = [...selectedTeams, team];
    }
  }

  function clearTeams() {
    selectedTeams = [];
  }

  // All batting stats sort descending (higher = better)
  const sortedBatters = $derived(
    batters
      .filter((p: any) => p.season === selectedSeason)
      .filter((p: any) => p.season_batting_ab > 0)
      .filter((p: any) => selectedTeams.length === 0 || selectedTeams.includes(p.team_abbreviation))
      .sort((a: any, b: any) => Number(b[batSortKey]) - Number(a[batSortKey]))
  );

  // ERA, BB, L sort ascending (lower = better); all others descending
  const ascendingPitStats = new Set(['season_pitching_era', 'season_pitching_bb', 'season_pitching_l']);
  const sortedPitchers = $derived(
    pitchers
      .filter((p: any) => p.season === selectedSeason)
      .filter((p: any) => (p.season_pitching_ip ?? 0) > 0)
      .filter((p: any) => selectedTeams.length === 0 || selectedTeams.includes(p.team_abbreviation))
      .sort((a: any, b: any) => {
        const av = Number(a[pitSortKey]);
        const bv = Number(b[pitSortKey]);
        return ascendingPitStats.has(pitSortKey) ? av - bv : bv - av;
      })
  );

  // ─── Incremental rendering ───────────────────────────────────────────────────
  let visibleCount = $state(30);
  let sentinelRef = $state<HTMLElement | null>(null);

  onMount(() => {
    const io = new IntersectionObserver((entries) => {
      if (entries[0].isIntersecting) visibleCount += 30;
    }, { rootMargin: '200px' });
    if (sentinelRef) io.observe(sentinelRef);
    return () => io.disconnect();
  });

  $effect(() => {
    selectedSeason; activeTab; batSortKey; pitSortKey; selectedTeams;
    visibleCount = 30;
  });

  const displayRows = $derived(
    (activeTab === 'Batting' ? sortedBatters : sortedPitchers).slice(0, visibleCount)
  );
  const totalRows = $derived(
    (activeTab === 'Batting' ? sortedBatters : sortedPitchers).length
  );

  function fmtAvg(v: any) { return v ? String(v).replace(/^0/, '') : '—'; }
  function fmtNum(v: any) { return v != null ? v : '—'; }
  function fmtIp(v: any) {
    if (v == null) return '—';
    const full = Math.floor(Number(v));
    const frac = Math.round((Number(v) - full) * 3);
    return frac === 0 ? `${full}.0` : `${full}.${frac}`;
  }
</script>

<!-- Header + season tabs -->
<div class="space-y-8">

  <div>
    <h1 class="text-2xl font-bold text-white tracking-tight">Players</h1>
</div>

<style>
  .scrollbar-hide {
    -ms-overflow-style: none;
    scrollbar-width: none;
  }
  .scrollbar-hide::-webkit-scrollbar {
    display: none;
  }
</style>

<div class="mb-5 flex flex-wrap items-center gap-2">
      <div class="flex gap-1 bg-gray-900 border border-gray-800 rounded-lg p-1 w-fit">
    {#each seasons as season}
      <button
        type="button"
        onclick={() => selectedSeason = season}
        class="px-3 py-1 rounded-md text-sm font-medium transition-colors
          {selectedSeason === season ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-white hover:bg-gray-800'}"
      >
        {season}
      </button>
    {/each}
  </div>
</div>

<!-- Batting / Pitching toggle + Team filter -->
<div class="flex flex-wrap gap-3 mb-5 items-center">
  <div class="flex gap-1 bg-gray-800/50 rounded-lg p-1 w-fit">
    {#each (['Batting', 'Pitching'] as Tab[]) as tab}
      <button
      type="button"
        onclick={() => activeTab = tab}
        class="px-4 py-1.5 rounded-md text-sm font-medium transition-colors {activeTab === tab ? 'bg-blue-600 text-white shadow' : 'text-gray-400 hover:text-white'}"
      >{tab}</button>
    {/each}
  </div>
  <div class="relative">
    <button
      type="button"
      onclick={() => teamDropdownOpen = !teamDropdownOpen}
      class="bg-gray-800 border border-gray-700 text-gray-300 text-sm rounded-lg px-4 py-2 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 flex items-center gap-2 justify-between"
    >
      <span>
        {#if selectedTeams.length === 0}
          All Teams
        {:else if selectedTeams.length === 1}
          {selectedTeams[0]}
        {:else}
          {selectedTeams.length} Teams
        {/if}
      </span>
      <svg class="w-4 h-4 transition-transform {teamDropdownOpen ? 'rotate-180' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
      </svg>
    </button>
    {#if teamDropdownOpen}
      <div class="absolute z-50 mt-1 w-29 bg-gray-800 border border-gray-700 rounded-lg shadow-lg overflow-hidden">
        <div class="max-h-75 overflow-y-auto scrollbar-hide">
          <button
            type="button"
            onclick={() => clearTeams()}
            class="w-full px-4 py-2 text-left text-sm hover:bg-gray-700 transition-colors {selectedTeams.length === 0 ? 'text-blue-400' : 'text-gray-300'}"
          >
            All Teams
          </button>
          {#each teams as team}
            <button
              type="button"
              onclick={() => toggleTeam(team)}
              class="w-full px-4 py-2 text-left text-sm hover:bg-gray-700 transition-colors flex items-center gap-2 {selectedTeams.includes(team) ? 'text-blue-400' : 'text-gray-300'}"
            >
              <span class="w-4 h-4 border border-gray-600 rounded flex items-center justify-center {selectedTeams.includes(team) ? 'bg-blue-600 border-blue-600' : ''}">
                {#if selectedTeams.includes(team)}
                  <svg class="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7" />
                  </svg>
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
<div class="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
  <div class="overflow-x-auto">
    <table class="w-full text-sm table-fixed">
      <thead class="text-xs text-gray-500 border-b border-gray-800 bg-gray-800/40">
        {#if activeTab === 'Batting'}
          <tr>
            <th class="text-left px-4 py-3 font-medium" style="width: 5%">#</th>
            <th class="text-left px-2 py-3 font-medium" style="width: 20%">Player</th>
            <!-- Flag column: fixed narrow, no header text -->
            <th class="py-3" style="width: 5%"></th>
            <th class="px-2 py-3 font-medium text-center hidden sm:table-cell" style="width: 8%">Team</th>
            <th class="px-2 py-3 font-medium text-center hidden md:table-cell" style="width: 6%">
              <button type="button" onclick={() => batSortKey = 'games_played'} class="w-full block hover:text-white transition-colors {batSortKey === 'games_played' ? 'text-blue-400 font-semibold' : ''}">G</button>
            </th>
            <th class="px-2 py-3 font-medium text-center hidden md:table-cell" style="width: 6%">
              <button type="button" onclick={() => batSortKey = 'season_batting_ab'} class="w-full block hover:text-white transition-colors {batSortKey === 'season_batting_ab' ? 'text-blue-400 font-semibold' : ''}">AB</button>
            </th>
            <th class="px-2 py-3 font-medium text-center" style="width: 8%">
              <button type="button" onclick={() => batSortKey = 'season_batting_avg'} class="w-full block hover:text-white transition-colors {batSortKey === 'season_batting_avg' ? 'text-blue-400 font-semibold' : ''}">AVG</button>
            </th>
            <th class="px-2 py-3 font-medium text-center hidden sm:table-cell" style="width: 6%">
              <button type="button" onclick={() => batSortKey = 'season_batting_hr'} class="w-full block hover:text-white transition-colors {batSortKey === 'season_batting_hr' ? 'text-blue-400 font-semibold' : ''}">HR</button>
            </th>
            <th class="px-2 py-3 font-medium text-center hidden sm:table-cell" style="width: 6%">
              <button type="button" onclick={() => batSortKey = 'season_batting_rbi'} class="w-full block hover:text-white transition-colors {batSortKey === 'season_batting_rbi' ? 'text-blue-400 font-semibold' : ''}">RBI</button>
            </th>
            <th class="px-2 py-3 font-medium text-center hidden lg:table-cell" style="width: 7%">
              <button type="button" onclick={() => batSortKey = 'season_batting_obp'} class="w-full block hover:text-white transition-colors {batSortKey === 'season_batting_obp' ? 'text-blue-400 font-semibold' : ''}">OBP</button>
            </th>
            <th class="px-2 py-3 font-medium text-center hidden lg:table-cell" style="width: 7%">
              <button type="button" onclick={() => batSortKey = 'season_batting_slg'} class="w-full block hover:text-white transition-colors {batSortKey === 'season_batting_slg' ? 'text-blue-400 font-semibold' : ''}">SLG</button>
            </th>
            <th class="px-2 py-3 font-medium text-center" style="width: 8%">
              <button type="button" onclick={() => batSortKey = 'season_batting_ops'} class="w-full block hover:text-white transition-colors {batSortKey === 'season_batting_ops' ? 'text-blue-400 font-semibold' : ''}">OPS</button>
            </th>
            <th class="px-3 py-3 font-medium text-center hidden md:table-cell" style="width: 6%">
              <button type="button" onclick={() => batSortKey = 'season_batting_sb'} class="w-full block hover:text-white transition-colors {batSortKey === 'season_batting_sb' ? 'text-blue-400 font-semibold' : ''}">SB</button>
            </th>
          </tr>
        {:else}
          <tr>
            <th class="text-left px-4 py-3 font-medium" style="width: 5%">#</th>
            <th class="text-left px-2 py-3 font-medium" style="width: 20%">Player</th>
            <!-- Flag column: fixed narrow, no header text -->
            <th class="py-3" style="width: 5%"></th>
            <th class="px-2 py-3 font-medium text-center hidden sm:table-cell" style="width: 8%">Team</th>
            <th class="px-2 py-3 font-medium text-center hidden md:table-cell" style="width: 7%">
              <button type="button" onclick={() => pitSortKey = 'games_played'} class="w-full block hover:text-white transition-colors {pitSortKey === 'games_played' ? 'text-blue-400 font-semibold' : ''}">G</button>
            </th>
            <th class="px-2 py-3 font-medium text-center" style="width: 10%">
              <button type="button" onclick={() => pitSortKey = 'season_pitching_era'} class="w-full block hover:text-white transition-colors {pitSortKey === 'season_pitching_era' ? 'text-blue-400 font-semibold' : ''}">ERA</button>
            </th>
            <th class="px-2 py-3 font-medium text-center" style="width: 10%">
              <button type="button" onclick={() => pitSortKey = 'season_pitching_ip'} class="w-full block hover:text-white transition-colors {pitSortKey === 'season_pitching_ip' ? 'text-blue-400 font-semibold' : ''}">IP</button>
            </th>
            <th class="px-2 py-3 font-medium text-center hidden sm:table-cell" style="width: 7%">
              <button type="button" onclick={() => pitSortKey = 'season_pitching_so'} class="w-full block hover:text-white transition-colors {pitSortKey === 'season_pitching_so' ? 'text-blue-400 font-semibold' : ''}">K</button>
            </th>
            <th class="px-2 py-3 font-medium text-center hidden sm:table-cell" style="width: 7%">
              <button type="button" onclick={() => pitSortKey = 'season_pitching_bb'} class="w-full block hover:text-white transition-colors {pitSortKey === 'season_pitching_bb' ? 'text-blue-400 font-semibold' : ''}">BB</button>
            </th>
            <th class="px-2 py-3 font-medium text-center hidden md:table-cell" style="width: 7%">
              <button type="button" onclick={() => pitSortKey = 'season_pitching_w'} class="w-full block hover:text-white transition-colors {pitSortKey === 'season_pitching_w' ? 'text-blue-400 font-semibold' : ''}">W</button>
            </th>
            <th class="px-2 py-3 font-medium text-center hidden md:table-cell" style="width: 7%">
              <button type="button" onclick={() => pitSortKey = 'season_pitching_l'} class="w-full block hover:text-white transition-colors {pitSortKey === 'season_pitching_l' ? 'text-blue-400 font-semibold' : ''}">L</button>
            </th>
            <th class="px-3 py-3 font-medium text-center hidden lg:table-cell" style="width: 7%">
              <button type="button" onclick={() => pitSortKey = 'season_pitching_sv'} class="w-full block hover:text-white transition-colors {pitSortKey === 'season_pitching_sv' ? 'text-blue-400 font-semibold' : ''}">SV</button>
            </th>
          </tr>
        {/if}
      </thead>
      <tbody>
        {#each displayRows as row, i (row.person_id + '_' + row.season)}
          <tr class="border-b border-gray-800/50 last:border-0 hover:bg-gray-800/30 transition-colors">
            {#if activeTab === 'Batting'}
              <td class="px-4 py-2.5 text-gray-600 text-xs">{i + 1}</td>
              <td class="px-2 py-2.5">
                <a href="/players/{row.person_id}" class="font-medium text-white hover:text-blue-400 transition-colors">{row.full_name}</a>
              </td>
              <!-- Flag -->
              <td class="w-8 py-2.5 pr-1">
                <span class="inline-block">{@html flagHtml(row.team_abbreviation)}</span>
              </td>
              <td class="px-2 py-2.5 text-center text-gray-400 hidden sm:table-cell">{row.team_abbreviation}</td>
              <td class="px-2 py-2.5 text-center {batSortKey === 'games_played' ? 'text-blue-400 font-semibold' : 'text-gray-400'} hidden md:table-cell">{fmtNum(row.games_played)}</td>
              <td class="px-2 py-2.5 text-center {batSortKey === 'season_batting_ab' ? 'text-blue-400 font-semibold' : 'text-gray-400'} hidden md:table-cell">{fmtNum(row.season_batting_ab)}</td>
              <td class="px-2 py-2.5 text-center font-mono {batSortKey === 'season_batting_avg' ? 'text-blue-400 font-semibold' : 'text-gray-300'}">{fmtAvg(row.season_batting_avg)}</td>
              <td class="px-2 py-2.5 text-center {batSortKey === 'season_batting_hr' ? 'text-blue-400 font-semibold' : 'text-gray-300'} hidden sm:table-cell">{fmtNum(row.season_batting_hr)}</td>
              <td class="px-2 py-2.5 text-center {batSortKey === 'season_batting_rbi' ? 'text-blue-400 font-semibold' : 'text-gray-300'} hidden sm:table-cell">{fmtNum(row.season_batting_rbi)}</td>
              <td class="px-2 py-2.5 text-center {batSortKey === 'season_batting_obp' ? 'text-blue-400 font-semibold' : 'text-gray-300'} hidden lg:table-cell">{fmtNum(row.season_batting_obp)}</td>
              <td class="px-2 py-2.5 text-center {batSortKey === 'season_batting_slg' ? 'text-blue-400 font-semibold' : 'text-gray-300'} hidden lg:table-cell">{fmtNum(row.season_batting_slg)}</td>
              <td class="px-2 py-2.5 text-center font-mono {batSortKey === 'season_batting_ops' ? 'text-blue-400 font-semibold' : 'text-gray-300'}">{fmtAvg(row.season_batting_ops)}</td>
              <td class="px-3 py-2.5 text-center {batSortKey === 'season_batting_sb' ? 'text-blue-400 font-semibold' : 'text-gray-300'} hidden md:table-cell">{fmtNum(row.season_batting_sb)}</td>
            {:else}
              <td class="px-4 py-2.5 text-gray-600 text-xs">{i + 1}</td>
              <td class="px-2 py-2.5">
                <a href="/players/{row.person_id}" class="font-medium text-white hover:text-blue-400 transition-colors">{row.full_name}</a>
              </td>
              <!-- Flag -->
              <td class="w-8 py-2.5 pr-1">
                <span class="inline-block">{@html flagHtml(row.team_abbreviation)}</span>
              </td>
              <td class="px-2 py-2.5 text-center text-gray-400 hidden sm:table-cell">{row.team_abbreviation}</td>
              <td class="px-2 py-2.5 text-center {pitSortKey === 'games_played' ? 'text-blue-400 font-semibold' : 'text-gray-400'} hidden md:table-cell">{fmtNum(row.games_played)}</td>
              <td class="px-2 py-2.5 text-center font-mono {pitSortKey === 'season_pitching_era' ? 'text-blue-400 font-semibold' : 'text-gray-300'}">{fmtNum(row.season_pitching_era)}</td>
              <td class="px-2 py-2.5 text-center font-mono {pitSortKey === 'season_pitching_ip' ? 'text-blue-400 font-semibold' : 'text-gray-300'}">{fmtIp(row.season_pitching_ip)}</td>
              <td class="px-2 py-2.5 text-center {pitSortKey === 'season_pitching_so' ? 'text-blue-400 font-semibold' : 'text-gray-300'} hidden sm:table-cell">{fmtNum(row.season_pitching_so)}</td>
              <td class="px-2 py-2.5 text-center {pitSortKey === 'season_pitching_bb' ? 'text-blue-400 font-semibold' : 'text-gray-400'} hidden sm:table-cell">{fmtNum(row.season_pitching_bb)}</td>
              <td class="px-2 py-2.5 text-center {pitSortKey === 'season_pitching_w' ? 'text-blue-400 font-semibold' : 'text-gray-300'} hidden md:table-cell">{fmtNum(row.season_pitching_w)}</td>
              <td class="px-2 py-2.5 text-center {pitSortKey === 'season_pitching_l' ? 'text-blue-400 font-semibold' : 'text-gray-400'} hidden md:table-cell">{fmtNum(row.season_pitching_l)}</td>
              <td class="px-3 py-2.5 text-center {pitSortKey === 'season_pitching_sv' ? 'text-blue-400 font-semibold' : 'text-gray-300'} hidden lg:table-cell">{fmtNum(row.season_pitching_sv)}</td>
            {/if}
          </tr>
        {/each}
      </tbody>
    </table>
  </div>
</div>

<!-- Count -->
<p class="text-xs text-gray-600 mt-2">Showing {Math.min(visibleCount, totalRows)} of {totalRows} players</p>

<!-- Infinite scroll sentinel -->
{#if visibleCount < totalRows}
  <div bind:this={sentinelRef} class="mt-4 flex justify-center">
    <div class="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
  </div>
{/if}
</div>