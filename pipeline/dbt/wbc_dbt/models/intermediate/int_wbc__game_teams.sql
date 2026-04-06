with schedule as (

    select * from {{ ref('stg_wbc__schedule') }}

),

boxscore as (

    select * from {{ ref('stg_wbc__boxscores') }}

),

-- unpivot schedule home/away into one row per team per game
schedule_unpivoted as (

    select
        game_pk,
        ingested_at,
        'away'                                                      as side,
        away_team_id                                                as team_id,
        trim(both '"' from away_team_name)                         as team_name,
        away_score                                                  as score,
        away_hits                                                   as hits,
        away_runs                                                   as runs,
        away_errors                                                 as errors,
        away_left_on_base                                           as left_on_base,
        away_is_winner                                             as is_winner,
        away_wins                                                   as wins,
        away_losses                                                 as losses,
        trim(both '"' from away_win_pct)::numeric                  as win_pct
    from schedule

    union all

    select
        game_pk,
        ingested_at,
        'home'                                                      as side,
        home_team_id                                                as team_id,
        trim(both '"' from home_team_name)                         as team_name,
        home_score                                                  as score,
        home_hits                                                   as hits,
        home_runs                                                   as runs,
        home_errors                                                 as errors,
        home_left_on_base                                           as left_on_base,
        home_is_winner                                             as is_winner,
        home_wins                                                   as wins,
        home_losses                                                 as losses,
        trim(both '"' from home_win_pct)::numeric                  as win_pct
    from schedule

),

-- extract team-level data from boxscore for both sides
boxscore_away as (

    select
        game_pk,
        away_team_id                                               as team_id,

        -- team identity from boxscore team object
        away_team_data->'team'->>'abbreviation'                    as team_abbreviation,
        away_team_data->'team'->'league'->>'name'                  as league_name,
        (away_team_data->'team'->'division'->>'id')::int           as division_id,
        away_team_data->'team'->'division'->>'name'                as division_name,

        -- team batting stats
        (away_team_data->'teamStats'->'batting'->>'atBats')::int          as batting_at_bats,
        (away_team_data->'teamStats'->'batting'->>'runs')::int            as batting_runs,
        (away_team_data->'teamStats'->'batting'->>'hits')::int            as batting_hits,
        (away_team_data->'teamStats'->'batting'->>'doubles')::int         as batting_doubles,
        (away_team_data->'teamStats'->'batting'->>'triples')::int         as batting_triples,
        (away_team_data->'teamStats'->'batting'->>'homeRuns')::int        as batting_home_runs,
        (away_team_data->'teamStats'->'batting'->>'rbi')::int             as batting_rbi,
        (away_team_data->'teamStats'->'batting'->>'baseOnBalls')::int     as batting_walks,
        (away_team_data->'teamStats'->'batting'->>'intentionalWalks')::int as batting_intentional_walks,
        (away_team_data->'teamStats'->'batting'->>'strikeOuts')::int      as batting_strikeouts,
        (away_team_data->'teamStats'->'batting'->>'hitByPitch')::int      as batting_hit_by_pitch,
        (away_team_data->'teamStats'->'batting'->>'sacBunts')::int        as batting_sac_bunts,
        (away_team_data->'teamStats'->'batting'->>'sacFlies')::int        as batting_sac_flies,
        (away_team_data->'teamStats'->'batting'->>'stolenBases')::int     as batting_stolen_bases,
        (away_team_data->'teamStats'->'batting'->>'caughtStealing')::int  as batting_caught_stealing,
        (away_team_data->'teamStats'->'batting'->>'leftOnBase')::int      as batting_left_on_base,
        (away_team_data->'teamStats'->'batting'->>'totalBases')::int      as batting_total_bases,
        (away_team_data->'teamStats'->'batting'->>'groundIntoDoublePlay')::int as batting_gidp,
        (away_team_data->'teamStats'->'batting'->>'plateAppearances')::int as batting_plate_appearances,

        -- team pitching stats
        (away_team_data->'teamStats'->'pitching'->>'outs')::int           as pitching_outs,
        (away_team_data->'teamStats'->'pitching'->>'hits')::int           as pitching_hits_allowed,
        (away_team_data->'teamStats'->'pitching'->>'runs')::int           as pitching_runs_allowed,
        (away_team_data->'teamStats'->'pitching'->>'earnedRuns')::int     as pitching_earned_runs,
        (away_team_data->'teamStats'->'pitching'->>'homeRuns')::int       as pitching_home_runs_allowed,
        (away_team_data->'teamStats'->'pitching'->>'strikeOuts')::int     as pitching_strikeouts,
        (away_team_data->'teamStats'->'pitching'->>'baseOnBalls')::int    as pitching_walks,
        (away_team_data->'teamStats'->'pitching'->>'intentionalWalks')::int as pitching_intentional_walks,
        (away_team_data->'teamStats'->'pitching'->>'hitBatsmen')::int     as pitching_hit_batsmen,
        (away_team_data->'teamStats'->'pitching'->>'wildPitches')::int    as pitching_wild_pitches,
        (away_team_data->'teamStats'->'pitching'->>'balks')::int          as pitching_balks,
        (away_team_data->'teamStats'->'pitching'->>'numberOfPitches')::int as pitching_total_pitches,
        (away_team_data->'teamStats'->'pitching'->>'balls')::int          as pitching_balls,
        (away_team_data->'teamStats'->'pitching'->>'strikes')::int        as pitching_strikes,
        (away_team_data->'teamStats'->'pitching'->>'battersFaced')::int   as pitching_batters_faced,
        (away_team_data->'teamStats'->'pitching'->>'inheritedRunners')::int as pitching_inherited_runners,
        (away_team_data->'teamStats'->'pitching'->>'inheritedRunnersScored')::int as pitching_inherited_runners_scored,

        -- team fielding stats
        (away_team_data->'teamStats'->'fielding'->>'errors')::int         as fielding_errors,
        (away_team_data->'teamStats'->'fielding'->>'assists')::int        as fielding_assists,
        (away_team_data->'teamStats'->'fielding'->>'putOuts')::int        as fielding_put_outs,
        (away_team_data->'teamStats'->'fielding'->>'chances')::int        as fielding_chances,
        (away_team_data->'teamStats'->'fielding'->>'passedBall')::int     as fielding_passed_balls,
        (away_team_data->'teamStats'->'fielding'->>'pickoffs')::int       as fielding_pickoffs

    from boxscore

),

