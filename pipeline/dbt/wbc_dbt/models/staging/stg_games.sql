with source as (
    select
        game_pk,
        data,
        ingested_at
    from {{ source('raw', 'games') }}
),

flattened as (
    select
        game_pk,
        (data->>'season')::int as season,

        -- Team abbreviations are only available in boxscore, not schedule
        data->'teams'->'away'->'team'->>'abbreviation' as away_team_abbreviation,
        data->'teams'->'home'->'team'->>'abbreviation' as home_team_abbreviation,

        -- Boxscore summary totals
        data->'teams'->'away'->'teamStats'->'batting'->>'runs' as away_runs,
        data->'teams'->'away'->'teamStats'->'batting'->>'hits' as away_hits,
        data->'teams'->'away'->'teamStats'->'batting'->>'errors' as away_errors,
        data->'teams'->'away'->'teamStats'->'batting'->>'leftOnBase' as away_left_on_base,

        data->'teams'->'home'->'teamStats'->'batting'->>'runs' as home_runs,
        data->'teams'->'home'->'teamStats'->'batting'->>'hits' as home_hits,
        data->'teams'->'home'->'teamStats'->'batting'->>'errors' as home_errors,
        data->'teams'->'home'->'teamStats'->'batting'->>'leftOnBase' as home_left_on_base,

        ingested_at

    from source
)

select * from flattened