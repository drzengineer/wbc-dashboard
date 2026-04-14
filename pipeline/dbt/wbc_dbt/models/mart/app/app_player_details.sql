/*
    app_player_details
    ------------------
    Purpose: Single source of truth for the player [id] page.
             One query returns everything the frontend needs — bio, per-season
             stats, per-game logs, season max values for gauges/radar, and
             career totals. Zero calculations remain on the frontend.

    Grain:   one row per player_id
    Sources: dim_players            — bio spine
             fct_player_game_stats  — per-game raw counts (batting + pitching)
             dim_games              — official_date, season, tournament_round
             fct_team_game_stats    — per-game scores / team sides for game result
             dim_teams              — team_abbreviation for player header + game log
*/

-- 1. RAW GAME STATS
with player_games as (
    select
        fps.player_id,
        fps.team_id,
        fps.game_pk,
        dg.season,
        dg.official_date,
        dg.tournament_round             as round_label,
        fps.batting_at_bats             as batting_ab,
        fps.batting_hits                as batting_h,
        fps.batting_runs                as batting_r,
        fps.batting_doubles             as batting_2b,
        fps.batting_triples             as batting_3b,
        fps.batting_home_runs           as batting_hr,
        fps.batting_rbi                 as batting_rbi,
        fps.batting_walks               as batting_bb,
        fps.batting_strikeouts          as batting_so,
        fps.batting_stolen_bases        as batting_sb,
        fps.batting_plate_appearances   as batting_pa,
        fps.batting_total_bases         as batting_tb,
        fps.pitching_outs               as pitching_outs,
        fps.pitching_earned_runs        as pitching_er,
        fps.pitching_strikeouts         as pitching_so,
        fps.pitching_walks              as pitching_bb,
        fps.pitching_hits_allowed       as pitching_h,
        fps.pitching_wins               as pitching_w,
        fps.pitching_losses             as pitching_l,
        fps.pitching_saves              as pitching_sv,
        fps.pitching_batters_faced      as pitching_bf,
        fps.pitching_games_started      as pitching_gs
    from {{ ref('fct_player_game_stats') }} fps
    inner join {{ ref('dim_games') }} dg on fps.game_pk = dg.game_pk
),

-- 2. GAME RESULT CONTEXT
game_results as (
    select
        away.game_pk,
        away.team_abbreviation  as away_team_abbreviation,
        away.score              as away_score,
        home.team_abbreviation  as home_team_abbreviation,
        home.score              as home_score
    from {{ ref('fct_team_game_stats') }} away
    inner join {{ ref('fct_team_game_stats') }} home
        on  away.game_pk = home.game_pk
        and away.side    = 'away'
        and home.side    = 'home'
),

-- 3. SEASON AGGREGATES PER PLAYER
season_stats as (
    select
        player_id,
        season,
        count(distinct game_pk) as games_played,
        sum(batting_ab) as ab,
        sum(batting_h) as h,
        sum(batting_r) as r,
        sum(batting_2b) as doubles,
        sum(batting_3b) as triples,
        sum(batting_hr) as hr,
        sum(batting_rbi) as rbi,
        sum(batting_bb) as bb,
        sum(batting_so) as so,
        sum(batting_sb) as sb,
        sum(batting_pa) as pa,
        sum(batting_tb) as tb,
        round(sum(batting_h)::numeric / nullif(sum(batting_ab), 0), 3) as batting_avg,
        round((sum(batting_h) + sum(batting_bb))::numeric / nullif(sum(batting_pa), 0), 3) as obp,
        round(sum(batting_tb)::numeric / nullif(sum(batting_ab), 0), 3) as slg,
        round(((sum(batting_h) + sum(batting_bb))::numeric / nullif(sum(batting_pa), 0)) + (sum(batting_tb)::numeric / nullif(sum(batting_ab), 0)), 3) as ops,
        sum(pitching_outs) as p_outs,
        sum(pitching_er) as p_er,
        sum(pitching_so) as p_so,
        sum(pitching_bb) as p_bb,
        sum(pitching_h) as p_h,
        sum(pitching_w) as p_w,
        sum(pitching_l) as p_l,
        sum(pitching_sv) as p_sv,
        sum(pitching_bf) as p_bf,
        sum(pitching_gs) as p_gs,
        round(sum(pitching_er)::numeric * 9 / nullif(sum(pitching_outs)::numeric / 3, 0), 2) as era,
        round(sum(pitching_outs)::numeric / 3, 1) as ip,
        min(team_id) as team_id
    from player_games
    group by player_id, season
),

