/*
    agg_player_tournament_stats
    ---------------------------
    Purpose: One row per player per tournament (season + pool). Sums all counting
             stats from fct_player_game_stats and computes rate statistics from
             those totals. This is where dim attributes are joined in for the
             first time in the mart lineage.

    This is the primary table for player leaderboards, stat leaders, and
    tournament roster views. The frontend and BI tools should query this table
    rather than aggregating the fact table themselves.

    Source: fct_player_game_stats + dim_games + dim_players + dim_teams
    Grain: player_id + team_id + season + pool
*/

with fct as (

    select * from {{ ref('fct_player_game_stats') }}

),

dim_games as (

    select
        game_pk,
        season,
        pool,
        series_description
    from {{ ref('dim_games') }}

),

dim_players as (

    select
        player_id,
        full_name,
        boxscore_name,
        primary_position_code,
        primary_position_name,
        primary_position_type,
        primary_position_abbreviation,
        bat_side_code,
        pitch_hand_code,
        birth_country
    from {{ ref('dim_players') }}

),

dim_teams as (

    select
        team_id,
        team_name,
        team_abbreviation,
        division_id,
        division_name,
        league_name
    from {{ ref('dim_teams') }}

),

-- join game context onto the fact table before aggregating
fct_enriched as (

    select
        f.*,
        g.season,
        g.pool
    from fct f
    inner join dim_games g
        on f.game_pk = g.game_pk

),

aggregated as (

    select
        -- grain
        player_id,
        team_id,
        season,
        pool,

        -- role flags (true if ever true across the tournament)
        bool_or(pitching_games_started = 1)             as has_started_pitching,
        bool_or(not is_on_bench and not is_substitute)  as has_started,

        -- appearances
        count(distinct game_pk)                         as games_played,
        count(*) filter (where not is_on_bench
            and not is_substitute)                      as games_started,
        count(*) filter (
            where pitching_games_started = 1)           as games_started_pitching,

        -- batting counts
        sum(batting_plate_appearances)                  as batting_plate_appearances,
        sum(batting_at_bats)                            as batting_at_bats,
        sum(batting_runs)                               as batting_runs,
        sum(batting_hits)                               as batting_hits,
        sum(batting_doubles)                            as batting_doubles,
        sum(batting_triples)                            as batting_triples,
        sum(batting_home_runs)                          as batting_home_runs,
        sum(batting_rbi)                                as batting_rbi,
        sum(batting_walks)                              as batting_walks,
        sum(batting_intentional_walks)                  as batting_intentional_walks,
        sum(batting_strikeouts)                         as batting_strikeouts,
        sum(batting_hit_by_pitch)                       as batting_hit_by_pitch,
        sum(batting_sac_bunts)                          as batting_sac_bunts,
        sum(batting_sac_flies)                          as batting_sac_flies,
        sum(batting_stolen_bases)                       as batting_stolen_bases,
        sum(batting_caught_stealing)                    as batting_caught_stealing,
        sum(batting_left_on_base)                       as batting_left_on_base,
        sum(batting_total_bases)                        as batting_total_bases,
        sum(batting_gidp)                               as batting_gidp,
        sum(batting_ground_outs)                        as batting_ground_outs,
        sum(batting_air_outs)                           as batting_air_outs,

        -- pitching counts
        sum(pitching_outs)                              as pitching_outs,
        sum(pitching_total_pitches)                     as pitching_total_pitches,
        sum(pitching_strikes)                           as pitching_strikes,
        sum(pitching_balls)                             as pitching_balls,
        sum(pitching_hits_allowed)                      as pitching_hits_allowed,
        sum(pitching_runs_allowed)                      as pitching_runs_allowed,
        sum(pitching_earned_runs)                       as pitching_earned_runs,
        sum(pitching_home_runs_allowed)                 as pitching_home_runs_allowed,
        sum(pitching_strikeouts)                        as pitching_strikeouts,
        sum(pitching_walks)                             as pitching_walks,
        sum(pitching_intentional_walks)                 as pitching_intentional_walks,
        sum(pitching_hit_batsmen)                       as pitching_hit_batsmen,
        sum(pitching_wild_pitches)                      as pitching_wild_pitches,
        sum(pitching_balks)                             as pitching_balks,
        sum(pitching_batters_faced)                     as pitching_batters_faced,
        sum(pitching_inherited_runners)                 as pitching_inherited_runners,
        sum(pitching_inherited_runners_scored)          as pitching_inherited_runners_scored,
        sum(pitching_wins)                              as pitching_wins,
        sum(pitching_losses)                            as pitching_losses,
        sum(pitching_saves)                             as pitching_saves,
        sum(pitching_holds)                             as pitching_holds,
        sum(pitching_blown_saves)                       as pitching_blown_saves,

        -- fielding counts
        sum(fielding_errors)                            as fielding_errors,
        sum(fielding_assists)                           as fielding_assists,
        sum(fielding_put_outs)                          as fielding_put_outs,
        sum(fielding_chances)                           as fielding_chances,
        sum(fielding_passed_balls)                      as fielding_passed_balls,
        sum(fielding_pickoffs)                          as fielding_pickoffs

    from fct_enriched
    group by
        player_id,
        team_id,
        season,
        pool

),

