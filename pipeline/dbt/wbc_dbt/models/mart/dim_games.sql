/*
    dim_games
    ---------
    Purpose: Descriptive attributes for every WBC game. This is the "when,
             where, and what kind" context that all three fact tables join to.

    Key design decisions:
        - No measures live here. Scores, hits, runs, errors all belong on
          fct_team_game_stats. A dimension describes; it does not measure.
        - Venue is intentionally kept on this table rather than broken out
          into a dim_venues. The WBC has a small, stable set of venues and
          there are no additional venue attributes (capacity, city coordinates,
          etc.) in the source data to justify a separate table.
        - No dim_date is needed. The WBC is a short tournament and there is
          no calendar-based analysis (fiscal periods, day-of-week trends, etc.)
          that would benefit from a dedicated date spine.
        - season + pool + series_description on this table serve as the
          "tournament dimension" — downstream agg models group by these
          columns rather than joining to a separate dim_tournaments.

    Grain: one row per game_pk
    Source: int_wbc__games
*/

with source as (

    select * from {{ ref('int_wbc__games') }}

),

final as (

    select
        -- primary key
        -- all three fact tables (fct_team_game_stats, fct_player_game_stats,
        -- fct_game_innings) join to this table on game_pk
        game_pk,

        -- game identifiers
        game_guid,

        -- tournament / series context
        -- these three columns together act as the "tournament dimension":
        -- group by season to get full-tournament aggregates
        -- group by season + pool to get pool-level aggregates
        season,
        tournament_round,
        pool_group,
        series_description,
        series_game_number,
        games_in_series,

        -- game classification
        -- game_type = 'F' means the game reached a final result
        game_type,

        -- scheduling
        -- official_date is the canonical date for grouping and display
        -- game_date carries the full timestamptz for exact scheduling
        official_date,
        game_date,
        day_night,

        -- venue
        -- kept here rather than a separate dim_venues (see header note)
        venue_id,
        venue_name,

        -- game flags
        -- these are rarely true in the WBC but surfaced for completeness
        is_tie,
        double_header,
        if_necessary,
        tiebreaker,

        -- WBC mercy rule: 10 run difference after 7 innings, 8 run difference after 5
        case
            when status_code = 'FM' then true
            else false
        end as is_mercy_rule,

        -- metadata
        ingested_at

    from source

)

select * from final
