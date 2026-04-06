/*
    int_wbc__players
    ----------------
    Purpose: Deduplicate the raw players staging table so that dim_players
             has a single, trustworthy spine to build from.

    Why this exists in int and not mart:
        - Every stg model should have a downstream int model to keep the
          lineage graph clean and prevent orphaned staging tables.
        - Deduplication is a transformation concern, not a business concern,
          so it belongs here rather than in the mart layer.

    Source: stg_wbc__players
    Grain: one row per player_id (the most recently ingested record wins)
*/

with source as (

    select * from {{ ref('stg_wbc__players') }}

),

/*
    Deduplicate using DISTINCT ON so that if the same player_id was ingested
    multiple times (e.g. pipeline reruns, API re-pulls), we keep only the
    most recent record. This is safe because the stg layer has already cast
    all types and renamed all columns.
*/
deduped as (

    select distinct on (player_id)
        *
    from source
    order by
        player_id,
        ingested_at desc

),

final as (

    select
        -- primary key
        player_id,

        -- player status
        active,
        is_verified,
        gender,

        -- name fields
        -- full_name is the canonical display name used across all mart models
        full_name,
        first_name,
        middle_name,
        last_name,
        use_name,
        use_last_name,
        boxscore_name,

        -- biographical information
        birth_date::date                    as birth_date,
        birth_city,
        birth_country,
        mlb_debut_date::date                as mlb_debut_date,

        -- physical attributes
        height,
        weight,
        current_age,

        -- batting / pitching handedness
        bat_side_code,
        pitch_hand_code,

        -- primary jersey number from the player bio API
        -- note: per-game jersey numbers live on fct_player_game_stats
        -- because players can wear different numbers across tournaments
        primary_number,

        -- primary position from the player bio API
        -- note: per-game positions live on fct_player_game_stats
        -- because players can play multiple positions across games
        primary_position_code,
        primary_position_name,
        primary_position_type,
        primary_position_abbreviation,

        -- strike zone measurements (used by pitching analysis)
        strike_zone_top,
        strike_zone_bottom,

        -- team association at time of ingestion
        -- this is a snapshot, not an SCD — use with caution for historical queries
        current_team_id,

        -- metadata
        ingested_at

    from deduped

)

select * from final
