<!-- src/routes/players/+page.svelte -->
<script lang="ts">
  import type { PageData } from './$types';

  const { data }: { data: PageData } = $props();

  const allBatters  = data.batters  as any[];
  const allPitchers = data.pitchers as any[];

  // ── Season filter ────────────────────────────────────────────
  const seasons = $derived(
    [...new Set([...allBatters, ...allPitchers].map((p) => p.season))]
      .sort((a, b) => Number(b) - Number(a))
  );

  let selectedSeason = $state('');

  $effect(() => {
    if (seasons.length && !seasons.includes(selectedSeason)) {
      selectedSeason = seasons[0];
    }
  });

  // ── Tab state: which side + which stat ──────────────────────
  type Side = 'batting' | 'pitching';
  type BattingStat  = 'avg' | 'hr' | 'rbi' | 'ops' | 'sb';
  type PitchingStat = 'era' | 'so' | 'ip'  | 'w'   | 'sv';

  let side        = $state<Side>('batting');
  let battingStat  = $state<BattingStat>('avg');
  let pitchingStat = $state<PitchingStat>('era');

  // ── Filtered pools ───────────────────────────────────────────
  const batters  = $derived(allBatters.filter((p) => p.season === selectedSeason));
  const pitchers = $derived(allPitchers.filter((p) => p.season === selectedSeason));

  // ── Batting leaderboard ──────────────────────────────────────
  const BATTING_STATS: { key: BattingStat; label: string; col: string; fmt: (v: any) => string; minAB: number }[] = [
    { key: 'avg', label: 'AVG', col: 'season_batting_avg', fmt: fmtAvg, minAB: 5 },
    { key: 'hr',  label: 'HR',  col: 'season_batting_hr',  fmt: (v) => v ?? '—', minAB: 0 },
    { key: 'rbi', label: 'RBI', col: 'season_batting_rbi', fmt: (v) => v ?? '—', minAB: 0 },
    { key: 'ops', label: 'OPS', col: 'season_batting_ops', fmt: fmtAvg, minAB: 5 },
    { key: 'sb',  label: 'SB',  col: 'season_batting_sb',  fmt: (v) => v ?? '—', minAB: 0 },
  ];

  const activeBattingStat = $derived(BATTING_STATS.find((s) => s.key === battingStat)!);

  const battingLeaders = $derived(() => {
    const def = activeBattingStat;
    return [...batters]
      .filter((p) => {
        if (def.minAB > 0 && (Number(p.season_batting_ab) || 0) < def.minAB) return false;
        return p[def.col] != null;
      })
      .sort((a, b) => {
        // ERA/rate stats: ascending; counting stats: descending
        if (def.key === 'avg' || def.key === 'ops') {
          return Number(b[def.col]) - Number(a[def.col]);
        }
        return Number(b[def.col]) - Number(a[def.col]);
      })
      .slice(0, 20);
  });

  // ── Pitching leaderboard ─────────────────────────────────────
  const PITCHING_STATS: { key: PitchingStat; label: string; col: string; fmt: (v: any) => string; asc: boolean; minIP: number }[] = [
    { key: 'era', label: 'ERA', col: 'season_pitching_era', fmt: fmtEra, asc: true,  minIP: 3 },
    { key: 'so',  label: 'K',   col: 'season_pitching_so',  fmt: (v) => v ?? '—', asc: false, minIP: 0 },
    { key: 'ip',  label: 'IP',  col: 'season_pitching_ip',  fmt: fmtIp, asc: false, minIP: 0 },
    { key: 'w',   label: 'W',   col: 'season_pitching_w',   fmt: (v) => v ?? '—', asc: false, minIP: 0 },
    { key: 'sv',  label: 'SV',  col: 'season_pitching_sv',  fmt: (v) => v ?? '—', asc: false, minIP: 0 },
  ];

  const activePitchingStat = $derived(PITCHING_STATS.find((s) => s.key === pitchingStat)!);

  const pitchingLeaders = $derived(() => {
    const def = activePitchingStat;
    return [...pitchers]
      .filter((p) => {
        if (def.minIP > 0 && (Number(p.season_pitching_ip) || 0) < def.minIP) return false;
        return p[def.col] != null;
      })
      .sort((a, b) =>
        def.asc
          ? Number(a[def.col]) - Number(b[def.col])
          : Number(b[def.col]) - Number(a[def.col])
      )
      .slice(0, 20);
  });

  // ── Formatters ───────────────────────────────────────────────
  function fmtAvg(val: any): string {
    const n = Number(val);
    if (isNaN(n)) return '—';
    return n === 1 ? '1.000' : n === 0 ? '.000' : n.toFixed(3).replace('0.', '.');
  }

  function fmtEra(val: any): string {
    const n = Number(val);
    if (isNaN(n)) return '—';
    return n.toFixed(2);
  }

  function fmtIp(val: any): string {
    const n = Number(val);
    if (isNaN(n)) return '—';
    return n.toFixed(1);
  }

  function countryFlag(abbr?: string): string {
    const FLAGS: Record<string, string> = {
      'USA': 'us', 'DOM': 'do', 'PUR': 'pr', 'JPN': 'jp', 'CUB': 'cu',
      'VEN': 've', 'MEX': 'mx', 'KOR': 'kr', 'NED': 'nl', 'ITA': 'it',
      'AUS': 'au', 'CAN': 'ca', 'PAN': 'pa', 'TPE': 'tw', 'CHN': 'cn',
      'NCA': 'ni', 'COL': 'co', 'ISR': 'il', 'GBR': 'gb', 'CZE': 'cz',
      'ESP': 'es', 'RSA': 'za', 'NZL': 'nz', 'BRA': 'br', 'FRA': 'fr',
      'GER': 'de', 'AUT': 'at', 'PHI': 'ph', 'PAK': 'pk', 'UGA': 'ug',
      'ARG': 'ar',
    };
    const code = abbr ? FLAGS[abbr] : null;
    if (!code) return '<span class="w-[20px] h-[14px] inline-block bg-gray-700 rounded"></span>';
    return `<img src="https://flagcdn.com/${code}.svg" alt="${abbr}" class="w-[20px] h-[14px] rounded-sm object-cover">`;
  }
