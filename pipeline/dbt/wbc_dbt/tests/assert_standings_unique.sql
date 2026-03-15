-- assert_standings_unique.sql
-- Each team should appear exactly once per season per round per pool.
-- A duplicate (season, round, pool_label, team_abbreviation) means the
-- home/away union-and-aggregate in standings.sql produced duplicate groups —
-- which would cause double-counting of wins, losses, and run totals.

select
    season,
    round,
    pool_label,
    team_abbreviation,
    count(*) as cnt
from {{ ref('standings') }}
group by season, round, pool_label, team_abbreviation
having count(*) > 1
