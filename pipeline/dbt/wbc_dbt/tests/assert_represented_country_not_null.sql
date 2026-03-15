-- assert_represented_country_not_null.sql
-- Every player in player_tournament_stats must have a represented_country.
-- This is derived from the team they appeared for in boxscores — if it's null,
-- the country derivation logic in the model has a gap.
-- (Note: birth_country nulls are acceptable — this test is specifically for
-- represented_country, which is the WBC team affiliation field.)

select
    person_id,
    season,
    full_name,
    represented_country
from {{ ref('player_tournament_stats') }}
where represented_country is null
