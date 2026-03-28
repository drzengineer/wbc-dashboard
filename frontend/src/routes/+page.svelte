<script lang="ts">
  const { data } = $props();
</script>

<h1 class="text-2xl font-bold mb-6">Dashboard</h1>

<div class="grid grid-cols-2 gap-6">
  <section>
    <h2 class="text-lg font-semibold mb-3 text-gray-300">Recent Games</h2>
    <p class="text-gray-500 text-sm">{data.recentGames.length} games loaded — UI coming Day 10</p>
  </section>

  <section>
    <h2 class="text-lg font-semibold mb-3 text-gray-300">Standings</h2>
    <p class="text-gray-500 text-sm">{data.standings.length} rows loaded — UI coming Day 10</p>
  </section>
</div>