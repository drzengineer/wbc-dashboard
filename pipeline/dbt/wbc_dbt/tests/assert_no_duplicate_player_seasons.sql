-- assert_no_duplicate_player_seasons.sql
-- player_tournament_stats must have exactly one row per player per season.
-- Duplicates would cause double-counting on all leaderboard queries.

select
    person_id,
    season,
    count(*) as cnt
from {{ ref('player_tournament_stats') }}
group by person_id, season
having count(*) > 1
