/*
    app_game_innings
    ----------------
    Purpose: UI-optimized inning breakdown view, 1 row per game.
             Pivoted inning runs for direct frontend consumption in game cards.
             
    Grain: one row per game
    Source: fct_game_innings + dim_games

    Design: Pivots atomic inning rows into home/away arrays
            This is the ONLY place we pivot inning data into side columns.
*/

with innings as (
    select
        game_pk,
        team_id,
        side,
        inning_num,
        runs,
        hits,
        errors
    from {{ ref('fct_game_innings') }}
),

away_innings as (
    select
        game_pk,
        inning_num,
        runs as away_runs
    from innings
    where side = 'away'
    order by inning_num
),

home_innings as (
    select
        game_pk,
        inning_num,
        runs as home_runs
    from innings
    where side = 'home'
    order by inning_num
),

team_totals as (
    select
        game_pk,
        side,
        sum(runs) as r,
        sum(hits) as h,
        sum(errors) as e
    from innings
    group by game_pk, side
),

pivoted as (
    select
        game_pk,
        -- Pivot away team innings into ordered array
        array_agg(away_runs order by inning_num) as away_innings,
        -- Pivot home team innings into ordered array
        array_agg(home_runs order by inning_num) as home_innings
    from away_innings
    join home_innings using (game_pk, inning_num)
    group by game_pk
),

final as (
    select
        p.game_pk,
        p.away_innings,
        p.home_innings,
        -- RHE totals
        away.r as away_r,
        away.h as away_h,
        away.e as away_e,
        home.r as home_r,
        home.h as home_h,
        home.e as home_e
    from pivoted p
    left join team_totals away on p.game_pk = away.game_pk and away.side = 'away'
    left join team_totals home on p.game_pk = home.game_pk and home.side = 'home'
)

select * from final