with source as (
    select game_pk, data, ingested_at
    from raw.schedule
),

-- raw.schedule team objects only contain id/link/name — no abbreviation field
-- abbreviation is only available in raw.games boxscore team objects, so we join to get it
-- left join ensures scheduled future games with no boxscore yet still appear (with null abbrev)
game_abbrevs as (
    select
        game_pk,
        data->'teams'->'away'->'team'->>'abbreviation'  as away_team_abbreviation,
        data->'teams'->'home'->'team'->>'abbreviation'  as home_team_abbreviation
    from raw.games
),

flattened as (
    select
        s.game_pk,
        (s.data->>'season')::int                                        as season,
        s.data->>'gameType'                                             as game_type,
        (s.data->>'officialDate')::date                                 as official_date,
        s.data->>'dayNight'                                             as day_night,
        s.data->'status'->>'abstractGameState'                          as abstract_game_state,
        s.data->'status'->>'detailedState'                              as detailed_state,
        case
            when s.data->'status'->>'detailedState' = 'Completed Early' then true
            when s.data->'status'->>'detailedState' = 'Final'           then false
            -- null for Live or Preview — game has not concluded, mercy rule unknown
            else null
        end                                                             as is_mercy_rule,
        s.data->'teams'->'away'->'team'->>'name'                        as away_team_name,
        -- abbreviation sourced from raw.games, not raw.schedule (schedule blob lacks this field)
        g.away_team_abbreviation,
        nullif(s.data->'teams'->'away'->'team'->>'id', '')::int          as away_team_id,
        s.data->'teams'->'home'->'team'->>'name'                        as home_team_name,
        g.home_team_abbreviation,
        nullif(s.data->'teams'->'home'->'team'->>'id', '')::int          as home_team_id,
        nullif(s.data->'teams'->'away'->>'score', '')::int              as away_score,
        nullif(s.data->'teams'->'home'->>'score', '')::int              as home_score,
        case
            when s.data->'teams'->'away'->>'isWinner' = 'true'  then true
            when s.data->'teams'->'away'->>'isWinner' = 'false' then false
            else null
        end                                                             as away_is_winner,
        case
            when s.data->'teams'->'home'->>'isWinner' = 'true'  then true
            when s.data->'teams'->'home'->>'isWinner' = 'false' then false
            else null
        end                                                             as home_is_winner,
        s.data->'venue'->>'name'                                        as venue_name,
        s.data->>'description'                                          as description,
        s.data->>'seriesDescription'                                    as series_description,
        s.data->>'ifNecessary'                                          as if_necessary,
        case
            when s.data->'teams'->'away'->'team'->>'placeholder' = 'true'  then true
            when s.data->'teams'->'away'->'team'->>'placeholder' = 'false' then false
            -- null when placeholder key absent (normal completed games)
            else null
        end                                                             as away_team_is_placeholder,
        case
            when s.data->'teams'->'home'->'team'->>'placeholder' = 'true'  then true
            when s.data->'teams'->'home'->'team'->>'placeholder' = 'false' then false
            -- null when placeholder key absent (normal completed games)
            else null
        end                                                             as home_team_is_placeholder,
        s.ingested_at
    from source s
    left join game_abbrevs g on s.game_pk = g.game_pk
)

select * from flattened