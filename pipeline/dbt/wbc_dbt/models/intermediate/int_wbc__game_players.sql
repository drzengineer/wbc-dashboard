with boxscore as (

    select * from {{ ref('stg_wbc__boxscores') }}

),

-- unnest the players jsonb map for the away team.
-- the players object is keyed as "ID{player_id}", so we strip the prefix to recover player_id.
away_players as (

    select
        b.game_pk,
        b.ingested_at,
        b.away_team_id                                                          as team_id,
        'away'                                                                  as side,
        replace(kv.key, 'ID', '')::int                                          as player_id,
        kv.value                                                                as player

    from boxscore b,
    jsonb_each(b.away_team_data->'players') as kv

),

home_players as (

    select
        b.game_pk,
        b.ingested_at,
        b.home_team_id                                                          as team_id,
        'home'                                                                  as side,
        replace(kv.key, 'ID', '')::int                                          as player_id,
        kv.value                                                                as player

    from boxscore b,
    jsonb_each(b.home_team_data->'players') as kv

),

all_players as (
    select * from away_players
    union all
    select * from home_players
),

-- derive batting order position by joining back to the battingOrder array.
-- battingOrder is an ordered array of player_ids; array index + 1 = lineup position.
away_batting_order as (

    select
        game_pk,
        away_team_id                                                            as team_id,
        (elem.value)::int                                                       as player_id,
        elem.ordinality                                                         as batting_order
    from boxscore,
    jsonb_array_elements(away_team_data->'battingOrder') with ordinality as elem(value, ordinality)

),

home_batting_order as (

    select
        game_pk,
        home_team_id                                                            as team_id,
        (elem.value)::int                                                       as player_id,
        elem.ordinality                                                         as batting_order
    from boxscore,
    jsonb_array_elements(home_team_data->'battingOrder') with ordinality as elem(value, ordinality)

),

batting_order as (
    select * from away_batting_order
    union all
    select * from home_batting_order
),

