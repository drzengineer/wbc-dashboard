-- assert_innings_pitched_valid.sql
-- Fails if any pitching_ip value is physically impossible.
--
-- Two checks:
--
-- 1. Converted decimal > 18.0 — no single-game pitcher throws 18+ innings.
--    Generous enough to cover any realistic extra-inning outing.
--
-- 2. Raw outs digit >= 3 — the digit after the decimal in baseball IP notation
--    represents outs (0, 1, or 2 only). A value of 3+ is physically impossible.
--    This check is performed on pitching_ip_raw (the original API string) NOT
--    on the converted pitching_ip decimal, because after conversion the only
--    possible fractional parts are 0, 0.3333, and 0.6667 — a fractional
--    component check on the converted value would be dead code that never fires.
--    Example: raw "4.3" → converted 4 + 3/3.0 = 5.0 (looks valid, is wrong).
--    Checking split_part('4.3', '.', 2)::int = 3 correctly catches this.
--
--    nullif(..., '') on the split_part result guards against a trailing-dot value
--    like "4." where split_part returns '' — casting '' to int throws a Postgres
--    runtime error. nullif converts '' to NULL, and NULL >= 3 = NULL (safe false).

select
    game_pk,
    person_id,
    pitching_ip_raw,
    pitching_ip
from {{ ref('player_game_stats') }}
where pitching_ip is not null
  and (
      pitching_ip > 18.0
      -- Check raw string: outs digit must be 0, 1, or 2 only
      -- nullif guards against trailing-dot values like "4." where split_part returns ''
      or (pitching_ip_raw like '%.%'
          and nullif(split_part(pitching_ip_raw, '.', 2), '')::int >= 3)
  )
