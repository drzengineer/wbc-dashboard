from dagster import asset, get_dagster_logger, AssetKey

@asset(
    deps=[
        AssetKey(["analytics", "game_results"]),
        AssetKey(["analytics", "standings"]),
        AssetKey(["analytics", "player_game_stats"]),
        AssetKey(["analytics", "player_tournament_stats"]),
    ],
    description=(
        "Refreshes pgvector embeddings in the vectors schema from analytics tables. "
        "Stub — full implementation in Day 8 when LangChain + pgvector is wired up."
    )
)
def refresh_embeddings() -> None:
    log = get_dagster_logger()
    log.info("Embeddings refresh not yet implemented — stub succeeded.")