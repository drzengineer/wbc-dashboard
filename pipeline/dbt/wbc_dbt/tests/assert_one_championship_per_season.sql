-- assert_one_championship_per_season.sql
-- Every completed season must have exactly one Championship game (game_type = 'W').
-- Returns seasons with 0 or 2+ championship games — both are data problems.
-- Note: 2026 will legitimately return here until the final is played,
-- so a failure on the active season during pool play is expected behavior.

select
    season,
    count(*) as championship_games
from {{ ref('game_results') }}
where game_type = 'W'
  and abstract_game_state = 'Final'
group by season
having count(*) != 1
