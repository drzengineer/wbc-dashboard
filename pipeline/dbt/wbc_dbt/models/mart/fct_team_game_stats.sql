/*
    fct_team_game_stats
    -------------------
    Purpose: Core team-level fact table. One row per team per game.
             Keys and measures only — no attributes pulled from dimension tables.
             All descriptive context (team name, game date, venue, pool, etc.)
             is joined in at the agg layer.

    Sources: int_wbc__game_teams (team stats per game)
             int_wbc__games      (tournament context per game)

    Grain: game_pk + team_id

    Join note: inner join is intentional. Every game_team row must have a
               corresponding game record. A missing game would mean broken
               source data, not a graceful null.

    Tournament context fields:
      tournament_round  – human-readable round label derived in int_wbc__games
                          ('Pool Play', 'Round 2', 'Quarterfinal', 'Semifinal', 'Championship')
      pool_group        – the specific pool or round group for filtering/aggregation
                          e.g. 'Pool A', 'Pool B', 'Pool 1', 'Pool 2',
                               'Quarterfinal', 'Semifinal', 'Championship'
*/

with source as (

    select
        gt.game_team_id,
        gt.game_pk,
        gt.team_id,
        gt.team_name,
        gt.team_abbreviation,
        gt.side,
        gt.is_winner,
        gt.score,
        gt.hits,
        gt.runs,
        gt.errors,
        gt.left_on_base,

        -- tournament context from game grain
        g.season,
        g.game_type,
        g.series_description,
        g.tournament_round,
        g.pool_group,

        -- batting counts
        gt.batting_plate_appearances,
        gt.batting_at_bats,
        gt.batting_runs,
        gt.batting_hits,
        gt.batting_doubles,
        gt.batting_triples,
        gt.batting_home_runs,
        gt.batting_rbi,
        gt.batting_walks,
        gt.batting_intentional_walks,
        gt.batting_strikeouts,
        gt.batting_hit_by_pitch,
        gt.batting_sac_bunts,
        gt.batting_sac_flies,
        gt.batting_stolen_bases,
        gt.batting_caught_stealing,
        gt.batting_left_on_base,
        gt.batting_total_bases,
        gt.batting_gidp,

        -- pitching counts
        gt.pitching_outs,
        gt.pitching_hits_allowed,
        gt.pitching_runs_allowed,
        gt.pitching_earned_runs,
        gt.pitching_home_runs_allowed,
        gt.pitching_strikeouts,
        gt.pitching_walks,
        gt.pitching_intentional_walks,
        gt.pitching_hit_batsmen,
        gt.pitching_wild_pitches,
        gt.pitching_balks,
        gt.pitching_total_pitches,
        gt.pitching_balls,
        gt.pitching_strikes,
        gt.pitching_batters_faced,
        gt.pitching_inherited_runners,
        gt.pitching_inherited_runners_scored,

        -- fielding counts
        gt.fielding_errors,
        gt.fielding_assists,
        gt.fielding_put_outs,
        gt.fielding_chances,
        gt.fielding_passed_balls,
        gt.fielding_pickoffs,

        gt.ingested_at

    from {{ ref('int_wbc__game_teams') }} gt
    inner join {{ ref('int_wbc__games') }} g
        on gt.game_pk = g.game_pk

),

/*
    Self-join to resolve the opponent for each team-game row.
    Each game has exactly two rows (home + away), so joining on
    game_pk where team_id differs gives us the opponent's score.
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
        s.game_pk,              -- → dim_games
        s.team_id,              -- → dim_teams
        opp.opponent_team_id,   -- → dim_teams (second alias for opponent context)

        -- team identity
        s.team_name,
        s.team_abbreviation,
        s.side,

        -- tournament context
        s.season,
        s.game_type,
        s.series_description,
        s.tournament_round,
        s.pool_group,

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
    inner join opponents opp
        on s.game_pk = opp.game_pk
        and s.team_id != opp.opponent_team_id

)

select * from final
