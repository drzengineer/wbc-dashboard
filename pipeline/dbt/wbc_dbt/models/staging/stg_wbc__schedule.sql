{{
  config(
    materialized = 'view',
    tags = ['staging', 'schedule', 'games']
  )
}}

with source as (
    select * from {{ source('wbc_raw', 'raw_wbc__schedule') }}
),

renamed as (
    select
        -- Primary Identifier
        game_pk,
        
        -- Audit Timestamp
        ingested_at,

        -- Game Metadata
        (data -> 'gameGuid')::text as game_guid,
        (data -> 'gameType')::text as game_type,
        (data -> 'season')::text as season,
        (data -> 'gameDate')::text as game_date,
        (data -> 'officialDate')::text as official_date,
        (data -> 'dayNight')::text as day_night,
        (data -> 'description')::text as description,
        (data -> 'seriesDescription')::text as series_description,
        
        -- Game Status
        (data -> 'isTie')::boolean as is_tie,
        (data -> 'status' -> 'statusCode')::text as status_code,
        (data -> 'status' -> 'startTimeTBD')::boolean as start_time_tbd,
        (data -> 'status' -> 'codedGameState')::text as coded_game_state,
        (data -> 'status' -> 'abstractGameCode')::text as abstract_game_code,
        
        -- Game Sequence Information
        (data -> 'gameNumber')::integer as game_number,
        (data -> 'doubleHeader')::text as double_header,
        (data -> 'tiebreaker')::text as tiebreaker,
        (data -> 'ifNecessary')::text as if_necessary,
        (data -> 'gamedayType')::text as gameday_type,
        (data -> 'gamesInSeries')::integer as games_in_series,
        (data -> 'seriesGameNumber')::integer as series_game_number,
        (data -> 'inningBreakLength')::integer as inning_break_length,
        (data -> 'reverseHomeAwayStatus')::boolean as reverse_home_away_status,
        
        -- Venue Information
        (data -> 'venue' -> 'id')::integer as venue_id,
        (data -> 'venue' -> 'name')::text as venue_name,

        -- Away Team
        (data -> 'teams' -> 'away' -> 'team' -> 'id')::integer as away_team_id,
        (data -> 'teams' -> 'away' -> 'team' -> 'name')::text as away_team_name,
        (data -> 'teams' -> 'away' -> 'score')::integer as away_score,
        (data -> 'teams' -> 'away' -> 'isWinner')::boolean as away_is_winner,
        (data -> 'teams' -> 'away' -> 'splitSquad')::boolean as away_split_squad,
        (data -> 'teams' -> 'away' -> 'seriesNumber')::integer as away_series_number,
        (data -> 'teams' -> 'away' -> 'leagueRecord' -> 'pct')::text as away_win_pct,
        (data -> 'teams' -> 'away' -> 'leagueRecord' -> 'wins')::integer as away_wins,
        (data -> 'teams' -> 'away' -> 'leagueRecord' -> 'losses')::integer as away_losses,
        
        -- Home Team
        (data -> 'teams' -> 'home' -> 'team' -> 'id')::integer as home_team_id,
        (data -> 'teams' -> 'home' -> 'team' -> 'name')::text as home_team_name,
        (data -> 'teams' -> 'home' -> 'score')::integer as home_score,
        (data -> 'teams' -> 'home' -> 'isWinner')::boolean as home_is_winner,
        (data -> 'teams' -> 'home' -> 'splitSquad')::boolean as home_split_squad,
        (data -> 'teams' -> 'home' -> 'seriesNumber')::integer as home_series_number,
        (data -> 'teams' -> 'home' -> 'leagueRecord' -> 'pct')::text as home_win_pct,
        (data -> 'teams' -> 'home' -> 'leagueRecord' -> 'wins')::integer as home_wins,
        (data -> 'teams' -> 'home' -> 'leagueRecord' -> 'losses')::integer as home_losses,
        
        -- Live Linescore State
        (data -> 'linescore' -> 'outs')::integer as outs,
        (data -> 'linescore' -> 'balls')::integer as balls,
        (data -> 'linescore' -> 'strikes')::integer as strikes,
        (data -> 'linescore' -> 'inningHalf')::text as inning_half,
        (data -> 'linescore' -> 'inningState')::text as inning_state,
        (data -> 'linescore' -> 'currentInning')::integer as current_inning,
        (data -> 'linescore' -> 'scheduledInnings')::integer as scheduled_innings,
        
        -- Linescore Team Totals
        (data -> 'linescore' -> 'teams' -> 'away' -> 'hits')::integer as away_hits,
        (data -> 'linescore' -> 'teams' -> 'away' -> 'runs')::integer as away_runs,
        (data -> 'linescore' -> 'teams' -> 'away' -> 'errors')::integer as away_errors,
        (data -> 'linescore' -> 'teams' -> 'away' -> 'leftOnBase')::integer as away_left_on_base,
        (data -> 'linescore' -> 'teams' -> 'home' -> 'hits')::integer as home_hits,
        (data -> 'linescore' -> 'teams' -> 'home' -> 'runs')::integer as home_runs,
        (data -> 'linescore' -> 'teams' -> 'home' -> 'errors')::integer as home_errors,
        (data -> 'linescore' -> 'teams' -> 'home' -> 'leftOnBase')::integer as home_left_on_base,
        
        -- Innings Breakdown (retained as json array)
        data -> 'linescore' -> 'innings' as innings

    from source
)

select * from renamed