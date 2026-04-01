<script lang="ts">
  import { onMount } from 'svelte';

  const { data } = $props();

  const player       = $derived(data.player as any);
  const allSeasons   = $derived(data.tournamentStats as any[]);
  const allGameLogs  = $derived(data.gameLogs as any[]);
  const isPitcher    = $derived(player?.position_type === 'Pitcher');

  const seasons = $derived(
    [...new Set(allSeasons.map((s: any) => s.season))].sort((a, b) => b - a)
  );
  let selectedSeason = $state(seasons[0] ?? 2026);

  const seasonRow = $derived(
    allSeasons.find((s: any) => s.season === selectedSeason) ?? allSeasons[0]
  );

  // Game log for selected season — lazy rendered
  const seasonLogs = $derived(
    allGameLogs.filter((g: any) => g.season === selectedSeason)
  );
  let visibleLogCount = $state(15);
  let logSentinelRef = $state<HTMLElement | null>(null);

  onMount(() => {
    const io = new IntersectionObserver((entries) => {
      if (entries[0].isIntersecting) visibleLogCount += 15;
    }, { rootMargin: '200px' });
    if (logSentinelRef) io.observe(logSentinelRef);
    return () => io.disconnect();
  });

  $effect(() => { selectedSeason; visibleLogCount = 15; });

  const visibleLogs = $derived(seasonLogs.slice(0, visibleLogCount));

  // ─── Career totals (multi-season batters/pitchers) ────────────────────────────
  const hasMultipleSeasons = $derived(allSeasons.length > 1);

  const careerBatting = $derived(() => {
    if (isPitcher || !hasMultipleSeasons) return null;
    return {
      g:   allSeasons.reduce((s: number, r: any) => s + (r.games_played ?? 0), 0),
      ab:  allSeasons.reduce((s: number, r: any) => s + (r.season_batting_ab ?? 0), 0),
      h:   allSeasons.reduce((s: number, r: any) => s + (r.season_batting_h ?? 0), 0),
      hr:  allSeasons.reduce((s: number, r: any) => s + (r.season_batting_hr ?? 0), 0),
      rbi: allSeasons.reduce((s: number, r: any) => s + (r.season_batting_rbi ?? 0), 0),
      r:   allSeasons.reduce((s: number, r: any) => s + (r.season_batting_r ?? 0), 0),
      bb:  allSeasons.reduce((s: number, r: any) => s + (r.season_batting_bb ?? 0), 0),
      so:  allSeasons.reduce((s: number, r: any) => s + (r.season_batting_so ?? 0), 0),
      sb:  allSeasons.reduce((s: number, r: any) => s + (r.season_batting_sb ?? 0), 0),
    };
  });

  const careerPitching = $derived(() => {
    if (!isPitcher || !hasMultipleSeasons) return null;
    const totalEarnedRuns = allSeasons.reduce((s: number, r: any) => {
      const era = Number(r.season_pitching_era);
      const ip  = Number(r.season_pitching_ip);
      return s + (isNaN(era) || isNaN(ip) ? 0 : (era * ip) / 9);
    }, 0);
    const totalIp = allSeasons.reduce((s: number, r: any) => s + Number(r.season_pitching_ip ?? 0), 0);
    const careerEra = totalIp > 0 ? ((totalEarnedRuns / totalIp) * 9).toFixed(2) : '—';
    return {
      era: careerEra,
      ip:  totalIp,
      w:   allSeasons.reduce((s: number, r: any) => s + (r.season_pitching_w ?? 0), 0),
      l:   allSeasons.reduce((s: number, r: any) => s + (r.season_pitching_l ?? 0), 0),
      sv:  allSeasons.reduce((s: number, r: any) => s + (r.season_pitching_sv ?? 0), 0),
      so:  allSeasons.reduce((s: number, r: any) => s + (r.season_pitching_so ?? 0), 0),
      bb:  allSeasons.reduce((s: number, r: any) => s + (r.season_pitching_bb ?? 0), 0),
    };
  });

  // ─── Helpers ──────────────────────────────────────────────────────────────────
  function fmtAvg(v: any) { return v ? String(v).replace(/^0/, '') : '—'; }
  function fmtNum(v: any) { return v != null ? v : '—'; }
  function fmtIp(v: any) {
    if (v == null) return '—';
    const full = Math.floor(Number(v));
    const frac = Math.round((Number(v) - full) * 3);
    return frac === 0 ? `${full}.0` : `${full}.${frac}`;
  }
  function age(birthDate: string) {
    if (!birthDate) return null;
    const diff = Date.now() - new Date(birthDate).getTime();
    return Math.floor(diff / (365.25 * 24 * 3600 * 1000));
  }
  function gameResult(log: any) {
    const gr = log._gr;
    if (!gr || gr.away_score == null) return '—';
    const myAbbr = log.team_abbreviation;
    const iAway  = gr.away_team_abbreviation === myAbbr;
    const myScore  = iAway ? gr.away_score : gr.home_score;
    const oppScore = iAway ? gr.home_score  : gr.away_score;
    const oppAbbr  = iAway ? gr.home_team_abbreviation : gr.away_team_abbreviation;
    const result   = myScore > oppScore ? 'W' : myScore < oppScore ? 'L' : 'T';
    return `${result} ${myScore}–${oppScore} vs ${oppAbbr}`;
  }
  function resultColor(log: any) {
    const gr = log._gr;
    if (!gr || gr.away_score == null) return 'text-gray-500';
    const myAbbr = log.team_abbreviation;
    const iAway  = gr.away_team_abbreviation === myAbbr;
    const myScore  = iAway ? gr.away_score : gr.home_score;
    const oppScore = iAway ? gr.home_score  : gr.away_score;
    return myScore > oppScore ? 'text-green-500' : myScore < oppScore ? 'text-red-500' : 'text-gray-400';
  }
