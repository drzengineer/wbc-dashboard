-- assert_player_game_stats_unique.sql
-- Each player should appear exactly once per game in player_game_stats.
-- A duplicate (game_pk, person_id) pair would mean the same player was
-- unnested twice for the same game — indicating a join or unnesting bug
-- in stg_player_game_stats.
--
-- Note: a player theoretically cannot appear on both home and away sides
-- of the same game. If that ever happened the team_side column would
-- distinguish them, but the (game_pk, person_id) pair would still duplicate
-- and this test would correctly catch it.

select
    game_pk,
    person_id,
    count(*) as cnt
from {{ ref('player_game_stats') }}
group by game_pk, person_id
having count(*) > 1
