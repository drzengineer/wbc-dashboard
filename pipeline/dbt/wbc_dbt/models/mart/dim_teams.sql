/*
    dim_teams
    ---------
    Purpose: Descriptive attributes for every WBC team. Provides the stable
             "who is this team" context that fact tables reference by team_id.

    Key design decisions:
        - There is no standalone stg_wbc__teams source, so this dimension is
          derived from int_wbc__game_teams. We take the most recently seen
          attributes per team_id across all game appearances.
        - No measures live here. Win/loss records, scores, and all stats
          belong on fct_team_game_stats or the agg tables.
        - division_id / division_name reflect the pool the team played in.
          In the WBC, teams can be in different pools across seasons, so
          these columns represent the most recently seen pool assignment.
          For historical pool analysis, use the division columns on
          fct_team_game_stats which are snapshotted per game.

    Grain: one row per team_id
    Source: int_wbc__game_teams
*/

with source as (

    select * from {{ ref('int_wbc__game_teams') }}

),

/*
    Rank each team's game appearances by ingested_at descending so we can
    take the most recently seen attribute values as the canonical team record.
    This handles cases where team metadata (abbreviation, pool assignment)
    may have been corrected in a later ingestion.
*/
ranked as (

    select
        *,
        row_number() over (
            partition by team_id
            order by ingested_at desc
        )                               as rn

    from source

),

most_recent as (

    select * from ranked where rn = 1

),

final as (

    select
        -- primary key
        -- referenced by fct_team_game_stats (team_id and opponent_team_id)
        -- and by fct_player_game_stats (team_id)
        team_id,

        -- team identity
        team_name,
        team_abbreviation,

        -- pool / division context (most recently seen — see header note)
        division_id,
        division_name,
        league_name,

        -- metadata
        ingested_at

    from most_recent

)

select * from final