-- 4. SEASON MAX STATS (ALL PLAYERS)
season_maxes as (
    select
        season,
        max(batting_avg)    as max_batting_avg,
        max(obp)            as max_obp,
        max(slg)            as max_slg,
        max(ops)            as max_ops,
        max(hr)             as max_hr,
        max(rbi)            as max_rbi,
        max(r)              as max_r,
        max(sb)             as max_sb,
        max(h)              as max_h,
        max(bb)             as max_bb,
        max(so)             as max_so,
        max(p_so)           as max_p_so,
        max(ip)             as max_ip,
        max(p_w)            as max_p_w,
        max(p_l)            as max_p_l,
        max(p_sv)           as max_p_sv,
        max(games_played)   as max_games_played,
        max(p_bf)           as max_p_bf,
        max(p_h)            as max_p_h,
        max(p_bb)           as max_p_bb
    from season_stats
    group by season
),

-- 5. LATEST TEAM PER PLAYER
latest_team as (
    select distinct on (player_id)
        player_id,
        team_id
    from player_games
    order by player_id, official_date desc
),

-- 6. AGGREGATE SEASONS JSON
player_seasons_agg as (
    select
        ss.player_id,
        jsonb_agg(
            jsonb_build_object(
                'season',                   ss.season,
                'team_abbreviation',        dt.team_abbreviation,
                'games_played',             ss.games_played,
                'season_batting_ab',        ss.ab,
                'season_batting_avg',       ss.batting_avg,
                'season_batting_h',         ss.h,
                'season_batting_doubles',   ss.doubles,
                'season_batting_triples',   ss.triples,
                'season_batting_hr',        ss.hr,
                'season_batting_rbi',       ss.rbi,
                'season_batting_r',         ss.r,
                'season_batting_bb',        ss.bb,
                'season_batting_so',        ss.so,
                'season_batting_obp',       ss.obp,
                'season_batting_slg',       ss.slg,
                'season_batting_ops',       ss.ops,
                'season_batting_sb',        ss.sb,
                'season_pitching_era',      ss.era,
                'season_pitching_ip',       ss.ip,
                'season_pitching_so',       ss.p_so,
                'season_pitching_bb',       ss.p_bb,
                'season_pitching_h',        ss.p_h,
                'season_pitching_w',        ss.p_w,
                'season_pitching_l',        ss.p_l,
                'season_pitching_sv',       ss.p_sv,
                'season_pitching_bf',       ss.p_bf,
                'season_pitching_gs',       ss.p_gs
            ) order by ss.season desc
        ) as tournament_stats,
        jsonb_object_agg(
            sm.season,
            jsonb_build_object(
                'batting', jsonb_build_object(
                    'season_batting_avg',   sm.max_batting_avg,
                    'season_batting_obp',   sm.max_obp,
                    'season_batting_slg',   sm.max_slg,
                    'season_batting_ops',   sm.max_ops,
                    'season_batting_hr',    sm.max_hr,
                    'season_batting_rbi',   sm.max_rbi,
                    'season_batting_r',     sm.max_r,
                    'season_batting_sb',    sm.max_sb,
                    'season_batting_h',     sm.max_h,
                    'season_batting_bb',    sm.max_bb,
                    'season_batting_so',    sm.max_so
                ),
                'pitching', jsonb_build_object(
                    'season_pitching_so',   sm.max_p_so,
                    'season_pitching_ip',   sm.max_ip,
                    'season_pitching_w',    sm.max_p_w,
                    'season_pitching_l',    sm.max_p_l,
                    'season_pitching_sv',   sm.max_p_sv,
                    'games_played',         sm.max_games_played,
                    'season_pitching_bf',   sm.max_p_bf,
                    'season_pitching_h',    sm.max_p_h,
                    'season_pitching_bb',   sm.max_p_bb
                )
            )
        ) as max_stats_by_season,
        jsonb_build_object(
            'g',    sum(ss.games_played),
            'ab',   sum(ss.ab),
            'h',    sum(ss.h),
            'hr',   sum(ss.hr),
            'rbi',  sum(ss.rbi),
            'r',    sum(ss.r),
            'bb',   sum(ss.bb),
            'sb',   sum(ss.sb)
        ) as career_batting,
        jsonb_build_object(
            'ip',   round(sum(ss.p_outs)::numeric / 3, 1),
            'era',  case when sum(ss.p_outs) > 0 then round(sum(ss.p_er)::numeric * 9 / (sum(ss.p_outs)::numeric / 3), 2) else null end,
            'w',    sum(ss.p_w),
            'l',    sum(ss.p_l),
            'sv',   sum(ss.p_sv),
            'so',   sum(ss.p_so),
            'bb',   sum(ss.p_bb)
        ) as career_pitching
    from season_stats ss
    left join {{ ref('dim_teams') }} dt on ss.team_id = dt.team_id
    left join season_maxes sm on ss.season = sm.season
    group by ss.player_id
),

