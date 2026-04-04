/*
================================================================================
int_games
Single source of truth for all game data.

This is the ONLY place we join schedule + boxscore. All downstream analytics
models select only from this table, never from staging or raw directly.

100% backwards compatible with existing schema. All existing fields preserved.
================================================================================
*/

with schedule as (
    select * from {{ ref('stg_schedule') }}
),

games as (
    select * from {{ ref('stg_games') }}
)

select
    -- Primary key
    s.game_pk,
    s.season,

    -- Core game metadata
    s.official_date,
    s.day_night,
    s.game_type,
    s.abstract_game_state,
    s.detailed_state,
    s.is_mercy_rule,

    -- Teams
    s.away_team_id,
    s.away_team_name,
    g.away_team_abbreviation,
    s.home_team_id,
    s.home_team_name,
    g.home_team_abbreviation,

    -- Scores and outcome
    s.away_score,
    s.home_score,
    s.away_is_winner,
    s.home_is_winner,

    -- Boxscore summary totals
    g.away_hits,
    g.away_errors,
    g.away_left_on_base,
    g.home_hits,
    g.home_errors,
    g.home_left_on_base,

    -- Venue and metadata
    s.venue_name,
    s.description,
    s.series_description,
    s.if_necessary,
    s.away_team_is_placeholder,
    s.home_team_is_placeholder,

    -- Audit
    s.ingested_at as schedule_ingested_at,
    g.ingested_at as games_ingested_at

from schedule s
left join games g using (game_pk)

order by s.season, s.official_date, s.game_pk