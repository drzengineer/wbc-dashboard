<!-- src/routes/+page.svelte -->
<script lang="ts">
  import type { PageData } from './$types';
  import { flagHtml } from '$lib/flags';

  const { data }: { data: PageData } = $props();

  const seasons = $derived(
    [...new Set((data.standings as any[]).map((s) => s.season))]
      .sort((a, b) => Number(b) - Number(a))
  );

  let selectedSeason = $state('');

  $effect(() => {
    if (seasons.length && !seasons.includes(selectedSeason)) {
      selectedSeason = seasons[0];
    }
  });

  // ── Bracket ──────────────────────────────────────────────
  const bracket = $derived(() => {
    const games = (data.knockoutGames as any[]).filter((g) => g.season === selectedSeason);
    const isModern = selectedSeason >= '2023';
    const qf = isModern
      ? games.filter((g) => g.game_type === 'D').sort((a, b) => a.official_date.localeCompare(b.official_date))
      : [];
    const sf = games.filter((g) => g.game_type === 'L').sort((a, b) => a.official_date.localeCompare(b.official_date));
    const final = games.find((g) => g.game_type === 'W') ?? null;
    return { qf, sf, final };
  });

  // ── Pools ────────────────────────────────────────────────
  const pools = $derived(() => {
    const rows = (data.standings as any[]).filter((s) => s.season === selectedSeason);
    const map = new Map<string, any[]>();
    for (const row of rows) {
      const key = row.pool_display ?? 'Other';
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(row);
    }
    for (const [, teams] of map) {
      teams.sort((a: any, b: any) => {
        const wPct = Number(b.pool_win_pct) - Number(a.pool_win_pct);
        if (wPct !== 0) return wPct;
        const diff = Number(b.pool_run_differential) - Number(a.pool_run_differential);
        if (diff !== 0) return diff;
        const rs = Number(b.pool_runs_scored) - Number(a.pool_runs_scored);
        if (rs !== 0) return rs;
        return Number(a.pool_runs_allowed) - Number(b.pool_runs_allowed);
      });
    }
    return new Map(
      [...map.entries()].sort(([a], [b]) => {
        const aIsSecond = a.toLowerCase().includes('second') || a.toLowerCase().includes('super');
        const bIsSecond = b.toLowerCase().includes('second') || b.toLowerCase().includes('super');
        if (aIsSecond && !bIsSecond) return -1;
        if (!aIsSecond && bIsSecond) return 1;
        return a.localeCompare(b);
      })
    );
  });

  // Winner on top; for unplayed games keep away on top
  function gameRows(game: any) {
    const away = {
      abbr: game.away_team_abbreviation,
      name: game.away_team_name,
      score: game.away_score,
      side: 'Away',
      isWinner: !!game.away_is_winner,
    };
    const home = {
      abbr: game.home_team_abbreviation,
      name: game.home_team_name,
      score: game.home_score,
      side: 'Home',
      isWinner: !!game.home_is_winner,
    };
    return away.isWinner || (!away.isWinner && !home.isWinner) ? [away, home] : [home, away];
  }

  function pct(val: any) {
    const n = Number(val);
    if (isNaN(n)) return '—';
    return n === 1 ? '1.000' : n === 0 ? '.000' : n.toFixed(3).replace('0.', '.');
  }

  function fmtDate(d: string) {
    return new Date(d + 'T00:00:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  }
</script>

<div class="space-y-8">

  <div>
    <h1 class="text-2xl font-bold text-white tracking-tight">Dashboard</h1>
  </div>

  <!-- Season tabs -->
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

  <!-- ── BRACKET ────────────────────────────────────────────── -->
  <section>
    <h2 class="text-lg font-semibold text-white mb-6">Bracket</h2>

    <div class="flex flex-col items-center gap-4">

      <!-- Championship -->
      <div class="w-full max-w-md">
        <p class="text-xs font-bold text-yellow-400 uppercase tracking-widest text-center mb-2">Championship</p>
        {#if bracket().final}
          {@const f = bracket().final}
          {@const rows = gameRows(f)}
          <div class="bg-gray-900 border border-yellow-500/50 rounded-xl overflow-hidden shadow-lg shadow-yellow-500/5">
            <div class="px-4 py-2 border-b border-gray-800 flex items-center justify-between">
              <span class="text-xs text-gray-500">{fmtDate(f.official_date)}</span>
              <span class="text-xs text-gray-500 truncate ml-2">{f.venue_name ?? ''}</span>
            </div>
            {#each rows as row, i}
              <div class="flex items-center justify-between px-4 py-3
                {i > 0 ? 'border-t border-gray-800/50' : ''}
                {row.isWinner ? 'bg-yellow-500/10' : ''}">
                <div class="flex items-center gap-2 min-w-0">
                  <span class="inline-block w-8 shrink-0">{@html flagHtml(row.abbr, row.name)}</span>
                  <span class="text-base font-semibold {row.isWinner ? 'text-yellow-400' : 'text-gray-400'}">
                    {#if row.isWinner}🏆 {/if}{row.abbr ?? row.name}
                  </span>
                  <span class="text-xs text-gray-600 hidden sm:inline truncate">{row.name}</span>
                </div>
                <div class="flex items-center gap-3 shrink-0">
                  <span class="text-[10px] font-medium px-1.5 py-0.5 rounded border
                    {row.side === 'Home' ? 'text-blue-400 border-blue-400/30 bg-blue-400/10' : 'text-gray-500 border-gray-700 bg-gray-800'}">
                    {row.side}
                  </span>
                  <span class="text-2xl font-bold tabular-nums w-8 text-right {row.isWinner ? 'text-yellow-400' : 'text-gray-500'}">
                    {row.score ?? '—'}
                  </span>
                </div>
              </div>
            {/each}
          </div>
        {:else}
          <div class="bg-gray-900 border border-yellow-500/20 border-dashed rounded-xl px-4 py-8 text-center text-gray-600 text-sm">TBD</div>
        {/if}
      </div>

      <div class="w-px h-5 bg-gray-700"></div>

      <!-- Semifinals -->
      <div class="w-full max-w-2xl">
        <p class="text-xs font-bold text-gray-300 uppercase tracking-widest text-center mb-2">Semifinals</p>
        <div class="grid grid-cols-2 gap-4">
          {#each Array(2) as _, idx}
            {@const game = bracket().sf[idx]}
            {#if game}
              {@const rows = gameRows(game)}
              <div class="bg-gray-900 border border-gray-800 rounded-lg overflow-hidden">
                <div class="px-3 py-1.5 border-b border-gray-800 flex items-center justify-between">
                  <span class="text-xs text-gray-500">{fmtDate(game.official_date)}</span>
                  <span class="text-xs text-gray-600 truncate ml-2">{game.venue_name ?? ''}</span>
                </div>
                {#each rows as row, i}
                  <div class="flex items-center justify-between px-3 py-2.5
                    {i > 0 ? 'border-t border-gray-800/50' : ''}
                    {row.isWinner ? 'bg-gray-800/60' : ''}">
                    <div class="flex items-center gap-1.5 min-w-0">
                      <span class="inline-block w-7 shrink-0">{@html flagHtml(row.abbr, row.name)}</span>
                      <span class="text-sm font-medium {row.isWinner ? 'text-white' : 'text-gray-500'} truncate">
                        {row.abbr ?? row.name}
                      </span>
                    </div>
                    <div class="flex items-center gap-2 shrink-0">
                      <span class="text-[10px] font-medium px-1 py-0.5 rounded border
                        {row.side === 'Home' ? 'text-blue-400 border-blue-400/30 bg-blue-400/10' : 'text-gray-500 border-gray-700 bg-gray-800'}">
                        {row.side}
                      </span>
                      <span class="text-sm font-bold tabular-nums w-6 text-right {row.isWinner ? 'text-white' : 'text-gray-500'}">
                        {row.score ?? '—'}
                      </span>
                    </div>
                  </div>
                {/each}
              </div>
            {:else}
              <div class="bg-gray-900 border border-gray-800 border-dashed rounded-lg px-4 py-6 text-center text-gray-600 text-sm">TBD</div>
            {/if}
          {/each}
        </div>
      </div>

      <!-- Quarterfinals (modern only) -->
      {#if bracket().qf.length > 0 || selectedSeason >= '2023'}
        <div class="w-px h-5 bg-gray-700"></div>
        <div class="w-full">
          <p class="text-xs font-bold text-gray-400 uppercase tracking-widest text-center mb-2">Quarterfinals</p>
          <div class="grid grid-cols-2 gap-4 lg:grid-cols-4">
            {#each Array(4) as _, idx}
              {@const game = bracket().qf[idx]}
              {#if game}
                {@const rows = gameRows(game)}
                <div class="bg-gray-900 border border-gray-800 rounded-lg overflow-hidden">
                  <div class="px-3 py-1.5 border-b border-gray-800 flex items-center justify-between">
                    <span class="text-xs text-gray-500">{fmtDate(game.official_date)}</span>
                    <span class="text-xs text-gray-600 truncate ml-2">{game.venue_name ?? ''}</span>
                  </div>
                  {#each rows as row, i}
                    <div class="flex items-center justify-between px-3 py-2.5
                      {i > 0 ? 'border-t border-gray-800/50' : ''}
                      {row.isWinner ? 'bg-gray-800/60' : ''}">
                      <div class="flex items-center gap-1.5 min-w-0">
                        <span class="inline-block w-6 shrink-0">{@html flagHtml(row.abbr, row.name)}</span>
                        <span class="text-sm font-medium {row.isWinner ? 'text-white' : 'text-gray-500'} truncate">
                          {row.abbr ?? row.name}
                        </span>
                      </div>
                      <div class="flex items-center gap-2 shrink-0">
                        <span class="text-[10px] font-medium px-1 py-0.5 rounded border
                          {row.side === 'Home' ? 'text-blue-400 border-blue-400/30 bg-blue-400/10' : 'text-gray-500 border-gray-700 bg-gray-800'}">
                          {row.side}
                        </span>
                        <span class="text-sm font-bold tabular-nums w-6 text-right {row.isWinner ? 'text-white' : 'text-gray-500'}">
                          {row.score ?? '—'}
                        </span>
                      </div>
                    </div>
                  {/each}
                </div>
              {:else}
                <div class="bg-gray-900 border border-gray-800 border-dashed rounded-lg px-4 py-6 text-center text-gray-600 text-sm">TBD</div>
              {/if}
            {/each}
          </div>
        </div>
      {/if}

    </div>
  </section>

  <!-- ── POOL STANDINGS ─────────────────────────────────────── -->
  <section>
    <h2 class="text-lg font-semibold text-white mb-4">Pool Standings</h2>
    <div class="grid grid-cols-1 gap-5 xl:grid-cols-2">
      {#each [...pools().entries()] as [poolName, teams]}
        <div class="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
          <div class="px-4 py-3 border-b border-gray-800 flex items-center gap-2">
            <span class="text-sm font-semibold text-white">{poolName}</span>
          </div>
          <!-- overflow-x-auto lets the table scroll on narrow screens instead of squishing -->
          <div class="overflow-x-auto">
            <table class="w-full text-sm">
              <thead>
                <tr class="text-xs text-gray-500 uppercase tracking-wider border-b border-gray-800">
                  <!-- indicator dot: fixed narrow column -->
                  <th class="w-5 pl-4 py-2"></th>
                  <!-- flag: fixed width -->
                  <th class="w-7 py-2"></th>
                  <!-- abbr: fixed, never wraps -->
                  <th class="w-10 py-2 text-left font-medium text-gray-500"></th>
                  <!-- full name: takes remaining space, hidden on small screens -->
                  <th class="py-2 text-left font-medium hidden sm:table-cell pr-3">Team</th>
                  <!-- stat columns: all fixed equal width, right-aligned, tabular-nums -->
                  <th class="w-10 py-2 text-center font-medium">GP</th>
                  <th class="w-10 py-2 text-center font-medium">W</th>
                  <th class="w-10 py-2 text-center font-medium">L</th>
                  <th class="w-14 py-2 text-center font-medium">PCT</th>
                  <th class="w-10 py-2 text-center font-medium">RS</th>
                  <th class="w-10 py-2 text-center font-medium">RA</th>
                  <th class="w-14 pr-4 py-2 text-center font-medium">DIFF</th>
                </tr>
              </thead>
              <tbody>
                {#each teams as team, i}
                  <tr class="border-b border-gray-800/50 last:border-0 hover:bg-gray-800/40 transition-colors
                    {team.is_champion ? 'bg-yellow-500/5' : ''}">
                    <!-- Indicator dot — fixed w-5 -->
                    <td class="w-5 p-4 py-2.5">
                      {#if i === 0}
                        <span class="text-green-400 text-xs leading-none">●</span>
                      {:else if i === 1}
                        <span class="text-green-400/50 text-xs leading-none">●</span>
                      {/if}
                    </td>
                    <!-- Flag — fixed w-7 -->
                    <td class="w-9 py-2.5">
                      <span class="inline-block w-6 shrink-0">{@html flagHtml(team.team_abbreviation, team.team_name)}</span>
                    </td>
                    <!-- Abbreviation — fixed w-10, never wraps -->
                    <td class="w-10 py-2.5 font-semibold text-white whitespace-nowrap">
                      {team.team_abbreviation ?? '—'}
                    </td>
                    <!-- Full name — flexible, hidden on small screens -->
                    <td class="py-2.5 text-gray-500 text-xs whitespace-nowrap pr-3 hidden sm:table-cell">
                      {team.team_name ?? ''}
                    </td>
                    <!-- Stat columns — all fixed width, tabular-nums -->
                    <td class="w-10 py-2.5 text-center tabular-nums text-gray-300">{team.pool_gp ?? '—'}</td>
                    <td class="w-10 py-2.5 text-center tabular-nums text-gray-300">{team.pool_wins ?? '—'}</td>
                    <td class="w-10 py-2.5 text-center tabular-nums text-gray-300">{team.pool_losses ?? '—'}</td>
                    <td class="w-14 py-2.5 text-center tabular-nums font-mono text-gray-200">{pct(team.pool_win_pct)}</td>
                    <td class="w-10 py-2.5 text-center tabular-nums text-gray-400">{team.pool_runs_scored ?? '—'}</td>
                    <td class="w-10 py-2.5 text-center tabular-nums text-gray-400">{team.pool_runs_allowed ?? '—'}</td>
                    <td class="w-14 pr-4 py-2.5 text-center tabular-nums font-mono
                      {Number(team.pool_run_differential) > 0 ? 'text-green-400' : Number(team.pool_run_differential) < 0 ? 'text-red-400' : 'text-gray-400'}">
                      {Number(team.pool_run_differential) > 0 ? '+' : ''}{team.pool_run_differential ?? '—'}
                    </td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        </div>
      {/each}
    </div>
  </section>

  <!-- ── RECENT RESULTS ─────────────────────────────────────── -->
  <section>
    <h2 class="text-lg font-semibold text-white mb-4">Recent Results</h2>
    {#if (data.recentGames as any[]).length === 0}
      <p class="text-gray-500 text-sm">No completed games found.</p>
    {:else}
      <div class="flex flex-col gap-3">
        {#each data.recentGames as game}
          <div class="bg-gray-900 border border-gray-800 rounded-xl px-5 py-4 hover:border-gray-700 transition-colors">
            <div class="flex items-center justify-between gap-4 flex-wrap">
              <div class="flex items-center gap-3">
                <div class="flex items-center gap-2">
                  <span class="inline-block w-6 shrink-0">{@html flagHtml((game as any).away_team_abbreviation, (game as any).away_team_name)}</span>
                  <span class="font-semibold text-white text-sm w-10 text-right shrink-0">
                    {(game as any).away_team_abbreviation ?? (game as any).away_team_name}
                  </span>
                  <span class="text-2xl font-bold tabular-nums {(game as any).away_is_winner ? 'text-white' : 'text-gray-500'}">
                    {(game as any).away_score ?? '—'}
                  </span>
                </div>
                <span class="text-gray-600 text-sm">–</span>
                <div class="flex items-center gap-2">
                  <span class="text-2xl font-bold tabular-nums {(game as any).home_is_winner ? 'text-white' : 'text-gray-500'}">
                    {(game as any).home_score ?? '—'}
                  </span>
                  <span class="font-semibold text-white text-sm w-10 shrink-0">
                    {(game as any).home_team_abbreviation ?? (game as any).home_team_name}
                  </span>
                  <span class="inline-block w-6 shrink-0">{@html flagHtml((game as any).home_team_abbreviation, (game as any).home_team_name)}</span>
                </div>
                {#if (game as any).is_mercy_rule}
                  <span class="text-xs bg-orange-500/20 text-orange-400 border border-orange-500/30 rounded px-1.5 py-0.5 shrink-0">Mercy</span>
                {/if}
              </div>
              <div class="flex items-center gap-3 text-xs text-gray-500 flex-wrap shrink-0">
                <span class="bg-gray-800 text-gray-300 rounded px-2 py-1">
                  {(game as any).round_label ?? (game as any).pool_display ?? '—'}
                </span>
                <span>{fmtDate((game as any).official_date)}</span>
                <span class="hidden md:inline text-gray-600">{(game as any).venue_name ?? ''}</span>
              </div>
            </div>
            {#if (game as any).venue_name}
              <p class="text-xs text-gray-600 mt-2 md:hidden">{(game as any).venue_name}</p>
            {/if}
          </div>
        {/each}
      </div>
    {/if}
  </section>

</div>