-- 7. AGGREGATE GAME LOGS JSON
player_logs_agg as (
    select
        pg.player_id,
        jsonb_agg(
            jsonb_build_object(
                'game_pk',          pg.game_pk,
                'season',           pg.season,
                'official_date',    pg.official_date,
                'round_label',      pg.round_label,
                'team_abbreviation',dt.team_abbreviation,
                'batting_ab',       pg.batting_ab,
                'batting_h',        pg.batting_h,
                'batting_hr',       pg.batting_hr,
                'batting_rbi',      pg.batting_rbi,
                'batting_bb',       pg.batting_bb,
                'batting_so',       pg.batting_so,
                'batting_sb',       pg.batting_sb,
                'pitching_ip',      round(pg.pitching_outs::numeric / 3, 1),
                'pitching_er',      pg.pitching_er,
                'pitching_so',      pg.pitching_so,
                'pitching_bb',      pg.pitching_bb,
                'pitching_h',       pg.pitching_h,
                'pitching_w',       pg.pitching_w,
                'pitching_l',       pg.pitching_l,
                'pitching_sv',      pg.pitching_sv,
                '_gr', jsonb_build_object(
                    'game_pk',                  gr.game_pk,
                    'official_date',            pg.official_date,
                    'round_label',              pg.round_label,
                    'away_team_abbreviation',   gr.away_team_abbreviation,
                    'home_team_abbreviation',   gr.home_team_abbreviation,
                    'away_score',               gr.away_score,
                    'home_score',               gr.home_score
                )
            ) order by pg.season desc, pg.official_date asc
        ) as game_logs
    from player_games pg
    left join {{ ref('dim_teams') }} dt on pg.team_id = dt.team_id
    left join game_results gr on pg.game_pk = gr.game_pk
    group by pg.player_id
)

-- 8. FINAL ASSEMBLY
select
    dp.player_id                                    as person_id,
    dp.full_name,
    dp.first_name,
    dp.last_name,
    dp.use_name,
    dp.primary_position_type                        as position_type,
    dp.primary_position_abbreviation                as position_abbreviation,
    lt_dt.team_abbreviation                         as team_abbreviation,
    lt_dt.team_abbreviation                         as represented_country,
    dp.birth_date,
    dp.birth_city,
    dp.birth_country,
    dp.current_age,
    dp.mlb_debut_date,
    dp.height,
    dp.weight,
    dp.bat_side_code                                as bat_side,
    dp.pitch_hand_code                              as pitch_hand,
    dp.primary_number                               as jersey_number,
    dp.strike_zone_top,
    dp.strike_zone_bottom,
    dp.active,
    psa.tournament_stats,
    pla.game_logs,
    psa.max_stats_by_season,
    psa.career_batting,
    psa.career_pitching
from {{ ref('dim_players') }} dp
inner join player_seasons_agg psa on dp.player_id = psa.player_id
left join player_logs_agg pla on dp.player_id = pla.player_id
left join latest_team lt on dp.player_id = lt.player_id
left join {{ ref('dim_teams') }} lt_dt on lt.team_id = lt_dt.team_id
