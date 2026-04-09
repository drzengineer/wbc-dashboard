/*
    app_game_detail
    ---------------
    Purpose: Single-query, frontend-ready game detail payload.
             One row per player per game, carrying all game context, both
             team-level stats (home and away), inning-by-inning breakdowns,
             and full player bio + per-game stats. The frontend does zero
             joining — it filters, groups, and renders only.

    Grain: game_pk + player_id
    Sources:
        app_game_results       – pivoted game header (scores, innings, RHE, flags)
        fct_team_game_stats    – full team batting / pitching / fielding counts
        fct_player_game_stats  – full player batting / pitching / fielding counts
        dim_players            – player biographical attributes

    Design decisions:
        - The grain is player × game rather than game because the frontend
          needs one query to populate every section of the detail panel
          (game header, box score, team stats comparison, batting lineups,
          pitching lines, bench) without a second round-trip.

        - Team-level stats for both home and away are denormalised onto
          every player row as `away_team_*` / `home_team_*` columns. This
          is intentional: the frontend picks a single game's rows, then
          reads the team columns off row[0]. No aggregation needed on the
          client side.

        - Inning arrays (away_innings, home_innings) and RHE totals come
          from app_game_results which already pivots them. They are passed
          through here unchanged.

        - Player rows whose batting_order IS NULL AND pitching_outs IS NULL
          AND is_on_bench IS FALSE represent players that appeared in the
          API boxscore roster but recorded no plate appearances or pitching
          activity. They are still included so the frontend can render a
          complete roster / bench section.

        - This model is materialised as a table (not a view) so Supabase
          can apply RLS policies and the frontend query is a simple
          .select('*').eq('game_pk', x) with no server-side joins.
*/

{{
    config(
        materialized = 'table',
        indexes = [
            {'columns': ['game_pk']},
            {'columns': ['game_pk', 'team_id']},
            {'columns': ['game_pk', 'player_id'], 'unique': true}
        ]
    )
}}

with

-- ─── game header ──────────────────────────────────────────────────────────────
-- One row per game: scores, inning arrays, RHE totals, flags, venue, round.
game_header as (

    select
        game_pk,
        season,
        official_date,
        game_type,
        round_label,
        round_order,

        away_team_name,
        away_team_abbreviation,
        away_score,
        away_is_winner,

        home_team_name,
        home_team_abbreviation,
        home_score,
        home_is_winner,

        is_mercy_rule,
        venue_name,
        pool_group,
        is_one_run_game,
        run_margin,
        total_runs,

        -- inning arrays & RHE totals (already pivoted in app_game_results)
        away_innings,
        home_innings,
        away_r,
        away_h,
        away_e,
        home_r,
        home_h,
        home_e

    from {{ ref('app_game_results') }}

),

-- ─── team stats (both sides) ─────────────────────────────────────────────────
-- Full batting / pitching / fielding aggregates for each team per game.
-- Self-joined so every player row can carry both teams' stats for comparison.
team_stats_raw as (

    select
        game_pk,
        team_id,
        side,

        -- identification
        team_name,
        team_abbreviation,
        is_winner,
        score,
        opponent_score,
        run_differential,

        -- box score line
        hits,
        errors,
        left_on_base,

        -- batting totals
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

        -- pitching totals
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

        -- fielding totals
        fielding_errors,
        fielding_assists,
        fielding_put_outs,
        fielding_chances,
        fielding_passed_balls,
        fielding_pickoffs

    from {{ ref('fct_team_game_stats') }}

),

away_team_stats as (
    select * from team_stats_raw where side = 'away'
),

home_team_stats as (
    select * from team_stats_raw where side = 'home'
),

