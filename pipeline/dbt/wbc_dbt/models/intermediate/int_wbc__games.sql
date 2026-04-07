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
        trim(both '"' from description)                        as pool_raw,
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
        trim(both '"' from status_code)                        as status_code,

        -- metadata
        ingested_at

    from source

),

classified as (

    select
        *,

        /*
            tournament_round
            ----------------
            F = Pool Play
            D = Quarterfinal in 2023+; Round 2 in all prior years
            L = Semifinal
            W = Championship
        */
        case
            when game_type = 'F'                        then 'Pool Play'
            when game_type = 'D' and season < 2023      then 'Round 2'
            when game_type = 'D' and season >= 2023     then 'Quarterfinals'
            when game_type = 'L'                        then 'Semifinals'
            when game_type = 'W'                        then 'Championship'
        end                                                     as tournament_round,

        /*
            pool_group
            ----------
            For pool play (F) and pre-2023 round 2 (D), extract the lettered
            or numbered pool from the raw description field. The description
            field is inconsistent across years so we apply patterns in
            specificity order.

            First-round pools use letters A–F.
            Pre-2023 second-round pools use numbers 1–2.
            Knockout rounds get their round name as the group.

            Pattern notes:
              - "WBC Pool A: Seoul - Game 2"    → Pool A
              - "WBC Pool A Game 3"             → Pool A
              - "Pool A - Game 6"               → Pool A
              - "Pool A Game 3"                 → Pool A
              - "Pool A, Tokyo Dome"            → Pool A
              - "Pool A"                        → Pool A
              - "Pool 1 - Game 5"               → Pool 1
              - "Pool 2, Hiram Bithorn Stadium" → Pool 2
              - "WBC Pool 1 Game 3"             → Pool 1
        */
        case
            when game_type = 'F'
                then 'Pool ' || upper(
                    substring(pool_raw from '(?i)pool\s+([A-F])(?:\s|:|,|$|-)')
                )
            when game_type = 'D' and season < 2023
                then 'Pool ' || upper(
                    substring(pool_raw from '(?i)pool\s+([A-F1-2])(?:\s|:|,|$|-)')
                )
            when game_type = 'D' and season >= 2023    then 'Quarterfinals'
            when game_type = 'L'                        then 'Semifinals'
            when game_type = 'W'                        then 'Championship'
        end                                                     as pool_group

    from final

)

select * from classified