</script>

<div class="space-y-8">

  <!-- Header -->
  <div>
    <h1 class="text-2xl font-bold text-white tracking-tight">Players</h1>
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

  <!-- Batting / Pitching toggle -->
  <div class="flex gap-1 bg-gray-900 border border-gray-800 rounded-lg p-1 w-fit">
    <button
      type="button"
      onclick={() => side = 'batting'}
      class="px-4 py-1.5 rounded-md text-sm font-medium transition-colors
        {side === 'batting' ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-white hover:bg-gray-800'}"
    >
      Batting
    </button>
    <button
      type="button"
      onclick={() => side = 'pitching'}
      class="px-4 py-1.5 rounded-md text-sm font-medium transition-colors
        {side === 'pitching' ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-white hover:bg-gray-800'}"
    >
      Pitching
    </button>
  </div>

  {#if side === 'batting'}

    <!-- Batting stat tabs -->
    <div class="flex gap-1 flex-wrap">
      {#each BATTING_STATS as stat}
        <button
          type="button"
          onclick={() => battingStat = stat.key}
          class="px-3 py-1 rounded-full text-xs font-medium border transition-colors
            {battingStat === stat.key
              ? 'bg-blue-600 border-blue-600 text-white'
              : 'border-gray-700 text-gray-400 hover:text-white hover:border-gray-500'}"
        >
          {stat.label}
        </button>
      {/each}
    </div>

    <!-- Batting leaderboard -->
    <div class="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
      <div class="px-5 py-3 border-b border-gray-800 flex items-center justify-between">
        <span class="text-sm font-semibold text-white">
          {activeBattingStat.label} Leaders
          {activeBattingStat.minAB > 0 ? `(min ${activeBattingStat.minAB} AB)` : ''}
        </span>
        <span class="text-xs text-gray-500">{selectedSeason} WBC</span>
      </div>

      {#if battingLeaders().length === 0}
        <p class="px-5 py-8 text-sm text-gray-500 text-center">No data for this selection.</p>
      {:else}
        <table class="w-full text-sm">
          <thead>
            <tr class="text-xs text-gray-500 uppercase tracking-wider border-b border-gray-800">
              <th class="text-left px-5 py-2 font-medium w-8">#</th>
              <th class="text-left px-3 py-2 font-medium">Player</th>
              <th class="text-left px-3 py-2 font-medium hidden sm:table-cell">Country</th>
              <th class="text-right px-3 py-2 font-medium">GP</th>
              <th class="text-right px-3 py-2 font-medium">AB</th>
              <th class="text-right px-3 py-2 font-medium">H</th>
              <th class="text-right px-3 py-2 font-medium">HR</th>
              <th class="text-right px-3 py-2 font-medium">RBI</th>
              <th class="text-right px-5 py-2 font-medium text-blue-400">{activeBattingStat.label}</th>
            </tr>
          </thead>
          <tbody>
            {#each battingLeaders() as player, i}
              <tr class="border-b border-gray-800/50 last:border-0 hover:bg-gray-800/40 transition-colors">
                <td class="px-5 py-3 text-gray-500 tabular-nums text-xs">{i + 1}</td>
                <td class="px-3 py-3">
                  <a
                    href="/players/{player.person_id}"
                    class="font-medium text-white hover:text-blue-400 transition-colors"
                  >
                    {player.full_name}
                  </a>
                  <span class="text-xs text-gray-500 ml-1.5">{player.position_type ?? ''}</span>
                </td>
                <td class="px-3 py-3 hidden sm:table-cell">
                  <div class="flex items-center gap-1.5">
                    <span>{@html countryFlag(player.team_abbreviation)}</span>
                    <span class="text-gray-400 text-xs">{player.team_abbreviation ?? '—'}</span>
                  </div>
                </td>
                <td class="px-3 py-3 text-right text-gray-400 tabular-nums">{player.games_played ?? '—'}</td>
                <td class="px-3 py-3 text-right text-gray-400 tabular-nums">{player.season_batting_ab ?? '—'}</td>
                <td class="px-3 py-3 text-right text-gray-400 tabular-nums">{player.season_batting_h ?? '—'}</td>
                <td class="px-3 py-3 text-right text-gray-400 tabular-nums">{player.season_batting_hr ?? '—'}</td>
                <td class="px-3 py-3 text-right text-gray-400 tabular-nums">{player.season_batting_rbi ?? '—'}</td>
                <td class="px-5 py-3 text-right font-bold tabular-nums text-white">
                  {activeBattingStat.fmt(player[activeBattingStat.col])}
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      {/if}
    </div>

  {:else}

    <!-- Pitching stat tabs -->
    <div class="flex gap-1 flex-wrap">
      {#each PITCHING_STATS as stat}
        <button
          type="button"
          onclick={() => pitchingStat = stat.key}
          class="px-3 py-1 rounded-full text-xs font-medium border transition-colors
            {pitchingStat === stat.key
              ? 'bg-blue-600 border-blue-600 text-white'
              : 'border-gray-700 text-gray-400 hover:text-white hover:border-gray-500'}"
        >
          {stat.label}
        </button>
      {/each}
    </div>

    <!-- Pitching leaderboard -->
    <div class="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
      <div class="px-5 py-3 border-b border-gray-800 flex items-center justify-between">
        <span class="text-sm font-semibold text-white">
          {activePitchingStat.label} Leaders
          {activePitchingStat.minIP > 0 ? `(min ${activePitchingStat.minIP} IP)` : ''}
        </span>
        <span class="text-xs text-gray-500">{selectedSeason} WBC</span>
      </div>

      {#if pitchingLeaders().length === 0}
        <p class="px-5 py-8 text-sm text-gray-500 text-center">No data for this selection.</p>
      {:else}
        <table class="w-full text-sm">
          <thead>
            <tr class="text-xs text-gray-500 uppercase tracking-wider border-b border-gray-800">
              <th class="text-left px-5 py-2 font-medium w-8">#</th>
              <th class="text-left px-3 py-2 font-medium">Player</th>
              <th class="text-left px-3 py-2 font-medium hidden sm:table-cell">Country</th>
              <th class="text-right px-3 py-2 font-medium">GP</th>
              <th class="text-right px-3 py-2 font-medium">W</th>
              <th class="text-right px-3 py-2 font-medium">L</th>
              <th class="text-right px-3 py-2 font-medium">SV</th>
              <th class="text-right px-3 py-2 font-medium">K</th>
              <th class="text-right px-3 py-2 font-medium">IP</th>
              <th class="text-right px-5 py-2 font-medium text-blue-400">{activePitchingStat.label}</th>
            </tr>
          </thead>
          <tbody>
            {#each pitchingLeaders() as player, i}
              <tr class="border-b border-gray-800/50 last:border-0 hover:bg-gray-800/40 transition-colors">
                <td class="px-5 py-3 text-gray-500 tabular-nums text-xs">{i + 1}</td>
                <td class="px-3 py-3">
                  <a
                    href="/players/{player.person_id}"
                    class="font-medium text-white hover:text-blue-400 transition-colors"
                  >
                    {player.full_name}
                  </a>
                </td>
                <td class="px-3 py-3 hidden sm:table-cell">
                  <div class="flex items-center gap-1.5">
                    <span>{@html countryFlag(player.team_abbreviation)}</span>
                    <span class="text-gray-400 text-xs">{player.team_abbreviation ?? '—'}</span>
                  </div>
                </td>
                <td class="px-3 py-3 text-right text-gray-400 tabular-nums">{player.games_played ?? '—'}</td>
                <td class="px-3 py-3 text-right text-gray-400 tabular-nums">{player.season_pitching_w ?? '—'}</td>
                <td class="px-3 py-3 text-right text-gray-400 tabular-nums">{player.season_pitching_l ?? '—'}</td>
                <td class="px-3 py-3 text-right text-gray-400 tabular-nums">{player.season_pitching_sv ?? '—'}</td>
                <td class="px-3 py-3 text-right text-gray-400 tabular-nums">{player.season_pitching_so ?? '—'}</td>
                <td class="px-3 py-3 text-right text-gray-400 tabular-nums">{fmtIp(player.season_pitching_ip)}</td>
                <td class="px-5 py-3 text-right font-bold tabular-nums text-white">
                  {activePitchingStat.fmt(player[activePitchingStat.col])}
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      {/if}
    </div>

  {/if}

</div>