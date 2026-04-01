// src/lib/flags.ts
// Single source of truth for WBC team flag images (flagcdn.com SVGs).
// Import flagHtml() wherever you need {@html flagHtml(abbr, name)}.

export const FLAG_IMAGES: Record<string, string> = {
  ARG: 'https://flagcdn.com/ar.svg',
  AUS: 'https://flagcdn.com/au.svg',
  AUT: 'https://flagcdn.com/at.svg',
  BRA: 'https://flagcdn.com/br.svg',
  CAN: 'https://flagcdn.com/ca.svg',
  CHN: 'https://flagcdn.com/cn.svg',
  COL: 'https://flagcdn.com/co.svg',
  CUB: 'https://flagcdn.com/cu.svg',
  CZE: 'https://flagcdn.com/cz.svg',
  DOM: 'https://flagcdn.com/do.svg',
  ESP: 'https://flagcdn.com/es.svg',
  FRA: 'https://flagcdn.com/fr.svg',
  GBR: 'https://flagcdn.com/gb.svg',
  GER: 'https://flagcdn.com/de.svg',
  ISR: 'https://flagcdn.com/il.svg',
  ITA: 'https://flagcdn.com/it.svg',
  JPN: 'https://flagcdn.com/jp.svg',
  KOR: 'https://flagcdn.com/kr.svg',
  MEX: 'https://flagcdn.com/mx.svg',
  NCA: 'https://flagcdn.com/ni.svg',
  NED: 'https://flagcdn.com/nl.svg',
  NZL: 'https://flagcdn.com/nz.svg',
  PAK: 'https://flagcdn.com/pk.svg',
  PAN: 'https://flagcdn.com/pa.svg',
  PHI: 'https://flagcdn.com/ph.svg',
  PUR: 'https://flagcdn.com/pr.svg',
  RSA: 'https://flagcdn.com/za.svg',
  TPE: 'https://flagcdn.com/tw.svg',
  UGA: 'https://flagcdn.com/ug.svg',
  USA: 'https://flagcdn.com/us.svg',
  VEN: 'https://flagcdn.com/ve.svg',
};

/**
 * Returns an <img> HTML string for use with Svelte's {@html} directive.
 * Falls back to an inline grey placeholder if no match is found.
 * Accepts either a WBC team abbreviation (e.g. "JPN") or a country name
 * (e.g. "Japan") — abbreviation is checked first.
 */
export function flagHtml(abbr?: string | null, name?: string | null): string {
  const src = (abbr && FLAG_IMAGES[abbr]) || (name && FLAG_IMAGES[name]);
  if (src) {
    return `<img src="${src}" alt="${abbr ?? name ?? ''}" class="w-6 h-4 object-cover rounded-sm inline-block align-middle">`;
  }
  return `<span class="w-6 h-4 inline-block bg-gray-700 rounded-sm align-middle"></span>`;
}