/*
    fct_team_game_stats
    -------------------
    Purpose: Core team-level fact table. One row per team per game.
             Keys and measures only — no attributes pulled from dimension tables.
             All descriptive context (team name, game date, venue, pool, etc.)
             is joined in at the agg layer.

    Source: int_wbc__game_teams (only)
    Grain: game_pk + team_id
*/

with source as (

    select
        game_team_id,
        game_pk,
        team_id,
        team_name,
        team_abbreviation,
        side,
        division_id,
        division_name,
        league_name,
        is_winner,
        score,
        hits,
        runs,
        errors,
        left_on_base,
        batting_plate_appearances,
        batting_at_bats,
        batting_runs,
        batting_hits,
        batting_doubles,
        batting_triples,
        batting_home_runs,
        batting_rbi,
        batting_walks,
        batting_intentional_walks,
        batting_strikeouts,
        batting_hit_by_pitch,
        batting_sac_bunts,
        batting_sac_flies,
        batting_stolen_bases,
        batting_caught_stealing,
        batting_left_on_base,
        batting_total_bases,
        batting_gidp,
        pitching_outs,
        pitching_hits_allowed,
        pitching_runs_allowed,
        pitching_earned_runs,
        pitching_home_runs_allowed,
        pitching_strikeouts,
        pitching_walks,
        pitching_intentional_walks,
        pitching_hit_batsmen,
        pitching_wild_pitches,
        pitching_balks,
        pitching_total_pitches,
        pitching_balls,
        pitching_strikes,
        pitching_batters_faced,
        pitching_inherited_runners,
        pitching_inherited_runners_scored,
        fielding_errors,
        fielding_assists,
        fielding_put_outs,
        fielding_chances,
        fielding_passed_balls,
        fielding_pickoffs,
        ingested_at
    from {{ ref('int_wbc__game_teams') }}

),

/*
    Self-reference to resolve the opponent for each team-game row.
    Each game has exactly two rows (home + away), so joining where
    game_pk matches but team_id differs gives us the opponent's score.
*/
opponents as (

    select
        game_pk,
        team_id     as opponent_team_id,
        score       as opponent_score
    from source

),

final as (

    select
        -- surrogate key
        s.game_team_id,

        -- foreign keys
        -- all descriptive attributes for these keys are joined at the agg layer
        s.game_pk,          -- → dim_games
        s.team_id,          -- → dim_teams
        opp.opponent_team_id, -- → dim_teams (join a second time for opponent context)

        -- game result measures
        s.is_winner,
        s.score,
        opp.opponent_score,
        s.score - opp.opponent_score    as run_differential,

        -- box score line
        s.hits,
        s.runs,
        s.errors,
        s.left_on_base,

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

        -- pitching counts
        s.pitching_outs,
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
        s.pitching_total_pitches,
        s.pitching_balls,
        s.pitching_strikes,
        s.pitching_batters_faced,
        s.pitching_inherited_runners,
        s.pitching_inherited_runners_scored,

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
    left join opponents opp
        on s.game_pk = opp.game_pk
        and s.team_id != opp.opponent_team_id

)

select * from final
