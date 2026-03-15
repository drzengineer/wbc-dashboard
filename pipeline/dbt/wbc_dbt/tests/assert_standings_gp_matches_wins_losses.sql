-- assert_standings_gp_matches_wins_losses.sql
-- For every standings row, wins + losses must equal games played.
-- A mismatch means a game was counted in GP but not resolved to a W or L,
-- which would indicate a data integrity problem in the standings derivation.

select
    season,
    round,
    pool_label,
    team_name,
    pool_gp,
    pool_wins,
    pool_losses
from {{ ref('standings') }}
where COALESCE(pool_wins, 0) + COALESCE(pool_losses, 0) != COALESCE(pool_gp, -1)
