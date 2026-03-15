-- assert_no_scores_on_unplayed_games.sql
-- Scheduled (Preview) games must have NULL scores — the API omits score fields
-- entirely for games that haven't started, and they should never be coerced to 0.
-- 
-- Live games are explicitly excluded — scores populate mid-game and that is
-- expected behavior. This test only guards against Preview games incorrectly
-- having scores, which would indicate a model or ingestion bug.

select
    game_pk,
    away_score,
    home_score,
    abstract_game_state
from {{ ref('game_results') }}
where abstract_game_state = 'Preview'
  and (away_score is not null or home_score is not null)
