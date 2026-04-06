{{
  config(
    materialized = 'view',
    tags = ['staging', 'players']
  )
}}

with source as (
    select * from {{ source('wbc_raw', 'raw_wbc__players') }}
),

renamed as (
    select
        -- Primary Identifier
        player_id,
        
        -- Audit Timestamp
        ingested_at,

        -- Player Status
        (data -> 'active')::boolean as active,
        (data -> 'gender')::text as gender,
        (data -> 'isVerified')::boolean as is_verified,
        
        -- Physical Attributes
        (data -> 'height')::text as height,
        (data -> 'weight')::integer as weight,
        (data -> 'currentAge')::integer as current_age,
        
        -- Name Fields
        (data -> 'useName')::text as use_name,
        (data -> 'fullName')::text as full_name,
        (data -> 'firstName')::text as first_name,
        (data -> 'middleName')::text as middle_name,
        (data -> 'lastName')::text as last_name,
        (data -> 'useLastName')::text as use_last_name,
        (data -> 'boxscoreName')::text as boxscore_name,
        
        -- Biographical Information
        (data -> 'birthDate')::text as birth_date,
        (data -> 'birthCity')::text as birth_city,
        (data -> 'birthCountry')::text as birth_country,
        (data -> 'mlbDebutDate')::text as mlb_debut_date,
        
        -- Game Attributes
        (data -> 'batSide' -> 'code')::text as bat_side_code,
        (data -> 'pitchHand' -> 'code')::text as pitch_hand_code,
        (data -> 'primaryNumber')::text as primary_number,
        
        -- Strike Zone Measurements
        (data -> 'strikeZoneTop')::numeric as strike_zone_top,
        (data -> 'strikeZoneBottom')::numeric as strike_zone_bottom,
        
        -- Position Information
        (data -> 'primaryPosition' -> 'code')::text as primary_position_code,
        (data -> 'primaryPosition' -> 'name')::text as primary_position_name,
        (data -> 'primaryPosition' -> 'type')::text as primary_position_type,
        (data -> 'primaryPosition' -> 'abbreviation')::text as primary_position_abbreviation,
        
        -- Team Association
        (data -> 'currentTeam' -> 'id')::integer as current_team_id

    from source
)

select * from renamed