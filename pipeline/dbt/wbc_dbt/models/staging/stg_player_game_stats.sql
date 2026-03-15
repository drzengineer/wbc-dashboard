with games as (
    select
        g.game_pk,
        g.data,
        -- season and official_date live in the data blob, not as top-level columns
        (s.data->>'season')::int            as season,
        (s.data->>'officialDate')::date     as official_date
    from raw.games g
    join raw.schedule s on g.game_pk = s.game_pk
    -- Only process completed games — scheduled games have empty {} players object
    -- Live games are excluded intentionally: partial-game seasonStats would poison
    -- tournament leaderboards. Stats for live games appear after re-ingestion.
    where s.data->'status'->>'abstractGameState' = 'Final'
),

away_players as (
    select
        g.game_pk,
        g.season,
        g.official_date,
        'away'                                              as team_side,
        -- Strip 'ID' prefix from key e.g. 'ID464277' → 464277
        regexp_replace(p.key, '^ID', '')::int               as person_id,
        p.value                                             as player_data,
        g.data->'teams'->'away'->'team'->>'abbreviation'   as team_abbreviation,
        g.data->'teams'->'away'->'team'->>'name'            as team_name
    from games g,
    jsonb_each(g.data->'teams'->'away'->'players') as p(key, value)
),

home_players as (
    select
        g.game_pk,
        g.season,
        g.official_date,
        'home'                                              as team_side,
        regexp_replace(p.key, '^ID', '')::int               as person_id,
        p.value                                             as player_data,
        g.data->'teams'->'home'->'team'->>'abbreviation'   as team_abbreviation,
        g.data->'teams'->'home'->'team'->>'name'            as team_name
    from games g,
    jsonb_each(g.data->'teams'->'home'->'players') as p(key, value)
),

all_players as (
    select * from away_players
    union all
    select * from home_players
),

