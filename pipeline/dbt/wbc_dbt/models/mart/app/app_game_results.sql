/*
    app_game_results
    -----------------
    Purpose: UI-optimized completed game view, 1 row per game.
             Exact schema match for frontend GameResult interface.
             This is the single source for all game card displays across the dashboard.

    Grain: one row per completed game
    Source: dim_games + pivoted fct_team_game_stats

    Design: This is the ONLY place we pivot team game rows into home/away columns.
            All base fact and dimension tables remain untouched in their proper grain.
*/

with teams as (
    select
        game_pk,
        team_id,
        team_name,
        team_abbreviation,
        score,
        is_winner,
        tournament_round,
        season,
        side
    from {{ ref('fct_team_game_stats') }}
),

away_teams as (
    select * from teams where side = 'away'
),

home_teams as (
    select * from teams where side = 'home'
),

games as (
    select
        game_pk,
        official_date,
        season,
        game_type,
        series_game_number,
        venue_name,
        is_mercy_rule
    from {{ ref('dim_games') }}
)

select
    -- Primary Key
    g.game_pk,

    -- Game Identification
    g.season,
    g.official_date,
    g.game_type,

    -- Round Information
    away.tournament_round as round_label,
    case away.tournament_round
        when 'Pool Play'         then 1
        when 'Round 2'           then 2
        when 'Quarterfinals'      then 3
        when 'Semifinals'         then 4
        when 'Championship'      then 5
        else 0
    end as round_order,
    series_game_number,

    -- Away Team
    away.team_name as away_team_name,
    away.team_abbreviation as away_team_abbreviation,
    away.score as away_score,
    away.is_winner as away_is_winner,

    -- Home Team
    home.team_name as home_team_name,
    home.team_abbreviation as home_team_abbreviation,
    home.score as home_score,
    home.is_winner as home_is_winner,

    -- Game Attributes
    g.is_mercy_rule,
    g.venue_name,

    -- Metadata
    current_timestamp as refreshed_at

from games g
left join away_teams away on g.game_pk = away.game_pk
left join home_teams home on g.game_pk = home.game_pk

order by g.official_date desc