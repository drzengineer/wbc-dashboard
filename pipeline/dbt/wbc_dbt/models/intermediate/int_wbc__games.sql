with source as (

    select * from {{ ref('stg_wbc__schedule') }}

),

final as (

    select
        -- primary key
        game_pk,

        -- identifiers
        trim(both '"' from game_guid)                           as game_guid,
        venue_id,
        trim(both '"' from venue_name)                         as venue_name,

        -- game classification
        trim(both '"' from game_type)                          as game_type,
        trim(both '"' from season)::int                        as season,
        trim(both '"' from description)                        as pool,
        trim(both '"' from series_description)                 as series_description,
        series_game_number,
        games_in_series,

        -- scheduling
        trim(both '"' from game_date)::timestamptz             as game_date,
        trim(both '"' from official_date)::date                as official_date,
        trim(both '"' from day_night)                          as day_night,

        -- game flags
        is_tie,
        trim(both '"' from double_header)                      as double_header,
        trim(both '"' from if_necessary)                       as if_necessary,
        trim(both '"' from tiebreaker)                         as tiebreaker,

        -- metadata
        ingested_at

    from source

)

select * from final
