-- ============================================================
-- standings
-- One row per team per season per round
-- Source: game_results
--
-- Covers:
--   round 1 (game_type = 'F'): first-round pools A/B/C/D — all seasons
--   round 2 (game_type = 'D'): second-round pools — 2006-2017 only
--     2006/2009/2013: Pool 1, Pool 2
--     2017: Pool E, Pool F
-- Excludes:
--   2023/2026 quarterfinals (game_type = 'D', pool_label = NULL) — single elim, no standings
--
-- Key columns:
--   round: 1 = first-round pool play, 2 = second-round pool play
--   pool_label: raw identifier (A/B/C/D/1/2/E/F)
--   pool_display: human-readable e.g. 'Pool A', 'Second Round Pool 1'
--   is_champion: true for the season's championship game winner
-- ============================================================

with games as (
    select * from {{ ref('game_results') }}
    where
        abstract_game_state = 'Final'
        -- include first-round pool play (all seasons)
        -- include second-round pools (2006-2017) where pool_label is not null
        -- exclude 2023/2026 quarterfinals where pool_label is null
        and (
            game_type = 'F'
            or (game_type = 'D' and pool_label is not null)
        )
),

away_records as (
    select
        season,
        round_order,
        pool_label,
        pool_display,
        tournament_format,
        away_team_name          as team_name,
        away_team_abbreviation  as team_abbreviation,
        count(*)                as gp,
        -- explicit = true/false rather than implicit boolean truthiness
        -- guards against null away_is_winner on Final games with API lag
        -- (null winner → gp++ but 0 wins AND 0 losses, caught by standings GP test)
        sum(case when away_is_winner = true  then 1 else 0 end)     as wins,
        sum(case when away_is_winner = false then 1 else 0 end)     as losses,
        sum(coalesce(away_score, 0)) as runs_scored,
        sum(coalesce(home_score, 0)) as runs_allowed
    from games
    group by season, round_order, pool_label, pool_display, tournament_format,
             away_team_name, away_team_abbreviation
),

home_records as (
    select
        season,
        round_order,
        pool_label,
        pool_display,
        tournament_format,
        home_team_name          as team_name,
        home_team_abbreviation  as team_abbreviation,
        count(*)                as gp,
        sum(case when home_is_winner = true  then 1 else 0 end)     as wins,
        sum(case when home_is_winner = false then 1 else 0 end)     as losses,
        sum(coalesce(home_score, 0)) as runs_scored,
        sum(coalesce(away_score, 0)) as runs_allowed
    from games
    group by season, round_order, pool_label, pool_display, tournament_format,
             home_team_name, home_team_abbreviation
),

combined as (
    select * from away_records
    union all
    select * from home_records
),

pool_totals as (
    select
        season,
        round_order                                 as round,
        pool_label,
        pool_display,
        tournament_format,
        team_name,
        team_abbreviation,
        sum(gp)                                     as pool_gp,
        sum(wins)                                   as pool_wins,
        sum(losses)                                 as pool_losses,
        sum(runs_scored)                            as pool_runs_scored,
        sum(runs_allowed)                           as pool_runs_allowed,
        sum(runs_scored) - sum(runs_allowed)        as pool_run_differential,
        round(
            sum(wins)::numeric / nullif(sum(gp), 0), 3
        )                                           as pool_win_pct
    from combined
    group by season, round_order, pool_label, pool_display, tournament_format,
             team_name, team_abbreviation
),

champions as (
    select
        season,
        winning_team_name           as team_name,
        winning_team_abbreviation   as team_abbreviation,
        true                        as is_champion
    from {{ ref('game_results') }}
    where game_type = 'W'
      and abstract_game_state = 'Final'
    -- Note: if winning_team_abbreviation is NULL due to known API lag
    -- (score populates before winner flags on live games), this CTE
    -- produces a null-abbreviation row. The left join below won't match
    -- on null = null, so is_champion = false for all teams that season.
    -- This is correct behavior — don't mark a champion until API confirms it.
    -- Re-ingestion after the game resolves this automatically.
)

select
    pt.season,
    pt.round,
    pt.pool_label,
    pt.pool_display,
    pt.tournament_format,
    pt.team_name,
    pt.team_abbreviation,
    pt.pool_gp,
    pt.pool_wins,
    pt.pool_losses,
    pt.pool_run_differential,
    pt.pool_runs_scored,
    pt.pool_runs_allowed,
    pt.pool_win_pct,
    coalesce(c.is_champion, false)  as is_champion
from pool_totals pt
left join champions c
    on pt.season = c.season
    and pt.team_abbreviation = c.team_abbreviation
order by season, round, pool_label, pool_win_pct desc, pool_run_differential desc