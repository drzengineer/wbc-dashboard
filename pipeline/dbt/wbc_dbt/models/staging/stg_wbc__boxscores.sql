{{
  config(
    materialized = 'view',
    tags = ['staging', 'boxscores', 'games']
  )
}}

with source as (
    select * from {{ source('wbc_raw', 'raw_wbc__boxscores') }}
),

renamed as (
    select
        -- Primary Identifier
        game_pk,
        
        -- Audit Timestamp
        ingested_at,

        -- General Game Information
        data -> 'info' as info,
        
        -- Full Team Objects (retained as json for downstream unnesting)
        data -> 'teams' -> 'away' as away_team_data,
        data -> 'teams' -> 'home' as home_team_data,
        
        -- Top Level Team Identifiers
        (data -> 'teams' -> 'away' -> 'team' -> 'id')::integer as away_team_id,
        (data -> 'teams' -> 'away' -> 'team' -> 'name')::text as away_team_name,
        (data -> 'teams' -> 'home' -> 'team' -> 'id')::integer as home_team_id,
        (data -> 'teams' -> 'home' -> 'team' -> 'name')::text as home_team_name

    from source
)

select * from renamed