boxscore_home as (

    select
        game_pk,
        home_team_id                                               as team_id,

        -- team identity from boxscore team object
        home_team_data->'team'->>'abbreviation'                    as team_abbreviation,
        home_team_data->'team'->'league'->>'name'                  as league_name,
        (home_team_data->'team'->'division'->>'id')::int           as division_id,
        home_team_data->'team'->'division'->>'name'                as division_name,

        -- team batting stats
        (home_team_data->'teamStats'->'batting'->>'atBats')::int          as batting_at_bats,
        (home_team_data->'teamStats'->'batting'->>'runs')::int            as batting_runs,
        (home_team_data->'teamStats'->'batting'->>'hits')::int            as batting_hits,
        (home_team_data->'teamStats'->'batting'->>'doubles')::int         as batting_doubles,
        (home_team_data->'teamStats'->'batting'->>'triples')::int         as batting_triples,
        (home_team_data->'teamStats'->'batting'->>'homeRuns')::int        as batting_home_runs,
        (home_team_data->'teamStats'->'batting'->>'rbi')::int             as batting_rbi,
        (home_team_data->'teamStats'->'batting'->>'baseOnBalls')::int     as batting_walks,
        (home_team_data->'teamStats'->'batting'->>'intentionalWalks')::int as batting_intentional_walks,
        (home_team_data->'teamStats'->'batting'->>'strikeOuts')::int      as batting_strikeouts,
        (home_team_data->'teamStats'->'batting'->>'hitByPitch')::int      as batting_hit_by_pitch,
        (home_team_data->'teamStats'->'batting'->>'sacBunts')::int        as batting_sac_bunts,
        (home_team_data->'teamStats'->'batting'->>'sacFlies')::int        as batting_sac_flies,
        (home_team_data->'teamStats'->'batting'->>'stolenBases')::int     as batting_stolen_bases,
        (home_team_data->'teamStats'->'batting'->>'caughtStealing')::int  as batting_caught_stealing,
        (home_team_data->'teamStats'->'batting'->>'leftOnBase')::int      as batting_left_on_base,
        (home_team_data->'teamStats'->'batting'->>'totalBases')::int      as batting_total_bases,
        (home_team_data->'teamStats'->'batting'->>'groundIntoDoublePlay')::int as batting_gidp,
        (home_team_data->'teamStats'->'batting'->>'plateAppearances')::int as batting_plate_appearances,

        -- team pitching stats
        (home_team_data->'teamStats'->'pitching'->>'outs')::int           as pitching_outs,
        (home_team_data->'teamStats'->'pitching'->>'hits')::int           as pitching_hits_allowed,
        (home_team_data->'teamStats'->'pitching'->>'runs')::int           as pitching_runs_allowed,
        (home_team_data->'teamStats'->'pitching'->>'earnedRuns')::int     as pitching_earned_runs,
        (home_team_data->'teamStats'->'pitching'->>'homeRuns')::int       as pitching_home_runs_allowed,
        (home_team_data->'teamStats'->'pitching'->>'strikeOuts')::int     as pitching_strikeouts,
        (home_team_data->'teamStats'->'pitching'->>'baseOnBalls')::int    as pitching_walks,
        (home_team_data->'teamStats'->'pitching'->>'intentionalWalks')::int as pitching_intentional_walks,
        (home_team_data->'teamStats'->'pitching'->>'hitBatsmen')::int     as pitching_hit_batsmen,
        (home_team_data->'teamStats'->'pitching'->>'wildPitches')::int    as pitching_wild_pitches,
        (home_team_data->'teamStats'->'pitching'->>'balks')::int          as pitching_balks,
        (home_team_data->'teamStats'->'pitching'->>'numberOfPitches')::int as pitching_total_pitches,
        (home_team_data->'teamStats'->'pitching'->>'balls')::int          as pitching_balls,
        (home_team_data->'teamStats'->'pitching'->>'strikes')::int        as pitching_strikes,
        (home_team_data->'teamStats'->'pitching'->>'battersFaced')::int   as pitching_batters_faced,
        (home_team_data->'teamStats'->'pitching'->>'inheritedRunners')::int as pitching_inherited_runners,
        (home_team_data->'teamStats'->'pitching'->>'inheritedRunnersScored')::int as pitching_inherited_runners_scored,

        -- team fielding stats
        (home_team_data->'teamStats'->'fielding'->>'errors')::int         as fielding_errors,
        (home_team_data->'teamStats'->'fielding'->>'assists')::int        as fielding_assists,
        (home_team_data->'teamStats'->'fielding'->>'putOuts')::int        as fielding_put_outs,
        (home_team_data->'teamStats'->'fielding'->>'chances')::int        as fielding_chances,
        (home_team_data->'teamStats'->'fielding'->>'passedBall')::int     as fielding_passed_balls,
        (home_team_data->'teamStats'->'fielding'->>'pickoffs')::int       as fielding_pickoffs

    from boxscore

),