final as (

    select
        -- surrogate key
        {{ dbt_utils.generate_surrogate_key(['a.player_id', 'a.team_id', 'a.season', 'a.pool']) }}
                                                        as player_tournament_id,

        -- grain
        a.player_id,
        a.team_id,
        a.season,
        a.pool,

        -- player attributes (joined from dim_players here in the agg layer)
        p.full_name,
        p.boxscore_name,
        p.primary_position_code,
        p.primary_position_name,
        p.primary_position_type,
        p.primary_position_abbreviation,
        p.bat_side_code,
        p.pitch_hand_code,
        p.birth_country,

        -- team attributes (joined from dim_teams here in the agg layer)
        t.team_name,
        t.team_abbreviation,
        t.division_id,
        t.division_name,
        t.league_name,

        -- role
        a.has_started_pitching                          as is_pitcher,
        a.has_started,
        a.games_played,
        a.games_started,
        a.games_started_pitching,

        -- batting counts
        a.batting_plate_appearances,
        a.batting_at_bats,
        a.batting_runs,
        a.batting_hits,
        a.batting_doubles,
        a.batting_triples,
        a.batting_home_runs,
        a.batting_rbi,
        a.batting_walks,
        a.batting_intentional_walks,
        a.batting_strikeouts,
        a.batting_hit_by_pitch,
        a.batting_sac_bunts,
        a.batting_sac_flies,
        a.batting_stolen_bases,
        a.batting_caught_stealing,
        a.batting_left_on_base,
        a.batting_total_bases,
        a.batting_gidp,
        a.batting_ground_outs,
        a.batting_air_outs,

        -- batting rates (computed from tournament totals)
        case
            when a.batting_at_bats > 0
            then round(a.batting_hits::numeric / a.batting_at_bats, 3)
        end                                             as batting_avg,

        case
            when (a.batting_at_bats + a.batting_walks + a.batting_hit_by_pitch + a.batting_sac_flies) > 0
            then round(
                (a.batting_hits + a.batting_walks + a.batting_hit_by_pitch)::numeric
                / (a.batting_at_bats + a.batting_walks + a.batting_hit_by_pitch + a.batting_sac_flies),
                3)
        end                                             as on_base_pct,

        case
            when a.batting_at_bats > 0
            then round(a.batting_total_bases::numeric / a.batting_at_bats, 3)
        end                                             as slugging_pct,

        case
            when a.batting_at_bats > 0
            and (a.batting_at_bats + a.batting_walks + a.batting_hit_by_pitch + a.batting_sac_flies) > 0
            then round(
                (a.batting_hits + a.batting_walks + a.batting_hit_by_pitch)::numeric
                / (a.batting_at_bats + a.batting_walks + a.batting_hit_by_pitch + a.batting_sac_flies)
                + a.batting_total_bases::numeric / a.batting_at_bats,
                3)
        end                                             as ops,

        case
            when (a.batting_stolen_bases + a.batting_caught_stealing) > 0
            then round(
                a.batting_stolen_bases::numeric
                / (a.batting_stolen_bases + a.batting_caught_stealing),
                3)
        end                                             as stolen_base_pct,

        case
            when a.batting_plate_appearances > 0
            then round(a.batting_strikeouts::numeric / a.batting_plate_appearances, 3)
        end                                             as batting_k_rate,

        case
            when a.batting_plate_appearances > 0
            then round(a.batting_walks::numeric / a.batting_plate_appearances, 3)
        end                                             as batting_bb_rate,

        -- pitching counts
        a.pitching_outs,

        -- innings pitched in baseball convention: 14 outs = 4.2, 15 outs = 5.0
        case
            when a.pitching_outs is not null
            then (a.pitching_outs / 3)
                 + round((a.pitching_outs % 3)::numeric / 10, 1)
        end                                             as innings_pitched,

        a.pitching_total_pitches,
        a.pitching_strikes,
        a.pitching_balls,
        a.pitching_hits_allowed,
        a.pitching_runs_allowed,
        a.pitching_earned_runs,
        a.pitching_home_runs_allowed,
        a.pitching_strikeouts,
        a.pitching_walks,
        a.pitching_intentional_walks,
        a.pitching_hit_batsmen,
        a.pitching_wild_pitches,
        a.pitching_balks,
        a.pitching_batters_faced,
        a.pitching_inherited_runners,
        a.pitching_inherited_runners_scored,
        a.pitching_wins,
        a.pitching_losses,
        a.pitching_saves,
        a.pitching_holds,
        a.pitching_blown_saves,

        -- pitching rates
        case
            when a.pitching_outs > 0
            then round((a.pitching_earned_runs::numeric * 27) / a.pitching_outs, 2)
        end                                             as era,

        case
            when a.pitching_outs > 0
            then round(
                ((a.pitching_walks + a.pitching_hits_allowed)::numeric * 3) / a.pitching_outs,
                3)
        end                                             as whip,

        case
            when a.pitching_total_pitches > 0
            then round(a.pitching_strikes::numeric / a.pitching_total_pitches, 3)
        end                                             as strike_pct,

        case
            when a.pitching_batters_faced > 0
            then round(a.pitching_strikeouts::numeric / a.pitching_batters_faced, 3)
        end                                             as k_rate,

        case
            when a.pitching_batters_faced > 0
            then round(a.pitching_walks::numeric / a.pitching_batters_faced, 3)
        end                                             as bb_rate,

        -- fielding counts
        a.fielding_errors,
        a.fielding_assists,
        a.fielding_put_outs,
        a.fielding_chances,
        a.fielding_passed_balls,
        a.fielding_pickoffs,

        -- fielding rate
        case
            when a.fielding_chances > 0
            then round(
                (a.fielding_put_outs + a.fielding_assists)::numeric / a.fielding_chances,
                3)
        end                                             as fielding_pct

    from aggregated a
    left join dim_players p
        on a.player_id = p.player_id
    left join dim_teams t
        on a.team_id = t.team_id

)

select * from final
