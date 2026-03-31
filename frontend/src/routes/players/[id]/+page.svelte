<!-- src/routes/players/[id]/+page.svelte -->
<script lang="ts">
  import type { PageData } from './$types';

  const { data }: { data: PageData } = $props();

  const player          = data.player          as any;
  const tournamentStats = data.tournamentStats  as any[];
  const allGameLogs     = data.gameLogs         as any[];

  const isPitcher = player.position_type === 'Pitcher';

  // ── Season selector for game log ─────────────────────────────
  const seasons = $derived(
    [...new Set(tournamentStats.map((s: any) => s.season))].sort((a, b) => Number(b) - Number(a))
  );

  let selectedSeason = $state('');

  $effect(() => {
    if (seasons.length && !seasons.includes(selectedSeason)) {
      selectedSeason = seasons[0];
    }
  });

  const gameLogs = $derived(
    allGameLogs
      .filter((g: any) => g.season === selectedSeason)
      .sort((a: any, b: any) => String(a.official_date).localeCompare(String(b.official_date)))
  );

  // ── Formatters ───────────────────────────────────────────────
  function fmtAvg(val: any): string {
    const n = Number(val);
    if (isNaN(n) || val == null) return '—';
    return n === 1 ? '1.000' : n === 0 ? '.000' : n.toFixed(3).replace('0.', '.');
  }

  function fmtEra(val: any): string {
    const n = Number(val);
    if (isNaN(n) || val == null) return '—';
    return n.toFixed(2);
  }

  function fmtIp(val: any): string {
    const n = Number(val);
    if (isNaN(n) || val == null) return '—';
    return n.toFixed(1);
  }

  function fmtDate(d: any): string {
    return new Date(String(d) + 'T00:00:00').toLocaleDateString('en-US', {
      month: 'short', day: 'numeric',
    });
  }

  function dash(v: any): string {
    return v != null && v !== '' ? String(v) : '—';
  }

  const FLAGS: Record<string, string> = {
    'USA': 'us', 'DOM': 'do', 'PUR': 'pr', 'JPN': 'jp', 'CUB': 'cu',
    'VEN': 've', 'MEX': 'mx', 'KOR': 'kr', 'NED': 'nl', 'ITA': 'it',
    'AUS': 'au', 'CAN': 'ca', 'PAN': 'pa', 'TPE': 'tw', 'CHN': 'cn',
    'NCA': 'ni', 'COL': 'co', 'ISR': 'il', 'GBR': 'gb', 'CZE': 'cz',
    'ESP': 'es', 'RSA': 'za', 'NZL': 'nz', 'BRA': 'br', 'FRA': 'fr',
    'GER': 'de', 'AUT': 'at', 'PHI': 'ph', 'PAK': 'pk', 'UGA': 'ug',
    'ARG': 'ar',
  };

  function flagImg(abbr?: string): string {
    const code = abbr ? FLAGS[abbr] : null;
    if (!code) return '<span class="w-[28px] h-[20px] inline-block bg-gray-700 rounded"></span>';
    return `<img src="https://flagcdn.com/${code}.svg" alt="${abbr}" class="w-[28px] h-[20px] rounded-sm object-cover">`;
  }

  function age(birthDate?: string): string {
    if (!birthDate) return '—';
    const bd = new Date(birthDate);
    const now = new Date();
    const yr = now.getFullYear() - bd.getFullYear();
    const adj = now < new Date(now.getFullYear(), bd.getMonth(), bd.getDate()) ? 1 : 0;
    return String(yr - adj);
  }

  // ── Game log helpers — use merged _gr (game_results) fields ──
  // team_side = 'home' | 'away' — opponent is the other side
  function gameOpponent(game: any): string {
    const gr = game._gr;
    if (!gr) return '—';
    return game.team_side === 'home'
      ? (gr.away_team_abbreviation ?? '—')
      : (gr.home_team_abbreviation ?? '—');
  }

  function gameResult(game: any): { label: string; cls: string } {
    const gr = game._gr;
    if (!gr) return { label: '—', cls: 'text-gray-500' };
    const myScore  = game.team_side === 'home' ? Number(gr.home_score) : Number(gr.away_score);
    const oppScore = game.team_side === 'home' ? Number(gr.away_score) : Number(gr.home_score);
    if (isNaN(myScore) || isNaN(oppScore)) return { label: '—', cls: 'text-gray-500' };
    if (myScore > oppScore) return { label: 'W', cls: 'text-green-400 font-bold' };
    if (myScore < oppScore) return { label: 'L', cls: 'text-red-400 font-bold' };
    return { label: 'T', cls: 'text-yellow-400 font-bold' };
  }

  function gameRound(game: any): string {
    return game._gr?.round_label ?? game._gr?.pool_display ?? '—';
  }

  // ── Career totals — only counting stats, no doubles/triples (not in player_tournament_stats) ──
  const careerBatting = $derived(() => {
    const ab  = tournamentStats.reduce((s: number, t: any) => s + (Number(t.season_batting_ab)  || 0), 0);
    const h   = tournamentStats.reduce((s: number, t: any) => s + (Number(t.season_batting_h)   || 0), 0);
    const hr  = tournamentStats.reduce((s: number, t: any) => s + (Number(t.season_batting_hr)  || 0), 0);
    const rbi = tournamentStats.reduce((s: number, t: any) => s + (Number(t.season_batting_rbi) || 0), 0);
    const r   = tournamentStats.reduce((s: number, t: any) => s + (Number(t.season_batting_r)   || 0), 0);
    const bb  = tournamentStats.reduce((s: number, t: any) => s + (Number(t.season_batting_bb)  || 0), 0);
    const so  = tournamentStats.reduce((s: number, t: any) => s + (Number(t.season_batting_so)  || 0), 0);
    const sb  = tournamentStats.reduce((s: number, t: any) => s + (Number(t.season_batting_sb)  || 0), 0);
    const avg = ab > 0 ? h / ab : null;
    return { ab, h, hr, rbi, r, bb, so, sb, avg };
  });

  const careerPitching = $derived(() => {
    const ip  = tournamentStats.reduce((s: number, t: any) => s + (Number(t.season_pitching_ip) || 0), 0);
    const so  = tournamentStats.reduce((s: number, t: any) => s + (Number(t.season_pitching_so) || 0), 0);
    const bb  = tournamentStats.reduce((s: number, t: any) => s + (Number(t.season_pitching_bb) || 0), 0);
    const w   = tournamentStats.reduce((s: number, t: any) => s + (Number(t.season_pitching_w)  || 0), 0);
    const l   = tournamentStats.reduce((s: number, t: any) => s + (Number(t.season_pitching_l)  || 0), 0);
    const sv  = tournamentStats.reduce((s: number, t: any) => s + (Number(t.season_pitching_sv) || 0), 0);
    // Back-calculate career ER from ERA × IP / 9 per season, then recompute career ERA
    // season_pitching_era is stored as text — Number() coerces it correctly
    const er  = tournamentStats.reduce((s: number, t: any) => {
      const era = Number(t.season_pitching_era);
      const ip  = Number(t.season_pitching_ip);
      if (isNaN(era) || !isFinite(era) || ip === 0) return s;
      return s + (era * ip / 9);
    }, 0);
    const era = ip > 0 ? (er / ip) * 9 : null;
    return { ip, so, bb, w, l, sv, era };
  });