-- ─── player stats ─────────────────────────────────────────────────────────────
player_stats as (

    select
        game_pk,
        player_id,
        team_id,

        -- roster role
        batting_order,
        is_on_bench,
        is_substitute,
        is_current_batter,
        is_current_pitcher,

        -- batting
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
        batting_ground_outs,
        batting_air_outs,
        batting_pickoffs,

        -- pitching
        pitching_outs,
        pitching_total_pitches,
        pitching_strikes,
        pitching_balls,
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
        pitching_batters_faced,
        pitching_inherited_runners,
        pitching_inherited_runners_scored,
        pitching_wins,
        pitching_losses,
        pitching_saves,
        pitching_holds,
        pitching_blown_saves,
        pitching_games_started,

        -- fielding
        fielding_errors,
        fielding_assists,
        fielding_put_outs,
        fielding_chances,
        fielding_passed_balls,
        fielding_pickoffs

    from {{ ref('fct_player_game_stats') }}

),

-- ─── player bio ───────────────────────────────────────────────────────────────
player_bio as (

    select
        player_id,
        full_name,
        first_name,
        last_name,
        use_name,
        boxscore_name,
        birth_date,
        birth_city,
        birth_country,
        current_age,
        height,
        weight,
        bat_side_code,
        pitch_hand_code,
        primary_number,
        primary_position_code,
        primary_position_name,
        primary_position_type,
        primary_position_abbreviation,
        mlb_debut_date,
        current_team_id
    from {{ ref('dim_players') }}

),

