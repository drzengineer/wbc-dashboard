with source as (
    select game_pk, data, ingested_at
    from {{ source('raw', 'schedule') }}
),

flattened as (
    select
        game_pk,
        (data->>'season')::int                                        as season,
        data->>'gameType'                                             as game_type,
        (data->>'officialDate')::date                                 as official_date,
        data->>'dayNight'                                             as day_night,
        data->'status'->>'abstractGameState'                          as abstract_game_state,
        data->'status'->>'detailedState'                              as detailed_state,
        case
            when data->'status'->>'detailedState' = 'Completed Early' then true
            when data->'status'->>'detailedState' = 'Final'           then false
            -- null for Live or Preview — game has not concluded, mercy rule unknown
            else null
        end                                                             as is_mercy_rule,
        data->'teams'->'away'->'team'->>'name'                        as away_team_name,
        nullif(data->'teams'->'away'->'team'->>'id', '')::int          as away_team_id,
        data->'teams'->'home'->'team'->>'name'                        as home_team_name,
        nullif(data->'teams'->'home'->'team'->>'id', '')::int          as home_team_id,
        nullif(data->'teams'->'away'->>'score', '')::int              as away_score,
        nullif(data->'teams'->'home'->>'score', '')::int              as home_score,
        case
            when data->'teams'->'away'->>'isWinner' = 'true'  then true
            when data->'teams'->'away'->>'isWinner' = 'false' then false
            else null
        end                                                             as away_is_winner,
        case
            when data->'teams'->'home'->>'isWinner' = 'true'  then true
            when data->'teams'->'home'->>'isWinner' = 'false' then false
            else null
        end                                                             as home_is_winner,
        data->'venue'->>'name'                                        as venue_name,
        data->>'description'                                          as description,
        data->>'seriesDescription'                                    as series_description,
        data->>'ifNecessary'                                          as if_necessary,
        case
            when data->'teams'->'away'->'team'->>'placeholder' = 'true'  then true
            when data->'teams'->'away'->'team'->>'placeholder' = 'false' then false
            -- null when placeholder key absent (normal completed games)
            else null
        end                                                             as away_team_is_placeholder,
        case
            when data->'teams'->'home'->'team'->>'placeholder' = 'true'  then true
            when data->'teams'->'home'->'team'->>'placeholder' = 'false' then false
            -- null when placeholder key absent (normal completed games)
            else null
        end                                                             as home_team_is_placeholder,
        ingested_at
    from source
)

select * from flattened
