<!-- src/routes/games/+page.svelte -->
<script lang="ts">
  import { flagHtml } from '$lib/flags';
  import type { PageData } from './$types';

  const { data }: { data: PageData } = $props();

  // ── All games ────────────────────────────────────────────────
  const allGames = data.games as any[];

  const seasons = $derived(
    [...new Set(allGames.map((g) => g.season))].sort((a, b) => Number(b) - Number(a))
  );

  // Map game_type to human-readable label, preferring DB field if present
  function roundLabel(game: any): string {
    if (game.round_label) return game.round_label;
    const type = game.game_type;
    if (type === 'W') return 'Championship';
    if (type === 'L') return 'Semifinals';
    if (type === 'D') return 'Quarterfinals';
    return game.pool_display ?? type ?? '—';
  }

  // Sort order: knockout rounds first, then pool play
  const ROUND_ORDER: Record<string, number> = {
    'Championship': 0,
    'Semifinals': 1,
    'Quarterfinals': 2,
  };
  function roundOrder(label: string): number {
    return label in ROUND_ORDER ? ROUND_ORDER[label] : 10;
  }

  // ── Filter state ─────────────────────────────────────────────
  let selectedSeason = $state('');
  let selectedRound  = $state('All');

  $effect(() => {
    if (seasons.length && !seasons.includes(selectedSeason)) {
      selectedSeason = seasons[0];
    }
  });

  // Reset round when season changes
  $effect(() => {
    selectedSeason;
    selectedRound = 'All';
  });

  const seasonGames = $derived(
    allGames.filter((g) => g.season === selectedSeason)
  );

  const availableRounds = $derived(() => {
    const labels = [...new Set(seasonGames.map(roundLabel))];
    return labels.sort((a, b) => {
      const diff = roundOrder(a) - roundOrder(b);
      return diff !== 0 ? diff : a.localeCompare(b);
    });
  });

  const filteredGames = $derived(
    selectedRound === 'All'
      ? seasonGames
      : seasonGames.filter((g) => roundLabel(g) === selectedRound)
  );

  // Championship/SF/QF first, then pool play by date desc
  const sortedGames = $derived(
    [...filteredGames].sort((a, b) => {
      const ra = roundOrder(roundLabel(a));
      const rb = roundOrder(roundLabel(b));
      if (ra !== rb) return ra - rb;
      return b.official_date.localeCompare(a.official_date);
    })
  );

  // ── Season-level stats ───────────────────────────────────────
  const totalGames = $derived(seasonGames.length);
  const knockoutCt = $derived(
    seasonGames.filter((g) => ['W', 'L', 'D'].includes(g.game_type)).length
  );
  const mercyCt = $derived(seasonGames.filter((g) => g.is_mercy_rule).length);
  const totalRuns = $derived(
    seasonGames.reduce(
      (sum: number, g: any) => sum + (Number(g.away_score) || 0) + (Number(g.home_score) || 0),
      0
    )
  );

  // ── Helpers ──────────────────────────────────────────────────
  function fmtDate(d: string) {
    return new Date(d + 'T00:00:00').toLocaleDateString('en-US', {
      month: 'short', day: 'numeric', year: 'numeric',
    });
  }

  function roundBadgeClass(label: string): string {
    if (label === 'Championship') return 'text-yellow-400 border-yellow-500/30 bg-yellow-500/10';
    if (label === 'Semifinals')   return 'text-purple-400 border-purple-500/30 bg-purple-500/10';
    if (label === 'Quarterfinals') return 'text-blue-400 border-blue-500/30 bg-blue-500/10';
    return 'text-gray-400 border-gray-700 bg-gray-800';
  }
</script>