</script>

<!-- Back link -->
<div class="mb-4">
  <a href="/players" class="text-sm text-gray-500 hover:text-blue-400 transition-colors flex items-center gap-1">
    <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/>
    </svg>
    Players
  </a>
</div>

<!-- Player header card -->
<div class="bg-gray-900 border border-gray-800 rounded-xl p-4 md:p-6 mb-6">
  <div class="flex flex-col sm:flex-row sm:items-start gap-4">
    <div class="flex-1 min-w-0">
      <h1 class="text-xl md:text-2xl font-bold text-white truncate">{player?.full_name}</h1>
      <div class="flex flex-wrap items-center gap-2 mt-1">
        <span class="text-sm text-gray-400">{player?.represented_country}</span>
        <span class="text-xs px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-400 border border-blue-700/40">{player?.position_abbreviation}</span>
        {#if allSeasons.length > 1}
          <span class="text-xs px-2 py-0.5 rounded-full bg-gray-800 text-gray-400">{allSeasons.length} WBC seasons</span>
        {/if}
      </div>
    </div>
    <div class="text-sm text-gray-500 space-y-0.5 shrink-0">
      {#if player?.birth_date}<div>Age {age(player.birth_date)}</div>{/if}
      {#if player?.height}<div>{player.height} / {player.weight} lb</div>{/if}
      {#if player?.bat_side && !isPitcher}<div>Bats {player.bat_side}</div>{/if}
      {#if player?.pitch_hand && isPitcher}<div>Throws {player.pitch_hand}</div>{/if}
    </div>
  </div>
</div>

<!-- Career totals (multi-season only) -->
{#if hasMultipleSeasons && (careerBatting() || careerPitching())}
  <section class="mb-6">
    <h2 class="text-sm font-semibold uppercase tracking-widest text-gray-500 mb-3">Career WBC Totals</h2>
    {#if careerBatting()}
      {@const cb = careerBatting()!}
      <div class="grid grid-cols-4 sm:grid-cols-8 gap-2">
        {#each [
          { label: 'G', value: cb.g }, { label: 'AB', value: cb.ab },
          { label: 'H', value: cb.h }, { label: 'HR', value: cb.hr },
          { label: 'RBI', value: cb.rbi }, { label: 'R', value: cb.r },
          { label: 'BB', value: cb.bb }, { label: 'SB', value: cb.sb },
        ] as stat}
          <div class="bg-gray-900 border border-gray-800 rounded-lg px-3 py-2 text-center">
            <div class="text-lg font-bold text-white">{stat.value}</div>
            <div class="text-xs text-gray-500">{stat.label}</div>
          </div>
        {/each}
      </div>
    {/if}
    {#if careerPitching()}
      {@const cp = careerPitching()!}
      <div class="grid grid-cols-4 sm:grid-cols-7 gap-2">
        {#each [
          { label: 'ERA', value: cp.era }, { label: 'IP', value: fmtIp(cp.ip) },
          { label: 'W', value: cp.w }, { label: 'L', value: cp.l },
          { label: 'SV', value: cp.sv }, { label: 'K', value: cp.so },
          { label: 'BB', value: cp.bb },
        ] as stat}
          <div class="bg-gray-900 border border-gray-800 rounded-lg px-3 py-2 text-center">
            <div class="text-lg font-bold text-white">{stat.value}</div>
            <div class="text-xs text-gray-500">{stat.label}</div>
          </div>
        {/each}
      </div>
    {/if}
  </section>
{/if}

<!-- By-season table -->
<section class="mb-6">
  <h2 class="text-sm font-semibold uppercase tracking-widest text-gray-500 mb-3">By Season</h2>
  <div class="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
    <div class="overflow-x-auto">
      <table class="w-full text-sm">
        <thead class="text-xs text-gray-500 border-b border-gray-800 bg-gray-800/40">
          {#if !isPitcher}
            <tr>
              <th class="text-left px-4 py-2.5 font-medium">Year</th>
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
              class="border-b border-gray-800/50 last:border-0 hover:bg-gray-800/30 transition-colors cursor-pointer {row.season === selectedSeason ? 'border-l-2 border-l-blue-500' : ''}"
              onclick={() => selectedSeason = row.season}
            >
              {#if !isPitcher}
                <td class="px-4 py-2.5 font-medium {row.season === selectedSeason ? 'text-blue-400' : ''}">{row.season}</td>
                <td class="px-2 py-2.5 text-center text-gray-400">{fmtNum(row.games_played)}</td>
                <td class="px-2 py-2.5 text-center text-gray-400">{fmtNum(row.season_batting_ab)}</td>
                <td class="px-2 py-2.5 text-center font-mono text-gray-200">{fmtAvg(row.season_batting_avg)}</td>
                <td class="px-2 py-2.5 text-center text-gray-300">{fmtNum(row.season_batting_hr)}</td>
                <td class="px-2 py-2.5 text-center text-gray-300">{fmtNum(row.season_batting_rbi)}</td>
                <td class="px-2 py-2.5 text-center font-mono text-gray-400 hidden sm:table-cell">{fmtAvg(row.season_batting_obp)}</td>
                <td class="px-2 py-2.5 text-center font-mono text-gray-400 hidden sm:table-cell">{fmtAvg(row.season_batting_slg)}</td>
                <td class="px-3 py-2.5 text-center font-mono text-gray-200">{fmtAvg(row.season_batting_ops)}</td>
              {:else}
                <td class="px-4 py-2.5 font-medium {row.season === selectedSeason ? 'text-blue-400' : ''}">{row.season}</td>
                <td class="px-2 py-2.5 text-center text-gray-400">{fmtNum(row.games_played)}</td>
                <td class="px-2 py-2.5 text-center font-mono text-gray-200">{fmtNum(row.season_pitching_era)}</td>
                <td class="px-2 py-2.5 text-center font-mono text-gray-300">{fmtIp(row.season_pitching_ip)}</td>
                <td class="px-2 py-2.5 text-center text-gray-300">{fmtNum(row.season_pitching_w)}</td>
                <td class="px-2 py-2.5 text-center text-gray-400">{fmtNum(row.season_pitching_l)}</td>
                <td class="px-2 py-2.5 text-center text-gray-400 hidden sm:table-cell">{fmtNum(row.season_pitching_sv)}</td>
                <td class="px-2 py-2.5 text-center text-gray-300 hidden sm:table-cell">{fmtNum(row.season_pitching_so)}</td>
                <td class="px-3 py-2.5 text-center text-gray-400 hidden sm:table-cell">{fmtNum(row.season_pitching_bb)}</td>
              {/if}
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  </div>
</section>

<!-- Game log — lazy loaded -->
<section>
  <div class="flex items-center gap-3 mb-3">
    <h2 class="text-sm font-semibold uppercase tracking-widest text-gray-500">Game Log</h2>
    <div class="flex gap-1">
      {#each seasons as s}
        <button
          onclick={() => selectedSeason = s}
          class="px-2.5 py-0.5 rounded-full text-xs font-medium transition-colors {selectedSeason === s ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-400 hover:text-white'}"
        >{s}</button>
      {/each}
    </div>
  </div>

  <div class="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
    <div class="overflow-x-auto">
      <table class="w-full text-sm">
        <thead class="text-xs text-gray-500 border-b border-gray-800 bg-gray-800/40">
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
            <tr class="border-b border-gray-800/50 last:border-0 hover:bg-gray-800/30 transition-colors">
              {#if !isPitcher}
                <td class="px-4 py-2 text-gray-400 whitespace-nowrap">{log.official_date}</td>
                <td class="px-2 py-2 text-gray-500 text-xs hidden sm:table-cell">{log._gr?.round_label ?? '—'}</td>
                <td class="px-2 py-2 text-xs {resultColor(log)} whitespace-nowrap">{gameResult(log)}</td>
                <td class="px-2 py-2 text-center text-gray-400">{fmtNum(log.batting_ab)}</td>
                <td class="px-2 py-2 text-center text-gray-300">{fmtNum(log.batting_h)}</td>
                <td class="px-2 py-2 text-center text-gray-300 hidden sm:table-cell">{fmtNum(log.batting_hr)}</td>
                <td class="px-2 py-2 text-center text-gray-300 hidden sm:table-cell">{fmtNum(log.batting_rbi)}</td>
                <td class="px-2 py-2 text-center text-gray-400 hidden md:table-cell">{fmtNum(log.batting_bb)}</td>
                <td class="px-3 py-2 text-center text-gray-400 hidden md:table-cell">{fmtNum(log.batting_so)}</td>
              {:else}
                <td class="px-4 py-2 text-gray-400 whitespace-nowrap">{log.official_date}</td>
                <td class="px-2 py-2 text-gray-500 text-xs hidden sm:table-cell">{log._gr?.round_label ?? '—'}</td>
                <td class="px-2 py-2 text-xs {resultColor(log)} whitespace-nowrap">{gameResult(log)}</td>
                <td class="px-2 py-2 text-center font-mono text-gray-300">{fmtIp(log.pitching_ip)}</td>
                <td class="px-2 py-2 text-center text-gray-400">{fmtNum(log.pitching_er)}</td>
                <td class="px-2 py-2 text-center text-gray-300 hidden sm:table-cell">{fmtNum(log.pitching_so)}</td>
                <td class="px-2 py-2 text-center text-gray-400 hidden sm:table-cell">{fmtNum(log.pitching_bb)}</td>
                <td class="px-2 py-2 text-center text-gray-400 hidden md:table-cell">{fmtNum(log.pitching_h)}</td>
                <td class="px-3 py-2 text-center text-xs hidden md:table-cell">
                  {#if log.pitching_w}<span class="text-green-500">W</span>{:else if log.pitching_l}<span class="text-red-500">L</span>{:else if log.pitching_sv}<span class="text-blue-400">SV</span>{:else}<span class="text-gray-600">—</span>{/if}
                </td>
              {/if}
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  </div>

  {#if seasonLogs.length === 0}
    <p class="text-gray-500 text-sm mt-3">No game log data for {selectedSeason}.</p>
  {/if}

  <!-- Infinite scroll sentinel -->
  {#if visibleLogCount < seasonLogs.length}
    <div bind:this={logSentinelRef} class="mt-4 flex justify-center">
      <div class="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
    </div>
  {/if}
</section>