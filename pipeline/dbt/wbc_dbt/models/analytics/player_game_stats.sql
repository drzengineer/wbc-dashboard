-- ============================================================
-- player_game_stats
-- One row per player per game
-- Source: stg_player_game_stats left joined to stg_players for bio enrichment
--
-- Column naming convention:
--   batting_*  : single-game batting stats (batting_ab, batting_h, batting_hr ...)
--   pitching_* : single-game pitching stats (pitching_ip, pitching_er, pitching_so ...)
--   season_*   : cumulative tournament totals from seasonStats (in player_tournament_stats)
--
-- Key notes:
--   represented_country: WBC country the player played for — derived from
--     team_name in the boxscore, NOT birthCountry from raw.players
--   batting_order: position in lineup (1–9), NULL for pitchers/bench/no order assigned
--   batting_order_raw: original API value (position × 100, e.g. 600 = 6th batter)
--   bio columns (birth_date, birth_country, height etc): sourced from stg_players —
--     will be NULL if player not found in raw.players (coverage gap, not a bug)
--   batting_avg: computed from batting_h / batting_ab for this game only
--   pitching_era: computed as 9 * ER / IP for this game only
--     pitching_er coalesced to 0 — a pitcher who allowed 0 earned runs has ERA 0.00,
--     not null. null ERA only when IP = 0 (pitcher recorded no outs) or IP is null.
--   pitching_ip: decimal innings (e.g. 4.6667 = "4.2" in baseball notation)
--   pitching_ip_raw: original string from API e.g. "4.2"
-- ============================================================

with game_stats as (
    select * from {{ ref('stg_player_game_stats') }}
),

players as (
    select * from {{ ref('stg_players') }}
)

select
    gs.game_pk,
    gs.season,
    gs.official_date,
    gs.team_side,
    gs.team_abbreviation,
    gs.team_name,
    gs.represented_country,
    gs.person_id,
    gs.full_name,

    -- bio from stg_players (left join — null if player not in raw.players)
    p.birth_date,
    p.birth_country,
    p.bat_side,
    p.pitch_hand,
    gs.position_abbreviation,
    gs.position_type,
    p.height,
    p.weight,
    p.mlb_debut_date,

    -- game context
    gs.jersey_number,
    gs.batting_order,
    gs.batting_order_raw,
    gs.is_on_bench,
    gs.is_substitute,

    -- single-game batting
    gs.batting_ab,
    gs.batting_h,
    gs.batting_2b,
    gs.batting_3b,
    gs.batting_hr,
    gs.batting_rbi,
    gs.batting_r,
    gs.batting_bb,
    gs.batting_so,
    gs.batting_sb,
    gs.batting_lob,
    gs.batting_sf,
    gs.batting_hbp,

    -- computed batting average for this game (null if no at bats)
    case
        when gs.batting_ab > 0 then round(gs.batting_h::numeric / gs.batting_ab, 3)
        else null
    end                                                     as batting_avg,

    -- single-game pitching
    gs.pitching_ip_raw,
    gs.pitching_ip,
    gs.pitching_er,
    gs.pitching_r,
    gs.pitching_so,
    gs.pitching_bb,
    gs.pitching_h,
    gs.pitching_hr,
    gs.pitching_bf,
    gs.pitching_w,
    gs.pitching_l,
    gs.pitching_sv,

    -- computed ERA for this game (9 * ER / IP)
    -- coalesce(pitching_er, 0): a pitcher who allowed 0 earned runs has ERA 0.00,
    -- not null. only null when IP = 0 (no outs recorded) or IP is null entirely.
    case
        when gs.pitching_ip > 0
        then round((9.0 * coalesce(gs.pitching_er, 0) / gs.pitching_ip)::numeric, 2)
        else null
    end                                                     as pitching_era

from game_stats gs
left join players p on gs.person_id = p.person_id
