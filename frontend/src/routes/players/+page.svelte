<script lang="ts">
  import { onMount } from 'svelte';

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
  type BatStat = 'season_batting_avg' | 'season_batting_hr' | 'season_batting_rbi' | 'season_batting_ops' | 'season_batting_sb';
  const batStatLabels: Record<BatStat, string> = {
    season_batting_avg: 'AVG', season_batting_hr: 'HR', season_batting_rbi: 'RBI',
    season_batting_ops: 'OPS', season_batting_sb: 'SB',
  };
  let batSortKey = $state<BatStat>('season_batting_avg');

  // ─── Pitching sort ───────────────────────────────────────────────────────────
  type PitStat = 'season_pitching_era' | 'season_pitching_so' | 'season_pitching_ip' | 'season_pitching_w' | 'season_pitching_sv';
  const pitStatLabels: Record<PitStat, string> = {
    season_pitching_era: 'ERA', season_pitching_so: 'K', season_pitching_ip: 'IP',
    season_pitching_w: 'W', season_pitching_sv: 'SV',
  };
  let pitSortKey = $state<PitStat>('season_pitching_era');

  // ERA sorts ascending (lower = better); all others descending
  const sortedBatters = $derived(
    batters
      .filter((p: any) => p.season === selectedSeason)
      .filter((p: any) => p.season_batting_ab > 0)
      .sort((a: any, b: any) => Number(b[batSortKey]) - Number(a[batSortKey]))
  );

  const sortedPitchers = $derived(
    pitchers
      .filter((p: any) => p.season === selectedSeason)
      .filter((p: any) => (p.season_pitching_ip ?? 0) > 0)
      .sort((a: any, b: any) => {
        const av = Number(a[pitSortKey]);
        const bv = Number(b[pitSortKey]);
        return pitSortKey === 'season_pitching_era' ? av - bv : bv - av;
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
    selectedSeason; activeTab; batSortKey; pitSortKey;
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
<div class="mb-5 flex flex-wrap items-center gap-2">
  <h1 class="text-xl md:text-2xl font-bold mr-2">Players</h1>
  {#each seasons as s}
    <button
      onclick={() => { selectedSeason = s; }}
      class="px-3 py-1 rounded-full text-xs font-semibold transition-colors {selectedSeason === s ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-400 hover:text-white'}"
    >{s}</button>
  {/each}
</div>

<!-- Batting / Pitching toggle -->
<div class="flex gap-1 mb-5 bg-gray-800/50 rounded-lg p-1 w-fit">
  {#each (['Batting', 'Pitching'] as Tab[]) as tab}
    <button
      onclick={() => activeTab = tab}
      class="px-4 py-1.5 rounded-md text-sm font-medium transition-colors {activeTab === tab ? 'bg-blue-600 text-white shadow' : 'text-gray-400 hover:text-white'}"
    >{tab}</button>
  {/each}
</div>

<!-- Stat sort pills -->
<div class="flex flex-wrap gap-2 mb-4">
  {#if activeTab === 'Batting'}
    {#each Object.entries(batStatLabels) as [key, label]}
      <button
        onclick={() => batSortKey = key as BatStat}
        class="px-3 py-1 rounded-full text-xs font-semibold transition-colors {batSortKey === key ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-400 hover:text-white'}"
      >{label}</button>
    {/each}
  {:else}
    {#each Object.entries(pitStatLabels) as [key, label]}
      <button
        onclick={() => pitSortKey = key as PitStat}
        class="px-3 py-1 rounded-full text-xs font-semibold transition-colors {pitSortKey === key ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-400 hover:text-white'}"
      >{label}</button>
    {/each}
  {/if}
</div>

<!-- Leaderboard table — responsive wrapper -->
<div class="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
  <div class="overflow-x-auto">
    <table class="w-full text-sm">
      <thead class="text-xs text-gray-500 border-b border-gray-800 bg-gray-800/40">
        {#if activeTab === 'Batting'}
          <tr>
            <th class="text-left px-4 py-3 font-medium w-8">#</th>
            <th class="text-left px-2 py-3 font-medium">Player</th>
            <th class="px-2 py-3 font-medium text-center hidden sm:table-cell">Team</th>
            <th class="px-2 py-3 font-medium text-center hidden md:table-cell">G</th>
            <th class="px-2 py-3 font-medium text-center hidden md:table-cell">AB</th>
            <th class="px-2 py-3 font-medium text-center">AVG</th>
            <th class="px-2 py-3 font-medium text-center hidden sm:table-cell">HR</th>
            <th class="px-2 py-3 font-medium text-center hidden sm:table-cell">RBI</th>
            <th class="px-2 py-3 font-medium text-center hidden lg:table-cell">OBP</th>
            <th class="px-2 py-3 font-medium text-center hidden lg:table-cell">SLG</th>
            <th class="px-2 py-3 font-medium text-center">OPS</th>
            <th class="px-3 py-3 font-medium text-center hidden md:table-cell">SB</th>
          </tr>
        {:else}
          <tr>
            <th class="text-left px-4 py-3 font-medium w-8">#</th>
            <th class="text-left px-2 py-3 font-medium">Player</th>
            <th class="px-2 py-3 font-medium text-center hidden sm:table-cell">Team</th>
            <th class="px-2 py-3 font-medium text-center hidden md:table-cell">G</th>
            <th class="px-2 py-3 font-medium text-center">ERA</th>
            <th class="px-2 py-3 font-medium text-center">IP</th>
            <th class="px-2 py-3 font-medium text-center hidden sm:table-cell">K</th>
            <th class="px-2 py-3 font-medium text-center hidden sm:table-cell">BB</th>
            <th class="px-2 py-3 font-medium text-center hidden md:table-cell">W</th>
            <th class="px-2 py-3 font-medium text-center hidden md:table-cell">L</th>
            <th class="px-3 py-3 font-medium text-center hidden lg:table-cell">SV</th>
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
              <td class="px-2 py-2.5 text-center text-gray-400 hidden sm:table-cell">{row.team_abbreviation}</td>
              <td class="px-2 py-2.5 text-center text-gray-400 hidden md:table-cell">{fmtNum(row.games_played)}</td>
              <td class="px-2 py-2.5 text-center text-gray-400 hidden md:table-cell">{fmtNum(row.season_batting_ab)}</td>
              <td class="px-2 py-2.5 text-center font-mono {batSortKey === 'season_batting_avg' ? 'text-blue-400 font-semibold' : 'text-gray-300'}">{fmtAvg(row.season_batting_avg)}</td>
              <td class="px-2 py-2.5 text-center {batSortKey === 'season_batting_hr' ? 'text-blue-400 font-semibold' : 'text-gray-300'} hidden sm:table-cell">{fmtNum(row.season_batting_hr)}</td>
              <td class="px-2 py-2.5 text-center {batSortKey === 'season_batting_rbi' ? 'text-blue-400 font-semibold' : 'text-gray-300'} hidden sm:table-cell">{fmtNum(row.season_batting_rbi)}</td>
              <td class="px-2 py-2.5 text-center font-mono text-gray-400 hidden lg:table-cell">{fmtAvg(row.season_batting_obp)}</td>
              <td class="px-2 py-2.5 text-center font-mono text-gray-400 hidden lg:table-cell">{fmtAvg(row.season_batting_slg)}</td>
              <td class="px-2 py-2.5 text-center font-mono {batSortKey === 'season_batting_ops' ? 'text-blue-400 font-semibold' : 'text-gray-300'}">{fmtAvg(row.season_batting_ops)}</td>
              <td class="px-3 py-2.5 text-center {batSortKey === 'season_batting_sb' ? 'text-blue-400 font-semibold' : 'text-gray-300'} hidden md:table-cell">{fmtNum(row.season_batting_sb)}</td>
            {:else}
              <td class="px-4 py-2.5 text-gray-600 text-xs">{i + 1}</td>
              <td class="px-2 py-2.5">
                <a href="/players/{row.person_id}" class="font-medium text-white hover:text-blue-400 transition-colors">{row.full_name}</a>
              </td>
              <td class="px-2 py-2.5 text-center text-gray-400 hidden sm:table-cell">{row.team_abbreviation}</td>
              <td class="px-2 py-2.5 text-center text-gray-400 hidden md:table-cell">{fmtNum(row.games_played)}</td>
              <td class="px-2 py-2.5 text-center font-mono {pitSortKey === 'season_pitching_era' ? 'text-blue-400 font-semibold' : 'text-gray-300'}">{fmtNum(row.season_pitching_era)}</td>
              <td class="px-2 py-2.5 text-center font-mono {pitSortKey === 'season_pitching_ip' ? 'text-blue-400 font-semibold' : 'text-gray-300'}">{fmtIp(row.season_pitching_ip)}</td>
              <td class="px-2 py-2.5 text-center {pitSortKey === 'season_pitching_so' ? 'text-blue-400 font-semibold' : 'text-gray-300'} hidden sm:table-cell">{fmtNum(row.season_pitching_so)}</td>
              <td class="px-2 py-2.5 text-center text-gray-400 hidden sm:table-cell">{fmtNum(row.season_pitching_bb)}</td>
              <td class="px-2 py-2.5 text-center {pitSortKey === 'season_pitching_w' ? 'text-blue-400 font-semibold' : 'text-gray-300'} hidden md:table-cell">{fmtNum(row.season_pitching_w)}</td>
              <td class="px-2 py-2.5 text-center text-gray-400 hidden md:table-cell">{fmtNum(row.season_pitching_l)}</td>
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