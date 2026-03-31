-- ============================================================
-- player_tournament_stats
-- One row per player per season — tournament leaderboard source
-- Source: stg_player_game_stats (seasonStats from last game) + stg_players for bio
--
-- Key notes:
--   seasonStats in the MLB API are cumulative — they accumulate across games
--   within a tournament. A player's seasonStats after game 3 = their totals
--   through game 3. We take seasonStats from each player's LAST game to get
--   their complete tournament totals.
--
--   DISTINCT ON (person_id, season) ORDER BY (person_id, season, game_pk DESC)
--   selects the last game row per player per season. game_pk DESC is a
--   deterministic tiebreaker in the edge case of multiple games on the same date
--   (nearly impossible in a tournament but theoretically possible). seasonStats
--   are cumulative so all tied rows have identical totals — any of them is correct,
--   but an explicit tiebreaker is better than relying on Postgres row ordering.
--
--   represented_country: WBC country played for this season — from boxscore team
--   birth_country: birthplace — from raw.players, NOT the same as represented_country
--
--   season_avg/obp/slg/ops/era: pre-computed by MLB API as strings e.g. ".342", "1.50"
--   season_ip: decimal innings (converted from baseball outs notation)
-- ============================================================

with game_stats as (
    select * from {{ ref('stg_player_game_stats') }}
),

players as (
    select * from {{ ref('stg_players') }}
),

-- count distinct games played per player per season
-- computed separately so it isn't collapsed by the DISTINCT ON in season_totals
games_played_counts as (
    select
        person_id,
        season,
        count(distinct game_pk) as games_played
    from game_stats
    group by person_id, season
),

-- take season stats from the last game only
-- DISTINCT ON + ORDER BY game_pk DESC picks the most recent game row per player per season
-- seasonStats are cumulative so the last game always has complete tournament totals
season_totals as (
    select distinct on (gs.person_id, gs.season)
        gs.person_id,
        gs.season,
        gs.team_abbreviation,
        gs.team_name,
        gs.represented_country,
        gs.full_name,
        gs.position_abbreviation,
        gs.position_type,

        -- tournament batting totals (season_ prefix = cumulative tournament total)
        gs.season_batting_avg,
        gs.season_batting_obp,
        gs.season_batting_slg,
        gs.season_batting_ops,
        gs.season_batting_ab,
        gs.season_batting_h,
        gs.season_batting_hr,
        gs.season_batting_rbi,
        gs.season_batting_r,
        gs.season_batting_bb,
        gs.season_batting_so,
        gs.season_batting_sb,

        -- tournament pitching totals
        gs.season_pitching_ip_raw,
        gs.season_pitching_ip,
        gs.season_pitching_era,
        gs.season_pitching_w,
        gs.season_pitching_l,
        gs.season_pitching_sv,
        gs.season_pitching_so,
        gs.season_pitching_bb,
        gs.season_pitching_bf

    from game_stats gs
    order by gs.person_id, gs.season, gs.official_date desc, gs.game_pk desc
)

select
    st.person_id,
    st.season,
    st.full_name,
    st.represented_country,
    st.team_name,
    st.team_abbreviation,
    st.position_abbreviation,
    st.position_type,
    gp.games_played,

    -- bio enrichment from stg_players
    -- birth_country is birthplace, NOT represented_country (which is WBC team)
    p.birth_date,
    p.birth_country,
    p.bat_side,
    p.pitch_hand,
    p.height,
    p.weight,
    p.mlb_debut_date,
    p.is_active,

    -- tournament batting totals
    st.season_batting_avg,
    st.season_batting_obp,
    st.season_batting_slg,
    st.season_batting_ops,
    st.season_batting_ab,
    st.season_batting_h,
    st.season_batting_hr,
    st.season_batting_rbi,
    st.season_batting_r,
    st.season_batting_bb,
    st.season_batting_so,
    st.season_batting_sb,

    -- tournament pitching totals
    st.season_pitching_ip_raw,
    st.season_pitching_ip,
    st.season_pitching_era,
    st.season_pitching_w,
    st.season_pitching_l,
    st.season_pitching_sv,
    st.season_pitching_so,
    st.season_pitching_bb,
    st.season_pitching_bf

from season_totals st
join games_played_counts gp
    on st.person_id = gp.person_id
    and st.season = gp.season
left join players p on st.person_id = p.person_id
