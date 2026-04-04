-- ============================================================
-- game_results
-- One row per game across all WBC seasons (2006-2026)
-- Source: stg_schedule (which joins raw.schedule + raw.games for abbreviations)
--
-- Key code reference:
--   game_type: F=Pool Play, D=Second Round (2006-2017) or Quarterfinals (2023+)
--              L=Semifinals, W=Championship
--   round_order: 1=Pool Play, 2=Second Round/QF, 3=Semis, 4=Championship
--   pool_label: letter (A/B/C/D) for round 1 pools
--               number (1/2) or letter (E/F) for round 2 pools (2006-2017 only)
--               NULL for all knockout rounds (QF/SF/Final)
--   pool_display: human-readable pool label e.g. 'Pool A', 'Second Round Pool 1'
--   tournament_format: pool_then_second_round (2006-2017)
--                      pool_then_quarterfinals (2023+)
--   away_score/home_score: NULL on unplayed games (field absent in API, not zero)
--   away_team_is_placeholder: true when team not yet determined
--     NOTE: unreliable for 2026 semis/final — use away_score IS NULL as the
--     authoritative signal that a game hasn't been played
-- ============================================================

with base as (
    select * from {{ ref('int_games') }}
)

select
    game_pk,
    season,
    official_date,
    day_night,

    -- raw round code from MLB API (F/D/L/W)
    game_type,

    -- human-readable round label
    -- D means different things by season: Second Round (2006-2017) vs Quarterfinals (2023+)
    case
        when game_type = 'F'                        then 'Pool Play'
        when game_type = 'D' and season >= 2023     then 'Quarterfinals'
        when game_type = 'D' and season <  2023     then 'Second Round'
        when game_type = 'L'                        then 'Semifinals'
        when game_type = 'W'                        then 'Championship'
        else game_type
    end                                             as round_label,

    -- integer sort order for frontend (consistent across all season formats)
    case game_type
        when 'F' then 1
        when 'D' then 2
        when 'L' then 3
        when 'W' then 4
    end                                             as round_order,

    -- bracket template selector for frontend
    -- pool_then_second_round: D games are round-robin pools (2006-2017)
    -- pool_then_quarterfinals: D games are single-elim knockouts (2023+)
    case
        when season in (2006, 2009, 2013, 2017) then 'pool_then_second_round'
        when season in (2023, 2026)             then 'pool_then_quarterfinals'
        else 'unknown'
    end                                             as tournament_format,

    -- raw pool identifier — letter (A/B/C/D/E/F) or number (1/2), NULL for knockouts
    -- anchored regex prevents matching pool refs inside QF descriptions e.g.
    -- "Quarterfinal 1: Pool C Runner-Up vs. Pool D Winner" → NULL (correct)
    -- "WBC Pool A: Seoul - Game 1" → 'A' (correct)
    case
        when description ~* '^(WBC\s+)?Pool\s+[A-Z0-9]'
        then regexp_replace(description, '(?i)^(?:WBC\s+)?Pool\s+([A-Z0-9]).*', '\1')
        else null
    end                                             as pool_label,

    -- human-readable pool label for display
    -- distinguishes first round pools from second round pools
    case
        when game_type = 'F'
            and description ~* '^(WBC\s+)?Pool\s+[A-Z0-9]'
            then 'Pool ' || regexp_replace(description, '(?i)^(?:WBC\s+)?Pool\s+([A-Z0-9]).*', '\1')
        when game_type = 'D'
            and description ~* '^(WBC\s+)?Pool\s+[A-Z0-9]'
            then 'Second Round Pool ' || regexp_replace(description, '(?i)^(?:WBC\s+)?Pool\s+([A-Z0-9]).*', '\1')
        else null
    end                                             as pool_display,

    -- teams
    away_team_name,
    away_team_abbreviation,
    away_team_id,
    home_team_name,
    home_team_abbreviation,
    home_team_id,

    -- scores (NULL on unplayed games — absent in API, not zero)
    away_score,
    home_score,

    -- Boxscore summary totals (new! from int_games)
    away_hits,
    away_errors,
    away_left_on_base,
    home_hits,
    home_errors,
    home_left_on_base,

    -- winner flags (NULL on unplayed games)
    away_is_winner,
    home_is_winner,
    case
        when home_is_winner = true then home_team_name
        when away_is_winner = true then away_team_name
        else null
    end                                             as winning_team_name,
    case
        when home_is_winner = true then home_team_abbreviation
        when away_is_winner = true then away_team_abbreviation
        else null
    end                                             as winning_team_abbreviation,

    -- absolute score margin (NULL on unplayed games)
    case
        when away_score is not null and home_score is not null
        then abs(away_score - home_score)
        else null
    end                                             as run_margin,

    -- game status
    abstract_game_state,
    detailed_state,
    is_mercy_rule,

    -- venue and descriptions
    venue_name,
    -- raw description preserved for:
    --   a) bracket display on unplayed games e.g. "Quarterfinal 2: Pool B Runner-Up vs. Pool A Winner"
    --   b) game context on completed games
    description,
    series_description,
    if_necessary,

    -- placeholder flags (true when team not yet determined)
    -- NOTE: away_team_is_placeholder unreliable for 2026 semis/final
    -- use away_score IS NULL as authoritative unplayed game signal instead
    away_team_is_placeholder,
    home_team_is_placeholder

from base
order by season, round_order, official_date, game_pk
