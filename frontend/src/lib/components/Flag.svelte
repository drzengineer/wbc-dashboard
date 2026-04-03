<script lang="ts">
  let {
    country,
    size = "md",
  }: { country: string | null | undefined; size?: "sm" | "md" | "lg" } = $props();

  const upper = $derived(country?.toUpperCase().trim() ?? '');
  
  const threeLetterMap: Record<string, string> = {
    ARG: 'AR', AUS: 'AU', AUT: 'AT', BRA: 'BR', CAN: 'CA',
    CHN: 'CN', COL: 'CO', CUB: 'CU', CZE: 'CZ', DOM: 'DO',
    ESP: 'ES', FRA: 'FR', GBR: 'GB', GER: 'DE', ISR: 'IL',
    ITA: 'IT', JPN: 'JP', KOR: 'KR', MEX: 'MX', NCA: 'NI',
    NED: 'NL', NZL: 'NZ', PAK: 'PK', PAN: 'PA', PHI: 'PH',
    PUR: 'PR', RSA: 'ZA', TPE: 'TW', UGA: 'UG', USA: 'US',
    VEN: 'VE'
  };

  const code = $derived(
    !upper ? null :
    upper.length >= 3 ? threeLetterMap[upper] ?? upper.slice(0, 2) :
    upper
  );

  const dimensions = $derived(
    size === "sm" ? 16 : size === "lg" ? 36 : 24
  );

  const flagUrl = $derived(code ? `https://flagcdn.com/${code.toLowerCase()}.svg` : null);

  let failed = $state(false);
</script>

{#if flagUrl && !failed}
  <img
    src={flagUrl}
    alt={country ?? ''}
    loading="lazy"
    decoding="async"
    style="width: {dimensions}px; aspect-ratio: 3/2; object-fit: cover;"
    onerror={() => failed = true}
  />
{:else if country}
  <span class="text-xs font-semibold tracking-tighter text-white/60">{country}</span>
{/if}