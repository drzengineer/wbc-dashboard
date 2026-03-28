<script lang="ts">
  const { data } = $props();
</script>

<h1 class="text-2xl font-bold mb-6">Players</h1>

<div class="flex gap-6">
  <p class="text-gray-500 text-sm">{data.batters.length} batters loaded — UI coming Day 10</p>
  <p class="text-gray-500 text-sm">{data.pitchers.length} pitchers loaded — UI coming Day 10</p>
</div>