boxscore_combined as (
    select * from boxscore_away
    union all
    select * from boxscore_home
),

final as (

    select
        -- surrogate key
        {{ dbt_utils.generate_surrogate_key(['s.game_pk', 's.team_id']) }}
                                                                    as game_team_id,

        -- grain
        s.game_pk,
        s.team_id,
        s.team_name,
        b.team_abbreviation,
        s.side,

        -- pool / division context
        b.division_id,
        b.division_name,
        b.league_name,

        -- game result
        s.is_winner,
        s.score,
        s.wins,
        s.losses,
        s.win_pct,

        -- box score line
        s.hits,
        s.runs,
        s.errors,
        s.left_on_base,

        -- team batting stats
        b.batting_plate_appearances,
        b.batting_at_bats,
        b.batting_runs,
        b.batting_hits,
        b.batting_doubles,
        b.batting_triples,
        b.batting_home_runs,
        b.batting_rbi,
        b.batting_walks,
        b.batting_intentional_walks,
        b.batting_strikeouts,
        b.batting_hit_by_pitch,
        b.batting_sac_bunts,
        b.batting_sac_flies,
        b.batting_stolen_bases,
        b.batting_caught_stealing,
        b.batting_left_on_base,
        b.batting_total_bases,
        b.batting_gidp,

        -- team pitching stats
        b.pitching_outs,
        b.pitching_hits_allowed,
        b.pitching_runs_allowed,
        b.pitching_earned_runs,
        b.pitching_home_runs_allowed,
        b.pitching_strikeouts,
        b.pitching_walks,
        b.pitching_intentional_walks,
        b.pitching_hit_batsmen,
        b.pitching_wild_pitches,
        b.pitching_balks,
        b.pitching_total_pitches,
        b.pitching_balls,
        b.pitching_strikes,
        b.pitching_batters_faced,
        b.pitching_inherited_runners,
        b.pitching_inherited_runners_scored,

        -- team fielding stats
        b.fielding_errors,
        b.fielding_assists,
        b.fielding_put_outs,
        b.fielding_chances,
        b.fielding_passed_balls,
        b.fielding_pickoffs,

        -- metadata
        s.ingested_at

    from schedule_unpivoted s
    left join boxscore_combined b
        on s.game_pk = b.game_pk
        and s.team_id = b.team_id

)

select * from final