<div class="space-y-8">

  <!-- Page header -->
  <div>
    <h1 class="text-2xl font-bold text-white tracking-tight">Games</h1>
  </div>

  <!-- Season tabs -->
  <div class="flex gap-1 bg-gray-900 border border-gray-800 rounded-lg p-1 w-fit">
    {#each seasons as season}
      <button
        type="button"
        onclick={() => selectedSeason = season}
        class="px-3 py-1 rounded-md text-sm font-medium transition-colors
          {selectedSeason === season
            ? 'bg-blue-600 text-white'
            : 'text-gray-400 hover:text-white hover:bg-gray-800'}"
      >
        {season}
      </button>
    {/each}
  </div>

  <!-- Season stat cards -->
  <div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
    <div class="bg-gray-900 border border-gray-800 rounded-xl px-4 py-4">
      <p class="text-xs text-gray-500 uppercase tracking-wider mb-1">Games Played</p>
      <p class="text-2xl font-bold text-white tabular-nums">{totalGames}</p>
    </div>
    <div class="bg-gray-900 border border-gray-800 rounded-xl px-4 py-4">
      <p class="text-xs text-gray-500 uppercase tracking-wider mb-1">Knockout Games</p>
      <p class="text-2xl font-bold text-white tabular-nums">{knockoutCt}</p>
    </div>
    <div class="bg-gray-900 border border-gray-800 rounded-xl px-4 py-4">
      <p class="text-xs text-gray-500 uppercase tracking-wider mb-1">Total Runs</p>
      <p class="text-2xl font-bold text-white tabular-nums">{totalRuns}</p>
    </div>
    <div class="bg-gray-900 border border-gray-800 rounded-xl px-4 py-4">
      <p class="text-xs text-gray-500 uppercase tracking-wider mb-1">Mercy Rule</p>
      <p class="text-2xl font-bold tabular-nums {mercyCt > 0 ? 'text-orange-400' : 'text-white'}">{mercyCt}</p>
    </div>
  </div>

  <!-- Round filter pills -->
  <div class="flex flex-wrap gap-2 items-center">
    <span class="text-xs text-gray-500 mr-1">Round:</span>
    <button
      type="button"
      onclick={() => selectedRound = 'All'}
      class="px-3 py-1 rounded-full text-xs font-medium border transition-colors
        {selectedRound === 'All'
          ? 'bg-blue-600 border-blue-600 text-white'
          : 'border-gray-700 text-gray-400 hover:text-white hover:border-gray-500'}"
    >
      All
    </button>
    {#each availableRounds() as round}
      <button
        type="button"
        onclick={() => selectedRound = round}
        class="px-3 py-1 rounded-full text-xs font-medium border transition-colors
          {selectedRound === round
            ? 'bg-blue-600 border-blue-600 text-white'
            : 'border-gray-700 text-gray-400 hover:text-white hover:border-gray-500'}"
      >
        {round}
      </button>
    {/each}
  </div>

  <!-- Result count -->
  <p class="text-xs text-gray-500 -mt-4">
    {filteredGames.length} game{filteredGames.length === 1 ? '' : 's'}
    {selectedRound !== 'All' ? `· ${selectedRound}` : ''}
    · {selectedSeason} WBC
  </p>

  <!-- Game cards -->
  {#if sortedGames.length === 0}
    <div class="bg-gray-900 border border-gray-800 rounded-xl px-6 py-12 text-center">
      <p class="text-gray-500 text-sm">No completed games for this selection.</p>
    </div>
  {:else}
    <div class="flex flex-col gap-3">
      {#each sortedGames as game}
        {@const label   = roundLabel(game)}
        {@const isChamp = game.game_type === 'W'}
        {@const awayWon = !!game.away_is_winner}
        {@const homeWon = !!game.home_is_winner}

        <div class="bg-gray-900 border rounded-xl px-5 py-4 transition-colors hover:border-gray-600
          {isChamp ? 'border-yellow-500/40 shadow shadow-yellow-500/5' : 'border-gray-800'}">

          <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">

            <!-- Score block -->
            <div class="flex items-center gap-4 flex-wrap">

              <!-- Away team -->
              <div class="flex items-center gap-2">
                <span class="inline-block w-6 shrink-0">{@html flagHtml(game.away_team_abbreviation, game.away_team_name)}</span>
                <span class="text-sm font-semibold w-9 text-right shrink-0
                  {awayWon ? 'text-white' : 'text-gray-500'}">
                  {game.away_team_abbreviation ?? game.away_team_name ?? '—'}
                </span>
                <span class="text-2xl font-bold tabular-nums w-7 text-right shrink-0
                  {awayWon ? (isChamp ? 'text-yellow-400' : 'text-white') : 'text-gray-500'}">
                  {game.away_score ?? '—'}
                </span>
              </div>

              <span class="text-gray-700 select-none">–</span>

              <!-- Home team -->
              <div class="flex items-center gap-2">
                <span class="text-2xl font-bold tabular-nums w-7 shrink-0
                  {homeWon ? (isChamp ? 'text-yellow-400' : 'text-white') : 'text-gray-500'}">
                  {game.home_score ?? '—'}
                </span>
                <span class="text-sm font-semibold w-9 shrink-0
                  {homeWon ? 'text-white' : 'text-gray-500'}">
                  {game.home_team_abbreviation ?? game.home_team_name ?? '—'}
                </span>
                <span class="inline-block w-6 shrink-0">{@html flagHtml(game.home_team_abbreviation, game.home_team_name)}</span>
              </div>

              <!-- Badges -->
              {#if game.is_mercy_rule}
                <span class="text-xs bg-orange-500/20 text-orange-400 border border-orange-500/30 rounded px-1.5 py-0.5 shrink-0">
                  Mercy
                </span>
              {/if}
              {#if isChamp && (awayWon || homeWon)}
                <span class="text-base shrink-0">🏆</span>
              {/if}

            </div>

            <!-- Round + date + venue -->
            <div class="flex flex-wrap items-center gap-2 text-xs shrink-0">
              <span class="border rounded px-2 py-0.5 font-medium {roundBadgeClass(label)}">
                {label}
              </span>
              <span class="text-gray-500">{fmtDate(game.official_date)}</span>
              {#if game.venue_name}
                <span class="text-gray-600 hidden md:inline">{game.venue_name}</span>
              {/if}
            </div>

          </div>

          <!-- Venue on mobile -->
          {#if game.venue_name}
            <p class="text-xs text-gray-600 mt-2 md:hidden">{game.venue_name}</p>
          {/if}

        </div>
      {/each}
    </div>
  {/if}

</div>