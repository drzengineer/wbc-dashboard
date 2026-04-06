/*
    fct_player_game_stats
    ---------------------
    Purpose: Core player-level fact table. One row per player per game.
             Keys and measures only — no attributes pulled from dimension tables.
             All descriptive context (player name, position, team name, game date,
             etc.) is joined in at the agg layer.

    Source: int_wbc__game_players (only)
    Grain: game_pk + player_id
*/

with source as (

    select * from {{ ref('int_wbc__game_players') }}

),

final as (

    select
        -- surrogate key
        s.game_player_id,

        -- foreign keys
        -- all descriptive attributes for these keys are joined at the agg layer
        s.game_pk,      -- → dim_games
        s.player_id,    -- → dim_players
        s.team_id,      -- → dim_teams

        -- game role measures
        -- batting_order is a measure of lineup position, not a display attribute
        s.batting_order,
        s.is_on_bench,
        s.is_substitute,
        s.is_current_batter,
        s.is_current_pitcher,

        -- batting counts
        s.batting_plate_appearances,
        s.batting_at_bats,
        s.batting_runs,
        s.batting_hits,
        s.batting_doubles,
        s.batting_triples,
        s.batting_home_runs,
        s.batting_rbi,
        s.batting_walks,
        s.batting_intentional_walks,
        s.batting_strikeouts,
        s.batting_hit_by_pitch,
        s.batting_sac_bunts,
        s.batting_sac_flies,
        s.batting_stolen_bases,
        s.batting_caught_stealing,
        s.batting_left_on_base,
        s.batting_total_bases,
        s.batting_gidp,
        s.batting_ground_outs,
        s.batting_air_outs,
        s.batting_pickoffs,

        -- pitching counts
        s.pitching_outs,
        s.pitching_total_pitches,
        s.pitching_strikes,
        s.pitching_balls,
        s.pitching_hits_allowed,
        s.pitching_runs_allowed,
        s.pitching_earned_runs,
        s.pitching_home_runs_allowed,
        s.pitching_strikeouts,
        s.pitching_walks,
        s.pitching_intentional_walks,
        s.pitching_hit_batsmen,
        s.pitching_wild_pitches,
        s.pitching_balks,
        s.pitching_batters_faced,
        s.pitching_inherited_runners,
        s.pitching_inherited_runners_scored,
        s.pitching_wins,
        s.pitching_losses,
        s.pitching_saves,
        s.pitching_holds,
        s.pitching_blown_saves,
        s.pitching_games_started,

        -- fielding counts
        s.fielding_errors,
        s.fielding_assists,
        s.fielding_put_outs,
        s.fielding_chances,
        s.fielding_passed_balls,
        s.fielding_pickoffs,

        -- metadata
        s.ingested_at

    from source s

)

select * from final