final as (

    select
        -- surrogate key
        {{ dbt_utils.generate_surrogate_key(['p.game_pk', 'p.player_id']) }}
                                                                                as game_player_id,

        -- grain
        p.game_pk,
        p.player_id,
        p.team_id,
        p.side,

        -- player identity
        p.player->'person'->>'fullName'                                         as full_name,
        p.player->'person'->>'boxscoreName'                                     as boxscore_name,
        p.player->>'jerseyNumber'                                               as jersey_number,

        -- position (first element of allPositions covers multi-position games)
        p.player->'allPositions'->0->>'code'                                    as position_code,
        p.player->'allPositions'->0->>'name'                                    as position_name,
        p.player->'allPositions'->0->>'type'                                    as position_type,
        p.player->'allPositions'->0->>'abbreviation'                            as position_abbreviation,

        -- game status
        (p.player->'gameStatus'->>'isOnBench')::boolean                         as is_on_bench,
        (p.player->'gameStatus'->>'isSubstitute')::boolean                      as is_substitute,
        (p.player->'gameStatus'->>'isCurrentBatter')::boolean                   as is_current_batter,
        (p.player->'gameStatus'->>'isCurrentPitcher')::boolean                  as is_current_pitcher,

        -- batting order (null for pitchers/bench)
        bo.batting_order,

        -- game batting stats
        (p.player->'stats'->'batting'->>'plateAppearances')::int                as batting_plate_appearances,
        (p.player->'stats'->'batting'->>'atBats')::int                          as batting_at_bats,
        (p.player->'stats'->'batting'->>'runs')::int                            as batting_runs,
        (p.player->'stats'->'batting'->>'hits')::int                            as batting_hits,
        (p.player->'stats'->'batting'->>'doubles')::int                         as batting_doubles,
        (p.player->'stats'->'batting'->>'triples')::int                         as batting_triples,
        (p.player->'stats'->'batting'->>'homeRuns')::int                        as batting_home_runs,
        (p.player->'stats'->'batting'->>'rbi')::int                             as batting_rbi,
        (p.player->'stats'->'batting'->>'baseOnBalls')::int                     as batting_walks,
        (p.player->'stats'->'batting'->>'intentionalWalks')::int                as batting_intentional_walks,
        (p.player->'stats'->'batting'->>'strikeOuts')::int                      as batting_strikeouts,
        (p.player->'stats'->'batting'->>'hitByPitch')::int                      as batting_hit_by_pitch,
        (p.player->'stats'->'batting'->>'sacBunts')::int                        as batting_sac_bunts,
        (p.player->'stats'->'batting'->>'sacFlies')::int                        as batting_sac_flies,
        (p.player->'stats'->'batting'->>'stolenBases')::int                     as batting_stolen_bases,
        (p.player->'stats'->'batting'->>'caughtStealing')::int                  as batting_caught_stealing,
        (p.player->'stats'->'batting'->>'leftOnBase')::int                      as batting_left_on_base,
        (p.player->'stats'->'batting'->>'totalBases')::int                      as batting_total_bases,
        (p.player->'stats'->'batting'->>'groundIntoDoublePlay')::int            as batting_gidp,
        (p.player->'stats'->'batting'->>'groundOuts')::int                      as batting_ground_outs,
        (p.player->'stats'->'batting'->>'airOuts')::int                         as batting_air_outs,
        (p.player->'stats'->'batting'->>'pickoffs')::int                        as batting_pickoffs,

        -- game pitching stats (null for non-pitchers)
        (p.player->'stats'->'pitching'->>'outs')::int                           as pitching_outs,
        (p.player->'stats'->'pitching'->>'numberOfPitches')::int                as pitching_total_pitches,
        (p.player->'stats'->'pitching'->>'strikes')::int                        as pitching_strikes,
        (p.player->'stats'->'pitching'->>'balls')::int                          as pitching_balls,
        (p.player->'stats'->'pitching'->>'hits')::int                           as pitching_hits_allowed,
        (p.player->'stats'->'pitching'->>'runs')::int                           as pitching_runs_allowed,
        (p.player->'stats'->'pitching'->>'earnedRuns')::int                     as pitching_earned_runs,
        (p.player->'stats'->'pitching'->>'homeRuns')::int                       as pitching_home_runs_allowed,
        (p.player->'stats'->'pitching'->>'strikeOuts')::int                     as pitching_strikeouts,
        (p.player->'stats'->'pitching'->>'baseOnBalls')::int                    as pitching_walks,
        (p.player->'stats'->'pitching'->>'intentionalWalks')::int               as pitching_intentional_walks,
        (p.player->'stats'->'pitching'->>'hitBatsmen')::int                     as pitching_hit_batsmen,
        (p.player->'stats'->'pitching'->>'wildPitches')::int                    as pitching_wild_pitches,
        (p.player->'stats'->'pitching'->>'balks')::int                          as pitching_balks,
        (p.player->'stats'->'pitching'->>'battersFaced')::int                   as pitching_batters_faced,
        (p.player->'stats'->'pitching'->>'inheritedRunners')::int               as pitching_inherited_runners,
        (p.player->'stats'->'pitching'->>'inheritedRunnersScored')::int         as pitching_inherited_runners_scored,
        (p.player->'stats'->'pitching'->>'wins')::int                           as pitching_wins,
        (p.player->'stats'->'pitching'->>'losses')::int                         as pitching_losses,
        (p.player->'stats'->'pitching'->>'saves')::int                          as pitching_saves,
        (p.player->'stats'->'pitching'->>'holds')::int                          as pitching_holds,
        (p.player->'stats'->'pitching'->>'blownSaves')::int                     as pitching_blown_saves,
        (p.player->'stats'->'pitching'->>'gamesStarted')::int                   as pitching_games_started,

        -- game fielding stats
        (p.player->'stats'->'fielding'->>'errors')::int                         as fielding_errors,
        (p.player->'stats'->'fielding'->>'assists')::int                        as fielding_assists,
        (p.player->'stats'->'fielding'->>'putOuts')::int                        as fielding_put_outs,
        (p.player->'stats'->'fielding'->>'chances')::int                        as fielding_chances,
        (p.player->'stats'->'fielding'->>'passedBall')::int                     as fielding_passed_balls,
        (p.player->'stats'->'fielding'->>'pickoffs')::int                       as fielding_pickoffs,

        -- metadata
        p.ingested_at

    from all_players p
    left join batting_order bo
        on p.game_pk = bo.game_pk
        and p.team_id = bo.team_id
        and p.player_id = bo.player_id

)

select * from final
