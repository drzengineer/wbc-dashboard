/*
    dim_players
    -----------
    Purpose: Descriptive attributes for every player who appears in WBC data.
             Provides the stable "who is this player" bio context that
             fct_player_game_stats joins to.

    Key design decisions:
        - stg_wbc__players (via int_wbc__players) is the primary spine.
          It contains the richest bio data: birthdate, birthplace, height,
          weight, bat/pitch hand, debut date, etc.
        - int_wbc__game_players is used as a fallback to catch any players
          who appeared in a game boxscore but were never pulled into the
          players API endpoint. The COALESCE pattern ensures we never lose
          a player who appeared in a game just because they lack a bio record.
        - No stats live here. A player's name and birthplace are stable;
          their AVG and ERA are not. All stats belong on the fact and agg
          tables.
        - Position and jersey number from the bio API are the "primary"
          values. Per-game values (which can differ) live on
          fct_player_game_stats.

    Grain: one row per player_id
    Sources: int_wbc__players (spine), int_wbc__game_players (fallback enrichment)
*/

with players as (

    select * from {{ ref('int_wbc__players') }}

),

/*
    Pull one row per player from game appearances as a fallback.
    We take the most recent game appearance to get the latest known
    name and position in case the bio API record is missing.
*/
game_players_ranked as (

    select
        *,
        row_number() over (
            partition by player_id
            order by ingested_at desc
        )                               as rn

    from {{ ref('int_wbc__game_players') }}

),

game_players as (

    select * from game_players_ranked where rn = 1

),

/*
    Union all known player_ids from both sources so we have a complete
    universe of players. The left join pattern below will then fill in
    whatever bio data is available.
*/
all_player_ids as (

    select player_id from players
    union
    select player_id from game_players

),

final as (

    select
        -- primary key
        a.player_id,

        -- player status (bio source only — not available from game data)
        p.active,
        p.is_verified,
        p.gender,

        -- name fields
        -- coalesce pulls from bio API first, falls back to game boxscore data
        -- if the player has no bio record
        coalesce(p.full_name,       gp.full_name)           as full_name,
        coalesce(p.first_name,      null)                   as first_name,
        coalesce(p.middle_name,     null)                   as middle_name,
        coalesce(p.last_name,       null)                   as last_name,
        coalesce(p.use_name,        null)                   as use_name,
        coalesce(p.use_last_name,   null)                   as use_last_name,
        coalesce(p.boxscore_name,   gp.boxscore_name)       as boxscore_name,

        -- biographical information (bio source only)
        p.birth_date,
        p.birth_city,
        p.birth_country,
        p.mlb_debut_date,

        -- physical attributes (bio source only)
        p.height,
        p.weight,
        p.current_age,

        -- handedness (bio source only)
        -- these are the most important scouting/analytical attributes
        p.bat_side_code,
        p.pitch_hand_code,

        -- primary jersey number from bio API
        -- note: per-game jersey numbers live on fct_player_game_stats
        p.primary_number,

        -- primary position from bio API
        -- coalesce to game data for players missing a bio record
        -- note: per-game positions live on fct_player_game_stats because
        -- players can and do play multiple positions across games
        coalesce(p.primary_position_code,           gp.position_code)           as primary_position_code,
        coalesce(p.primary_position_name,           gp.position_name)           as primary_position_name,
        coalesce(p.primary_position_type,           gp.position_type)           as primary_position_type,
        coalesce(p.primary_position_abbreviation,   gp.position_abbreviation)   as primary_position_abbreviation,

        -- strike zone measurements (bio source only, used in pitching analysis)
        p.strike_zone_top,
        p.strike_zone_bottom,

        -- current team at time of ingestion (snapshot — not historical)
        p.current_team_id,

        -- metadata
        -- use the bio ingested_at if available, otherwise fall back to game data
        coalesce(p.ingested_at, gp.ingested_at)     as ingested_at

    from all_player_ids a
    left join players p
        on a.player_id = p.player_id
    left join game_players gp
        on a.player_id = gp.player_id

)

select * from final
