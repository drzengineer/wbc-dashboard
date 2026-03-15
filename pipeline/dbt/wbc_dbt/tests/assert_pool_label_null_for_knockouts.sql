-- assert_pool_label_null_for_knockouts.sql
-- Semifinals and finals should never have a pool_label — they are not pool games.
-- Quarterfinals (game_type = 'D') in 2023+ are also single-elimination and
-- should have null pool_label. In 2006-2017, D-type games ARE second round pools
-- and legitimately have a pool_label, so those are excluded from this check.

select
    game_pk,
    season,
    game_type,
    round_label,
    pool_label,
    description
from {{ ref('game_results') }}
where game_type in ('L', 'W')
  and pool_label is not null

union all

select
    game_pk,
    season,
    game_type,
    round_label,
    pool_label,
    description
from {{ ref('game_results') }}
where game_type = 'D'
  and season >= 2023
  and pool_label is not null