</script>

<div class="space-y-8">

  <!-- Back link -->
  <div>
    <a href="/players" class="text-sm text-gray-500 hover:text-white transition-colors inline-flex items-center gap-1">
      ← Players
    </a>
  </div>

  <!-- ── PLAYER HEADER ─────────────────────────────────────────── -->
  <div class="bg-gray-900 border border-gray-800 rounded-xl px-6 py-6">
    <div class="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">

      <div>
        <div class="flex items-center gap-3 mb-2">
          <span class="text-2xl font-bold text-white tracking-tight">{player.full_name}</span>
          <span>{@html flagImg(player.team_abbreviation)}</span>
        </div>
        <div class="flex flex-wrap gap-x-4 gap-y-1.5 text-sm text-gray-400">
          {#if player.position_abbreviation}
            <span class="bg-gray-800 border border-gray-700 rounded px-2 py-0.5 text-xs font-medium text-gray-300">
              {player.position_abbreviation}
            </span>
          {/if}
          {#if player.team_name}
            <span>{player.team_name}</span>
          {/if}
          {#if player.birth_date}
            <span class="text-gray-500">Age {age(String(player.birth_date))}</span>
          {/if}
          {#if player.height}
            <span class="text-gray-500">{player.height}</span>
          {/if}
          {#if player.weight}
            <span class="text-gray-500">{player.weight} lbs</span>
          {/if}
          {#if player.bat_side}
            <span class="text-gray-500">Bats {player.bat_side}</span>
          {/if}
          {#if player.pitch_hand}
            <span class="text-gray-500">Throws {player.pitch_hand}</span>
          {/if}
        </div>
      </div>

      <div class="shrink-0 sm:text-right">
        <p class="text-xs text-gray-500 uppercase tracking-wider">WBC Seasons</p>
        <p class="text-3xl font-bold text-white">{seasons.length}</p>
        <p class="text-xs text-gray-500 mt-0.5">{seasons.join(' · ')}</p>
      </div>

    </div>
  </div>

  <!-- ── CAREER TOTALS (only shown for multi-season players) ───── -->
  {#if seasons.length > 1}
    <section>
      <h2 class="text-lg font-semibold text-white mb-4">Career WBC Totals</h2>
      <div class="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
        {#if !isPitcher}
          {@const cb = careerBatting()}
          <div class="grid grid-cols-4 sm:grid-cols-8 divide-x divide-y divide-gray-800">
            {#each [
              { label: 'AVG', value: fmtAvg(cb.avg) },
              { label: 'AB',  value: cb.ab  },
              { label: 'H',   value: cb.h   },
              { label: 'HR',  value: cb.hr  },
              { label: 'RBI', value: cb.rbi },
              { label: 'R',   value: cb.r   },
              { label: 'BB',  value: cb.bb  },
              { label: 'SO',  value: cb.so  },
            ] as stat}
              <div class="px-4 py-4 text-center">
                <p class="text-xs text-gray-500 uppercase tracking-wider mb-1">{stat.label}</p>
                <p class="text-xl font-bold text-white tabular-nums">{stat.value}</p>
              </div>
            {/each}
          </div>
        {:else}
          {@const cp = careerPitching()}
          <div class="grid grid-cols-4 sm:grid-cols-7 divide-x divide-y divide-gray-800">
            {#each [
              { label: 'ERA', value: fmtEra(cp.era) },
              { label: 'IP',  value: fmtIp(cp.ip)  },
              { label: 'W',   value: cp.w  },
              { label: 'L',   value: cp.l  },
              { label: 'SV',  value: cp.sv },
              { label: 'K',   value: cp.so },
              { label: 'BB',  value: cp.bb },
            ] as stat}
              <div class="px-4 py-4 text-center">
                <p class="text-xs text-gray-500 uppercase tracking-wider mb-1">{stat.label}</p>
                <p class="text-xl font-bold text-white tabular-nums">{stat.value}</p>
              </div>
            {/each}
          </div>
        {/if}
      </div>
    </section>
  {/if}

  <!-- ── BY-SEASON TABLE ───────────────────────────────────────── -->
  <section>
    <h2 class="text-lg font-semibold text-white mb-4">Tournament Stats by Season</h2>
    <div class="bg-gray-900 border border-gray-800 rounded-xl overflow-x-auto">

      {#if !isPitcher}
        <!-- Batting — note: doubles/triples not in player_tournament_stats, only in game log -->
        <table class="w-full text-sm">
          <thead>
            <tr class="text-xs text-gray-500 uppercase tracking-wider border-b border-gray-800">
              <th class="text-left  px-5 py-2 font-medium">Season</th>
              <th class="text-left  px-3 py-2 font-medium hidden sm:table-cell">Country</th>
              <th class="text-right px-3 py-2 font-medium">GP</th>
              <th class="text-right px-3 py-2 font-medium">AB</th>
              <th class="text-right px-3 py-2 font-medium">H</th>
              <th class="text-right px-3 py-2 font-medium">HR</th>
              <th class="text-right px-3 py-2 font-medium">RBI</th>
              <th class="text-right px-3 py-2 font-medium">R</th>
              <th class="text-right px-3 py-2 font-medium">BB</th>
              <th class="text-right px-3 py-2 font-medium">SO</th>
              <th class="text-right px-3 py-2 font-medium">SB</th>
              <th class="text-right px-3 py-2 font-medium">AVG</th>
              <th class="text-right px-5 py-2 font-medium">OPS</th>
            </tr>
          </thead>
          <tbody>
            {#each tournamentStats as ts}
              <tr class="border-b border-gray-800/50 last:border-0 hover:bg-gray-800/40 transition-colors
                {ts.season === selectedSeason ? 'bg-blue-600/5 border-l-2 border-l-blue-600' : ''}">
                <td class="px-5 py-3 font-semibold text-white">{ts.season}</td>
                <td class="px-3 py-3 hidden sm:table-cell">
                  <div class="flex items-center gap-1.5">
                    {@html flagImg(ts.team_abbreviation)}
                    <span class="text-gray-400 text-xs">{ts.team_abbreviation ?? '—'}</span>
                  </div>
                </td>
                <td class="px-3 py-3 text-right text-gray-300 tabular-nums">{dash(ts.games_played)}</td>
                <td class="px-3 py-3 text-right text-gray-400 tabular-nums">{dash(ts.season_batting_ab)}</td>
                <td class="px-3 py-3 text-right text-gray-400 tabular-nums">{dash(ts.season_batting_h)}</td>
                <td class="px-3 py-3 text-right text-gray-400 tabular-nums">{dash(ts.season_batting_hr)}</td>
                <td class="px-3 py-3 text-right text-gray-400 tabular-nums">{dash(ts.season_batting_rbi)}</td>
                <td class="px-3 py-3 text-right text-gray-400 tabular-nums">{dash(ts.season_batting_r)}</td>
                <td class="px-3 py-3 text-right text-gray-400 tabular-nums">{dash(ts.season_batting_bb)}</td>
                <td class="px-3 py-3 text-right text-gray-400 tabular-nums">{dash(ts.season_batting_so)}</td>
                <td class="px-3 py-3 text-right text-gray-400 tabular-nums">{dash(ts.season_batting_sb)}</td>
                <td class="px-3 py-3 text-right font-mono text-gray-200 tabular-nums">{fmtAvg(ts.season_batting_avg)}</td>
                <td class="px-5 py-3 text-right font-mono font-semibold text-white tabular-nums">{fmtAvg(ts.season_batting_ops)}</td>
              </tr>
            {/each}
          </tbody>
        </table>

      {:else}
        <!-- Pitching -->
        <table class="w-full text-sm">
          <thead>
            <tr class="text-xs text-gray-500 uppercase tracking-wider border-b border-gray-800">
              <th class="text-left  px-5 py-2 font-medium">Season</th>
              <th class="text-left  px-3 py-2 font-medium hidden sm:table-cell">Country</th>
              <th class="text-right px-3 py-2 font-medium">GP</th>
              <th class="text-right px-3 py-2 font-medium">W</th>
              <th class="text-right px-3 py-2 font-medium">L</th>
              <th class="text-right px-3 py-2 font-medium">SV</th>
              <th class="text-right px-3 py-2 font-medium">IP</th>
              <th class="text-right px-3 py-2 font-medium">K</th>
              <th class="text-right px-3 py-2 font-medium">BB</th>
              <th class="text-right px-3 py-2 font-medium">BF</th>
              <th class="text-right px-5 py-2 font-medium">ERA</th>
            </tr>
          </thead>
          <tbody>
            {#each tournamentStats as ts}
              <tr class="border-b border-gray-800/50 last:border-0 hover:bg-gray-800/40 transition-colors
                {ts.season === selectedSeason ? 'bg-blue-600/5 border-l-2 border-l-blue-600' : ''}">
                <td class="px-5 py-3 font-semibold text-white">{ts.season}</td>
                <td class="px-3 py-3 hidden sm:table-cell">
                  <div class="flex items-center gap-1.5">
                    {@html flagImg(ts.team_abbreviation)}
                    <span class="text-gray-400 text-xs">{ts.team_abbreviation ?? '—'}</span>
                  </div>
                </td>
                <td class="px-3 py-3 text-right text-gray-300 tabular-nums">{dash(ts.games_played)}</td>
                <td class="px-3 py-3 text-right text-gray-400 tabular-nums">{dash(ts.season_pitching_w)}</td>
                <td class="px-3 py-3 text-right text-gray-400 tabular-nums">{dash(ts.season_pitching_l)}</td>
                <td class="px-3 py-3 text-right text-gray-400 tabular-nums">{dash(ts.season_pitching_sv)}</td>
                <td class="px-3 py-3 text-right text-gray-400 tabular-nums">{fmtIp(ts.season_pitching_ip)}</td>
                <td class="px-3 py-3 text-right text-gray-400 tabular-nums">{dash(ts.season_pitching_so)}</td>
                <td class="px-3 py-3 text-right text-gray-400 tabular-nums">{dash(ts.season_pitching_bb)}</td>
                <td class="px-3 py-3 text-right text-gray-400 tabular-nums">{dash(ts.season_pitching_bf)}</td>
                <td class="px-5 py-3 text-right font-mono font-semibold text-white tabular-nums">{fmtEra(ts.season_pitching_era)}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      {/if}

    </div>
  </section>

  <!-- ── GAME LOG ──────────────────────────────────────────────── -->
  <section>
    <div class="flex items-center justify-between mb-4 flex-wrap gap-3">
      <h2 class="text-lg font-semibold text-white">Game Log</h2>
      <div class="flex gap-1 bg-gray-900 border border-gray-800 rounded-lg p-1">
        {#each seasons as season}
          <button
            type="button"
            onclick={() => selectedSeason = season}
            class="px-3 py-1 rounded-md text-xs font-medium transition-colors
              {selectedSeason === season ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-white hover:bg-gray-800'}"
          >
            {season}
          </button>
        {/each}
      </div>
    </div>

    {#if gameLogs.length === 0}
      <div class="bg-gray-900 border border-gray-800 rounded-xl px-6 py-10 text-center">
        <p class="text-gray-500 text-sm">No game log data for {selectedSeason}.</p>
      </div>
    {:else}
      <div class="bg-gray-900 border border-gray-800 rounded-xl overflow-x-auto">

        {#if !isPitcher}
          <table class="w-full text-sm">
            <thead>
              <tr class="text-xs text-gray-500 uppercase tracking-wider border-b border-gray-800">
                <th class="text-left  px-5 py-2 font-medium">Date</th>
                <th class="text-left  px-3 py-2 font-medium">Opp</th>
                <th class="text-center px-3 py-2 font-medium">W/L</th>
                <th class="text-left  px-3 py-2 font-medium hidden sm:table-cell">Round</th>
                <th class="text-right px-3 py-2 font-medium">AB</th>
                <th class="text-right px-3 py-2 font-medium">H</th>
                <th class="text-right px-3 py-2 font-medium">2B</th>
                <th class="text-right px-3 py-2 font-medium">3B</th>
                <th class="text-right px-3 py-2 font-medium">HR</th>
                <th class="text-right px-3 py-2 font-medium">RBI</th>
                <th class="text-right px-3 py-2 font-medium">BB</th>
                <th class="text-right px-3 py-2 font-medium">SO</th>
                <th class="text-right px-5 py-2 font-medium">AVG</th>
              </tr>
            </thead>
            <tbody>
              {#each gameLogs as game}
                {@const result = gameResult(game)}
                <tr class="border-b border-gray-800/50 last:border-0 hover:bg-gray-800/40 transition-colors">
                  <td class="px-5 py-2.5 text-gray-400 tabular-nums text-xs">{fmtDate(game.official_date)}</td>
                  <td class="px-3 py-2.5 text-gray-300 font-medium text-xs">{gameOpponent(game)}</td>
                  <td class="px-3 py-2.5 text-center text-xs {result.cls}">{result.label}</td>
                  <td class="px-3 py-2.5 hidden sm:table-cell text-xs text-gray-500">{gameRound(game)}</td>
                  <td class="px-3 py-2.5 text-right text-gray-400 tabular-nums text-xs">{dash(game.batting_ab)}</td>
                  <td class="px-3 py-2.5 text-right text-gray-400 tabular-nums text-xs">{dash(game.batting_h)}</td>
                  <td class="px-3 py-2.5 text-right text-gray-400 tabular-nums text-xs">{dash(game.batting_2b)}</td>
                  <td class="px-3 py-2.5 text-right text-gray-400 tabular-nums text-xs">{dash(game.batting_3b)}</td>
                  <td class="px-3 py-2.5 text-right text-gray-400 tabular-nums text-xs">{dash(game.batting_hr)}</td>
                  <td class="px-3 py-2.5 text-right text-gray-400 tabular-nums text-xs">{dash(game.batting_rbi)}</td>
                  <td class="px-3 py-2.5 text-right text-gray-400 tabular-nums text-xs">{dash(game.batting_bb)}</td>
                  <td class="px-3 py-2.5 text-right text-gray-400 tabular-nums text-xs">{dash(game.batting_so)}</td>
                  <td class="px-5 py-2.5 text-right font-mono text-white tabular-nums text-xs">{fmtAvg(game.batting_avg)}</td>
                </tr>
              {/each}
            </tbody>
          </table>

        {:else}
          <table class="w-full text-sm">
            <thead>
              <tr class="text-xs text-gray-500 uppercase tracking-wider border-b border-gray-800">
                <th class="text-left  px-5 py-2 font-medium">Date</th>
                <th class="text-left  px-3 py-2 font-medium">Opp</th>
                <th class="text-center px-3 py-2 font-medium">W/L</th>
                <th class="text-left  px-3 py-2 font-medium hidden sm:table-cell">Round</th>
                <th class="text-right px-3 py-2 font-medium">Dec</th>
                <th class="text-right px-3 py-2 font-medium">IP</th>
                <th class="text-right px-3 py-2 font-medium">H</th>
                <th class="text-right px-3 py-2 font-medium">ER</th>
                <th class="text-right px-3 py-2 font-medium">BB</th>
                <th class="text-right px-3 py-2 font-medium">K</th>
                <th class="text-right px-5 py-2 font-medium">ERA</th>
              </tr>
            </thead>
            <tbody>
              {#each gameLogs as game}
                {@const result = gameResult(game)}
                {@const dec    = game.pitching_w  ? 'W'
                               : game.pitching_l  ? 'L'
                               : game.pitching_sv ? 'SV'
                               : '—'}
                {@const decCls = dec === 'W'  ? 'text-green-400 font-bold'
                               : dec === 'L'  ? 'text-red-400 font-bold'
                               : dec === 'SV' ? 'text-blue-400 font-bold'
                               : 'text-gray-600'}
                <tr class="border-b border-gray-800/50 last:border-0 hover:bg-gray-800/40 transition-colors">
                  <td class="px-5 py-2.5 text-gray-400 tabular-nums text-xs">{fmtDate(game.official_date)}</td>
                  <td class="px-3 py-2.5 text-gray-300 font-medium text-xs">{gameOpponent(game)}</td>
                  <td class="px-3 py-2.5 text-center text-xs {result.cls}">{result.label}</td>
                  <td class="px-3 py-2.5 hidden sm:table-cell text-xs text-gray-500">{gameRound(game)}</td>
                  <td class="px-3 py-2.5 text-right text-xs {decCls}">{dec}</td>
                  <td class="px-3 py-2.5 text-right text-gray-400 tabular-nums text-xs">{fmtIp(game.pitching_ip)}</td>
                  <td class="px-3 py-2.5 text-right text-gray-400 tabular-nums text-xs">{dash(game.pitching_h)}</td>
                  <td class="px-3 py-2.5 text-right text-gray-400 tabular-nums text-xs">{dash(game.pitching_er)}</td>
                  <td class="px-3 py-2.5 text-right text-gray-400 tabular-nums text-xs">{dash(game.pitching_bb)}</td>
                  <td class="px-3 py-2.5 text-right text-gray-400 tabular-nums text-xs">{dash(game.pitching_so)}</td>
                  <td class="px-5 py-2.5 text-right font-mono text-white tabular-nums text-xs">{fmtEra(game.pitching_era)}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        {/if}

      </div>
    {/if}
  </section>

</div>