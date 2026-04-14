/*
    app_player_season_stats
    -----------------------
    Purpose: UI-optimized player season leaderboard view.
             Exact schema match for frontend Player page.
             This is the single source for all player leaderboard displays.

    Grain: one row per player per season
    Source: fct_player_game_stats + dim_players + dim_teams + dim_games

    Design: This is the ONLY place we aggregate player game stats to season totals.
            All rate calculations (AVG, ERA, OBP, SLG, OPS) happen here.
            Matches exact column naming schema that frontend is currently using.
*/

with player_game_stats as (

    select 
        ps.*,
        g.season
    from {{ ref('fct_player_game_stats') }} ps
    left join {{ ref('dim_games') }} g
        on ps.game_pk = g.game_pk

),

season_aggregates as (

    select
        player_id,
        season,
        
        -- Game counts
        count(distinct game_pk) as games_played,

        -- Batting aggregates
        sum(batting_at_bats) as season_batting_ab,
        sum(batting_hits) as season_batting_hits,
        sum(batting_doubles) as season_batting_doubles,
        sum(batting_triples) as season_batting_triples,
        sum(batting_home_runs) as season_batting_hr,
        sum(batting_rbi) as season_batting_rbi,
        sum(batting_walks) as season_batting_bb,
        sum(batting_strikeouts) as season_batting_so,
        sum(batting_stolen_bases) as season_batting_sb,
        sum(batting_plate_appearances) as season_batting_pa,
        sum(batting_total_bases) as season_batting_tb,
        sum(batting_sac_flies) as season_batting_sf,
        sum(batting_ground_outs + batting_air_outs) as season_batting_bip,

        -- Pitching aggregates
        sum(pitching_outs) / 3.0 as season_pitching_ip,
        sum(pitching_earned_runs) as season_pitching_er,
        sum(pitching_strikeouts) as season_pitching_so,
        sum(pitching_walks) as season_pitching_bb,
        sum(pitching_hits_allowed) as season_pitching_h,
        sum(pitching_wins) as season_pitching_w,
        sum(pitching_losses) as season_pitching_l,
        sum(pitching_saves) as season_pitching_sv,
        sum(pitching_batters_faced) as season_pitching_bf,
        sum(pitching_games_started) as season_pitching_gs,

        -- Team is consistent for all games a player appears in per tournament
        min(team_id) as team_id

    from player_game_stats
    group by player_id, season

),

players as (

    select * from {{ ref('dim_players') }}

),

teams as (

    select * from {{ ref('dim_teams') }}

),

final as (

    select
        -- Primary identifiers
        a.player_id as person_id,
        a.season,

        -- Player attributes
        p.full_name,
        p.primary_position_type as position_type,
        p.primary_position_abbreviation as position,

        -- Team attributes
        t.team_abbreviation,

        -- Game count
        a.games_played,

        -- Additional player attributes
        p.bat_side_code,
        p.pitch_hand_code,

        -- Batting stats
        a.season_batting_ab,
        a.season_batting_hits,
        round(cast(a.season_batting_hits as numeric) / nullif(a.season_batting_ab, 0), 3) as season_batting_avg,
        a.season_batting_doubles,
        a.season_batting_triples,
        a.season_batting_hr,
        a.season_batting_rbi,
        a.season_batting_bb,
        a.season_batting_so,
        round(cast(a.season_batting_hits + a.season_batting_bb as numeric) / nullif(a.season_batting_pa, 0), 3) as season_batting_obp,
        round(cast(a.season_batting_tb as numeric) / nullif(a.season_batting_ab, 0), 3) as season_batting_slg,
        round(
            (cast(a.season_batting_hits + a.season_batting_bb as numeric) / nullif(a.season_batting_pa, 0)) +
            (cast(a.season_batting_tb as numeric) / nullif(a.season_batting_ab, 0)),
            3
        ) as season_batting_ops,
        round(
            (cast(a.season_batting_tb as numeric) / nullif(a.season_batting_ab, 0)) - 
            (cast(a.season_batting_hits as numeric) / nullif(a.season_batting_ab, 0)),
            3
        ) as season_batting_iso,
        round(
            cast(a.season_batting_hits - a.season_batting_hr as numeric) / 
            nullif(a.season_batting_bip - a.season_batting_so - a.season_batting_hr, 0),
            3
        ) as season_batting_babip,
        round(cast(a.season_batting_so as numeric) / nullif(a.season_batting_pa, 0), 3) as season_batting_k_rate,
        round(cast(a.season_batting_bb as numeric) / nullif(a.season_batting_pa, 0), 3) as season_batting_bb_rate,
        a.season_batting_sb,

        -- Pitching stats
        round(cast(a.season_pitching_er * 9 as numeric) / nullif(a.season_pitching_ip, 0), 2) as season_pitching_era,
        round(a.season_pitching_ip, 1) as season_pitching_ip,
        round(cast(a.season_pitching_so * 9 as numeric) / nullif(a.season_pitching_ip, 0), 2) as season_pitching_k_per_9,
        round(cast(a.season_pitching_bb * 9 as numeric) / nullif(a.season_pitching_ip, 0), 2) as season_pitching_bb_per_9,
        round(cast(a.season_pitching_h + a.season_pitching_bb as numeric) / nullif(a.season_pitching_ip, 0), 3) as season_pitching_whip,
        a.season_pitching_so,
        a.season_pitching_bb,
        a.season_pitching_w,
        a.season_pitching_l,
        a.season_pitching_sv,
        a.season_pitching_gs

    from season_aggregates a
    left join players p
        on a.player_id = p.player_id
    left join teams t
        on a.team_id = t.team_id

)

select * from final
order by season desc, season_batting_ops desc, season_pitching_era asc