flattened as (
    select
        game_pk,
        season,
        official_date,
        team_side,
        team_abbreviation,
        team_name,
        -- represented_country = the WBC country this player played for
        -- NOT the same as birth_country in raw.players which is birthplace only
        -- e.g. a Dominican-born player can represent the USA
        team_name                                                       as represented_country,
        person_id,

        player_data->'person'->>'fullName'                              as full_name,
        player_data->'position'->>'abbreviation'                        as position_abbreviation,
        player_data->'position'->>'type'                                as position_type,
        nullif(player_data->>'jerseyNumber', '')                        as jersey_number,

        -- batting_order: MLB API stores as position * 100 (e.g. 600 = 6th batter)
        -- raw value preserved for reference; divided by 100 for display
        -- nullif(..., 0) converts API value of 0 (= no order assigned) to NULL
        nullif(player_data->>'battingOrder', '')::int                   as batting_order_raw,
        nullif(nullif(player_data->>'battingOrder', '')::int / 100, 0) as batting_order,

        case
            when player_data->'gameStatus' is not null
                then (player_data->'gameStatus'->>'isOnBench')::boolean
            else null
        end                                                             as is_on_bench,
        case
            when player_data->'gameStatus' is not null
                then (player_data->'gameStatus'->>'isSubstitute')::boolean
            else null
        end                                                             as is_substitute,

        -- ── single-game batting ──────────────────────────────────────────────
        -- stats.batting is {} for pitchers who didn't bat — all fields null
        -- batting_ prefix used throughout: a single row has both batting and
        -- pitching stats and the prefix removes all ambiguity (e.g. batting_so
        -- vs pitching_so are clearly distinct)
        nullif(player_data->'stats'->'batting'->>'atBats',      '')::int    as batting_ab,
        nullif(player_data->'stats'->'batting'->>'hits',        '')::int    as batting_h,
        nullif(player_data->'stats'->'batting'->>'doubles',     '')::int    as batting_2b,
        nullif(player_data->'stats'->'batting'->>'triples',     '')::int    as batting_3b,
        nullif(player_data->'stats'->'batting'->>'homeRuns',    '')::int    as batting_hr,
        nullif(player_data->'stats'->'batting'->>'rbi',         '')::int    as batting_rbi,
        nullif(player_data->'stats'->'batting'->>'runs',        '')::int    as batting_r,
        nullif(player_data->'stats'->'batting'->>'baseOnBalls', '')::int    as batting_bb,
        nullif(player_data->'stats'->'batting'->>'strikeOuts',  '')::int    as batting_so,
        nullif(player_data->'stats'->'batting'->>'stolenBases', '')::int    as batting_sb,
        nullif(player_data->'stats'->'batting'->>'leftOnBase',  '')::int    as batting_lob,
        nullif(player_data->'stats'->'batting'->>'sacFlies',    '')::int    as batting_sf,
        nullif(player_data->'stats'->'batting'->>'hitByPitch',  '')::int    as batting_hbp,

        -- ── single-game pitching ─────────────────────────────────────────────
        -- stats.pitching is {} for position players — all fields null
        -- pitching_ prefix mirrors batting_ convention above
        --
        -- IP conversion: inningsPitched uses baseball outs notation
        --   "4.2" = 4 innings + 2 outs = 4.6667 real innings
        --   digit after decimal is outs (0/1/2), NOT a decimal fraction
        --   "0.2" ≠ 0.2 innings — it means 2 outs = 0.6667 innings
        --
        -- Crash protection: if API returns whole number with no decimal e.g. "9",
        -- split_part returns '' for part 2. COALESCE converts '' → '0' before cast.
        nullif(player_data->'stats'->'pitching'->>'inningsPitched', '')     as pitching_ip_raw,
        case
            when nullif(player_data->'stats'->'pitching'->>'inningsPitched', '') is not null
            then round(
                split_part(player_data->'stats'->'pitching'->>'inningsPitched', '.', 1)::numeric
                + coalesce(nullif(split_part(player_data->'stats'->'pitching'->>'inningsPitched', '.', 2), ''), '0')::numeric / 3.0,
                4
            )
            else null
        end                                                                 as pitching_ip,
        nullif(player_data->'stats'->'pitching'->>'earnedRuns',    '')::int as pitching_er,
        nullif(player_data->'stats'->'pitching'->>'runs',          '')::int as pitching_r,
        nullif(player_data->'stats'->'pitching'->>'strikeOuts',    '')::int as pitching_so,
        nullif(player_data->'stats'->'pitching'->>'baseOnBalls',   '')::int as pitching_bb,
        nullif(player_data->'stats'->'pitching'->>'hits',          '')::int as pitching_h,
        nullif(player_data->'stats'->'pitching'->>'homeRuns',      '')::int as pitching_hr,
        nullif(player_data->'stats'->'pitching'->>'battersFaced',  '')::int as pitching_bf,
        -- win/loss/save: API returns as strings "0" or "1", cast to int
        nullif(player_data->'stats'->'pitching'->>'wins',          '')::int as pitching_w,
        nullif(player_data->'stats'->'pitching'->>'losses',        '')::int as pitching_l,
        nullif(player_data->'stats'->'pitching'->>'saves',         '')::int as pitching_sv,

        -- ── tournament cumulative batting (seasonStats) ──────────────────────
        -- seasonStats accumulate across games within a tournament.
        -- A player's seasonStats in game 3 = their totals through game 3.
        -- Take from the player's LAST game to get complete tournament totals.
        -- See player_tournament_stats for how last-game selection works.
        nullif(player_data->'seasonStats'->'batting'->>'avg',        '')    as season_batting_avg,
        nullif(player_data->'seasonStats'->'batting'->>'obp',        '')    as season_batting_obp,
        nullif(player_data->'seasonStats'->'batting'->>'slg',        '')    as season_batting_slg,
        nullif(player_data->'seasonStats'->'batting'->>'ops',        '')    as season_batting_ops,
        nullif(player_data->'seasonStats'->'batting'->>'atBats',     '')::int as season_batting_ab,
        nullif(player_data->'seasonStats'->'batting'->>'hits',       '')::int as season_batting_h,
        nullif(player_data->'seasonStats'->'batting'->>'homeRuns',   '')::int as season_batting_hr,
        nullif(player_data->'seasonStats'->'batting'->>'rbi',        '')::int as season_batting_rbi,
        nullif(player_data->'seasonStats'->'batting'->>'runs',       '')::int as season_batting_r,
        nullif(player_data->'seasonStats'->'batting'->>'baseOnBalls','')::int as season_batting_bb,
        nullif(player_data->'seasonStats'->'batting'->>'strikeOuts', '')::int as season_batting_so,
        nullif(player_data->'seasonStats'->'batting'->>'stolenBases','')::int as season_batting_sb,

        -- ── tournament cumulative pitching (seasonStats) ─────────────────────
        -- Same IP crash protection as single-game block above.
        nullif(player_data->'seasonStats'->'pitching'->>'inningsPitched', '') as season_pitching_ip_raw,
        case
            when nullif(player_data->'seasonStats'->'pitching'->>'inningsPitched', '') is not null
            then round(
                split_part(player_data->'seasonStats'->'pitching'->>'inningsPitched', '.', 1)::numeric
                + coalesce(nullif(split_part(player_data->'seasonStats'->'pitching'->>'inningsPitched', '.', 2), ''), '0')::numeric / 3.0,
                4
            )
            else null
        end                                                                   as season_pitching_ip,
        nullif(player_data->'seasonStats'->'pitching'->>'era',         '')   as season_pitching_era,
        nullif(player_data->'seasonStats'->'pitching'->>'wins',        '')::int as season_pitching_w,
        nullif(player_data->'seasonStats'->'pitching'->>'losses',      '')::int as season_pitching_l,
        nullif(player_data->'seasonStats'->'pitching'->>'saves',       '')::int as season_pitching_sv,
        nullif(player_data->'seasonStats'->'pitching'->>'strikeOuts',  '')::int as season_pitching_so,
        nullif(player_data->'seasonStats'->'pitching'->>'baseOnBalls', '')::int as season_pitching_bb,
        nullif(player_data->'seasonStats'->'pitching'->>'battersFaced','')::int as season_pitching_bf

    from all_players
)

select * from flattened
