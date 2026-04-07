/*
    app_pool_standings
    ------------------
    Purpose: Pre-aggregated pool standings, exactly matching frontend required schema
             Official WBC tiebreaker logic implemented natively in SQL

    Grain: one row per team per pool per season
    Source: fct_team_game_stats

    Design: All aggregation, calculation and sorting happens database side.
            Frontend just selects and displays, zero logic required.
*/

with team_pool_stats as (

    select
        season,
        pool_group,
        team_id,
        team_name,
        team_abbreviation,

        -- Standings metrics
        count(*) as pool_games_played,
        sum(case when is_winner then 1 else 0 end) as pool_wins,
        sum(case when is_winner then 0 else 1 end) as pool_losses,
        sum(run_differential) as pool_run_differential,
        sum(batting_runs) as pool_runs_scored,
        sum(pitching_runs_allowed) as pool_runs_allowed,

        -- Win percentage calculated correctly for NULL handling
        round(
            sum(case when is_winner then 1 else 0 end)::numeric / nullif(count(*), 0),
            3
        ) as pool_win_pct

    from {{ ref('fct_team_game_stats') }}
    where tournament_round in ('Pool Play', 'Round 2')
      and pool_group is not null

    group by 1, 2, 3, 4, 5

),

final as (

    select
        *,

        -- Official WBC Tiebreaker rank columns
        -- Used only for sorting, not returned to frontend
        row_number() over (
            partition by season, pool_group
            order by
                pool_win_pct desc,
                pool_run_differential desc,
                pool_runs_scored desc
        ) as pool_rank

    from team_pool_stats

)

select
    season,
    pool_group,
    team_id,
    team_name,
    team_abbreviation,
    pool_wins,
    pool_losses,
    pool_win_pct,
    pool_run_differential,
    pool_runs_scored,
    pool_runs_allowed

from final

order by
    season desc,
    pool_group,
    pool_rank