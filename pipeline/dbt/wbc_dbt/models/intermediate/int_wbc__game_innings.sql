with source as (

    select * from {{ ref('stg_wbc__schedule') }}

),

-- unnest the innings array into one row per inning per game
innings_unnested as (

    select
        game_pk,
        jsonb_array_elements(innings)   as inning
    from source

),

-- split each inning into two rows: one per side
unpivoted as (

    select
        game_pk,
        ingested_at,
        (inning->>'num')::int           as inning_num,
        inning->>'ordinalNum'           as ordinal_num,
        'away'                          as side,
        away_team_id                    as team_id,
        (inning->'away'->>'hits')::int  as hits,
        (inning->'away'->>'runs')::int  as runs,
        (inning->'away'->>'errors')::int as errors,
        (inning->'away'->>'leftOnBase')::int as left_on_base
    from innings_unnested
    join source using (game_pk)

    union all

    select
        game_pk,
        ingested_at,
        (inning->>'num')::int           as inning_num,
        inning->>'ordinalNum'           as ordinal_num,
        'home'                          as side,
        home_team_id                    as team_id,
        (inning->'home'->>'hits')::int  as hits,
        (inning->'home'->>'runs')::int  as runs,
        (inning->'home'->>'errors')::int as errors,
        (inning->'home'->>'leftOnBase')::int as left_on_base
    from innings_unnested
    join source using (game_pk)

),

final as (

    select
        -- surrogate key
        {{ dbt_utils.generate_surrogate_key(['game_pk', 'team_id', 'inning_num']) }}
                                        as game_inning_team_id,

        -- grain
        game_pk,
        team_id,
        inning_num,
        ordinal_num,
        side,

        -- stats
        hits,
        runs,
        errors,
        left_on_base,

        -- metadata
        ingested_at

    from unpivoted

)

select * from final
