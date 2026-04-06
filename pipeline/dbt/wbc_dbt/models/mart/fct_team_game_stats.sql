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

    select * from {{ ref('int_wbc__game_teams') }}

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
        s.wins,
        s.losses,
        s.win_pct,

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
