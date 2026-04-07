/*
    fct_game_innings
    ----------------
    Purpose: Atomic inning-level fact table. One row per team per inning per game.
             Keys and measures only — no attributes pulled from dimension tables.
             All descriptive context (team name, game date, venue, etc.) is
             joined in at the agg layer or by the frontend via dim joins.

    Source: int_wbc__game_innings (only)
    Grain: game_pk + team_id + inning_num
*/

with source as (

    select * from {{ ref('int_wbc__game_innings') }}

),

final as (

    select
        -- surrogate key
        s.game_inning_team_id,

        -- foreign keys
        -- all descriptive attributes for these keys are joined at the agg layer
        s.game_pk,      -- → dim_games
        s.team_id,      -- → dim_teams

        s.side,

        -- inning descriptor (not a measure but intrinsic to the grain)
        s.inning_num,
        s.ordinal_num,

        -- inning measures
        s.runs,
        s.hits,
        s.errors,
        s.left_on_base,

        -- metadata
        s.ingested_at

    from source s

)

select * from final