-- ─── final assembly ───────────────────────────────────────────────────────────
final as (

    select

        -- ── grain keys ──────────────────────────────────────────────────────
        ps.game_pk,
        ps.player_id,
        ps.team_id,

        -- ── game header (same on every row for this game_pk) ────────────────
        gh.season,
        gh.official_date,
        gh.game_type,
        gh.round_label,
        gh.round_order,
        gh.venue_name,
        gh.pool_group,
        gh.is_mercy_rule,
        gh.is_one_run_game,
        gh.run_margin,
        gh.total_runs,

        -- away team identity
        gh.away_team_name,
        gh.away_team_abbreviation,
        gh.away_score,
        gh.away_is_winner,

        -- home team identity
        gh.home_team_name,
        gh.home_team_abbreviation,
        gh.home_score,
        gh.home_is_winner,

        -- inning arrays & RHE totals
        gh.away_innings,
        gh.home_innings,
        gh.away_r,
        gh.away_h,
        gh.away_e,
        gh.home_r,
        gh.home_h,
        gh.home_e,

        -- ── away team stats (denormalised for side-by-side comparison) ──────
        ats.team_id                             as away_team_id,
        ats.is_winner                           as away_team_is_winner,
        ats.run_differential                    as away_run_differential,
        ats.left_on_base                        as away_left_on_base,
        -- batting
        ats.batting_plate_appearances           as away_batting_pa,
        ats.batting_at_bats                     as away_batting_ab,
        ats.batting_runs                        as away_batting_runs,
        ats.batting_hits                        as away_batting_hits,
        ats.batting_doubles                     as away_batting_doubles,
        ats.batting_triples                     as away_batting_triples,
        ats.batting_home_runs                   as away_batting_hr,
        ats.batting_rbi                         as away_batting_rbi,
        ats.batting_walks                       as away_batting_bb,
        ats.batting_intentional_walks           as away_batting_ibb,
        ats.batting_strikeouts                  as away_batting_so,
        ats.batting_hit_by_pitch                as away_batting_hbp,
        ats.batting_sac_bunts                   as away_batting_sac,
        ats.batting_sac_flies                   as away_batting_sf,
        ats.batting_stolen_bases                as away_batting_sb,
        ats.batting_caught_stealing             as away_batting_cs,
        ats.batting_left_on_base                as away_batting_lob,
        ats.batting_total_bases                 as away_batting_tb,
        ats.batting_gidp                        as away_batting_gidp,
        -- pitching
        ats.pitching_outs                       as away_pitching_outs,
        ats.pitching_total_pitches              as away_pitching_total_pitches,
        ats.pitching_strikes                    as away_pitching_strikes,
        ats.pitching_balls                      as away_pitching_balls,
        ats.pitching_hits_allowed               as away_pitching_hits_allowed,
        ats.pitching_runs_allowed               as away_pitching_runs_allowed,
        ats.pitching_earned_runs                as away_pitching_er,
        ats.pitching_home_runs_allowed          as away_pitching_hr_allowed,
        ats.pitching_strikeouts                 as away_pitching_so,
        ats.pitching_walks                      as away_pitching_bb,
        ats.pitching_hit_batsmen                as away_pitching_hbp,
        ats.pitching_wild_pitches               as away_pitching_wp,
        ats.pitching_balks                      as away_pitching_bk,
        ats.pitching_batters_faced              as away_pitching_bf,
        -- fielding
        ats.fielding_errors                     as away_fielding_errors,
        ats.fielding_assists                    as away_fielding_assists,
        ats.fielding_put_outs                   as away_fielding_put_outs,
        ats.fielding_chances                    as away_fielding_chances,
        ats.fielding_passed_balls               as away_fielding_passed_balls,
        ats.fielding_pickoffs                   as away_fielding_pickoffs,

        -- ── home team stats ─────────────────────────────────────────────────
        hts.team_id                             as home_team_id,
        hts.is_winner                           as home_team_is_winner,
        hts.run_differential                    as home_run_differential,
        hts.left_on_base                        as home_left_on_base,
        -- batting
        hts.batting_plate_appearances           as home_batting_pa,
        hts.batting_at_bats                     as home_batting_ab,
        hts.batting_runs                        as home_batting_runs,
        hts.batting_hits                        as home_batting_hits,
        hts.batting_doubles                     as home_batting_doubles,
        hts.batting_triples                     as home_batting_triples,
        hts.batting_home_runs                   as home_batting_hr,
        hts.batting_rbi                         as home_batting_rbi,
        hts.batting_walks                       as home_batting_bb,
        hts.batting_intentional_walks           as home_batting_ibb,
        hts.batting_strikeouts                  as home_batting_so,
        hts.batting_hit_by_pitch                as home_batting_hbp,
        hts.batting_sac_bunts                   as home_batting_sac,
        hts.batting_sac_flies                   as home_batting_sf,
        hts.batting_stolen_bases                as home_batting_sb,
        hts.batting_caught_stealing             as home_batting_cs,
        hts.batting_left_on_base                as home_batting_lob,
        hts.batting_total_bases                 as home_batting_tb,
        hts.batting_gidp                        as home_batting_gidp,
        -- pitching
        hts.pitching_outs                       as home_pitching_outs,
        hts.pitching_total_pitches              as home_pitching_total_pitches,
        hts.pitching_strikes                    as home_pitching_strikes,
        hts.pitching_balls                      as home_pitching_balls,
        hts.pitching_hits_allowed               as home_pitching_hits_allowed,
        hts.pitching_runs_allowed               as home_pitching_runs_allowed,
        hts.pitching_earned_runs                as home_pitching_er,
        hts.pitching_home_runs_allowed          as home_pitching_hr_allowed,
        hts.pitching_strikeouts                 as home_pitching_so,
        hts.pitching_walks                      as home_pitching_bb,
        hts.pitching_hit_batsmen                as home_pitching_hbp,
        hts.pitching_wild_pitches               as home_pitching_wp,
        hts.pitching_balks                      as home_pitching_bk,
        hts.pitching_batters_faced              as home_pitching_bf,
        -- fielding
        hts.fielding_errors                     as home_fielding_errors,
        hts.fielding_assists                    as home_fielding_assists,
        hts.fielding_put_outs                   as home_fielding_put_outs,
        hts.fielding_chances                    as home_fielding_chances,
        hts.fielding_passed_balls               as home_fielding_passed_balls,
        hts.fielding_pickoffs                   as home_fielding_pickoffs,

        -- ── player bio ──────────────────────────────────────────────────────
        pb.full_name,
        pb.first_name,
        pb.last_name,
        pb.use_name,
        pb.boxscore_name,
        pb.birth_date,
        pb.birth_city,
        pb.birth_country,
        pb.current_age,
        pb.height,
        pb.weight,
        pb.bat_side_code,
        pb.pitch_hand_code,
        pb.primary_number,
        pb.primary_position_code,
        pb.primary_position_name,
        pb.primary_position_type,
        pb.primary_position_abbreviation,
        pb.mlb_debut_date,

        -- ── player game role ────────────────────────────────────────────────
        ps.batting_order,
        ps.is_on_bench,
        ps.is_substitute,
        ps.is_current_batter,
        ps.is_current_pitcher,

        -- ── player batting stats ────────────────────────────────────────────
        ps.batting_plate_appearances            as player_batting_pa,
        ps.batting_at_bats                      as player_batting_ab,
        ps.batting_runs                         as player_batting_runs,
        ps.batting_hits                         as player_batting_hits,
        ps.batting_doubles                      as player_batting_doubles,
        ps.batting_triples                      as player_batting_triples,
        ps.batting_home_runs                    as player_batting_hr,
        ps.batting_rbi                          as player_batting_rbi,
        ps.batting_walks                        as player_batting_bb,
        ps.batting_intentional_walks            as player_batting_ibb,
        ps.batting_strikeouts                   as player_batting_so,
        ps.batting_hit_by_pitch                 as player_batting_hbp,
        ps.batting_sac_bunts                    as player_batting_sac,
        ps.batting_sac_flies                    as player_batting_sf,
        ps.batting_stolen_bases                 as player_batting_sb,
        ps.batting_caught_stealing              as player_batting_cs,
        ps.batting_left_on_base                 as player_batting_lob,
        ps.batting_total_bases                  as player_batting_tb,
        ps.batting_gidp                         as player_batting_gidp,

        -- ── player pitching stats ───────────────────────────────────────────
        ps.pitching_outs                        as player_pitching_outs,
        ps.pitching_total_pitches               as player_pitching_total_pitches,
        ps.pitching_strikes                     as player_pitching_strikes,
        ps.pitching_balls                       as player_pitching_balls,
        ps.pitching_hits_allowed                as player_pitching_hits_allowed,
        ps.pitching_runs_allowed                as player_pitching_runs_allowed,
        ps.pitching_earned_runs                 as player_pitching_er,
        ps.pitching_home_runs_allowed           as player_pitching_hr_allowed,
        ps.pitching_strikeouts                  as player_pitching_so,
        ps.pitching_walks                       as player_pitching_bb,
        ps.pitching_intentional_walks           as player_pitching_ibb,
        ps.pitching_hit_batsmen                 as player_pitching_hbp,
        ps.pitching_wild_pitches                as player_pitching_wp,
        ps.pitching_balks                       as player_pitching_bk,
        ps.pitching_batters_faced               as player_pitching_bf,
        ps.pitching_inherited_runners           as player_pitching_ir,
        ps.pitching_inherited_runners_scored    as player_pitching_irs,
        ps.pitching_wins                        as player_pitching_wins,
        ps.pitching_losses                      as player_pitching_losses,
        ps.pitching_saves                       as player_pitching_saves,
        ps.pitching_holds                       as player_pitching_holds,
        ps.pitching_blown_saves                 as player_pitching_bs,
        ps.pitching_games_started               as player_pitching_gs,

        -- ── player fielding stats ───────────────────────────────────────────
        ps.fielding_errors                      as player_fielding_errors,
        ps.fielding_assists                     as player_fielding_assists,
        ps.fielding_put_outs                    as player_fielding_put_outs,
        ps.fielding_chances                     as player_fielding_chances,
        ps.fielding_passed_balls                as player_fielding_passed_balls,
        ps.fielding_pickoffs                    as player_fielding_pickoffs

    from player_stats ps
    inner join game_header gh
        on ps.game_pk = gh.game_pk
    inner join away_team_stats ats
        on ps.game_pk = ats.game_pk
    inner join home_team_stats hts
        on ps.game_pk = hts.game_pk
    left join player_bio pb
        on ps.player_id = pb.player_id

)

select * from final
order by game_pk, team_id, batting_order nulls last, player_pitching_outs desc nulls last
