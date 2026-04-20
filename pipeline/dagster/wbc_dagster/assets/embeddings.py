"""
pipeline/dagster/wbc_dagster/assets/embeddings.py

Day 8: Real implementation — calls embed.py via subprocess.
Replaces the Day 5 stub.
"""

import subprocess
import sys
from pathlib import Path

from dagster import AssetKey, asset, get_dagster_logger

# embed.py lives at pipeline/ingestion/embed.py
# This file lives at pipeline/dagster/wbc_dagster/assets/embeddings.py
# parents[3] = pipeline/ locally, /app/ in container
EMBED_SCRIPT = Path(__file__).resolve().parents[3] / "ingestion" / "embed.py"


@asset(
    deps=[
        AssetKey(["wbc_mart", "app_game_results"]),
        AssetKey(["wbc_mart", "app_pool_standings"]),
        AssetKey(["wbc_mart", "app_player_season_stats"]),
        AssetKey(["wbc_mart", "app_game_detail"]),
    ],
    description="Embeds mart app layer data via local all-MiniLM-L6-v2 (SentenceTransformer) and upserts into vectors.embeddings.",
)
def refresh_embeddings() -> None:
    log = get_dagster_logger()
    log.info(f"Starting embedding refresh — script: {EMBED_SCRIPT}")

    if not EMBED_SCRIPT.exists():
        raise FileNotFoundError(f"embed.py not found at {EMBED_SCRIPT}")

    result = subprocess.run(
        [sys.executable, str(EMBED_SCRIPT)],
        capture_output=True,
        text=True,
    )

    # Always surface stdout so progress logs appear in Dagster UI
    if result.stdout:
        log.info(result.stdout)

    if result.returncode != 0:
        log.error(result.stderr)
        raise Exception(f"embed.py failed (exit {result.returncode}):\n{result.stderr}")

    log.info("Embedding refresh complete.")