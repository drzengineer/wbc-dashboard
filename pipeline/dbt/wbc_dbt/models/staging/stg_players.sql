with source as (
    select player_id, data, ingested_at
    from {{ source('raw', 'players') }}
),

flattened as (
    select
        player_id,
        (data->>'id')::int                              as person_id,
        data->>'fullName'                               as full_name,
        data->>'useName'                                as use_name,
        data->>'lastName'                               as last_name,
        data->>'boxscoreName'                           as boxscore_name,
        data->>'nameSlug'                               as name_slug,
        nullif(data->>'primaryNumber', '')              as jersey_number,
        data->>'height'                                 as height,
        nullif(data->>'weight', '')::int                as weight,
        -- nullif guards on all date/boolean casts — empty string from API crashes ::date/::boolean
        nullif(data->>'birthDate',    '')::date         as birth_date,
        data->>'birthCity'                              as birth_city,
        data->>'birthCountry'                           as birth_country,
        data->'batSide'->>'code'                        as bat_side,
        data->'pitchHand'->>'code'                      as pitch_hand,
        data->'primaryPosition'->>'abbreviation'        as position_abbreviation,
        data->'primaryPosition'->>'name'                as position_name,
        data->'primaryPosition'->>'type'                as position_type,
        nullif(data->>'mlbDebutDate', '')::date         as mlb_debut_date,
        nullif(data->>'active',       '')::boolean      as is_active,
        nullif(data->'currentTeam'->>'id', '')::int     as current_mlb_team_id,
        data->>'middleName'                             as middle_name,
        data->>'nameMatrilineal'                        as name_matrilineal,
        ingested_at
    from source
)

select * from flattened