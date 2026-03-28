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
# So we go up 4 levels: assets → wbc_dagster → dagster → pipeline → ingestion
EMBED_SCRIPT = Path(__file__).resolve().parents[4] / "ingestion" / "embed.py"


@asset(
    deps=[
        AssetKey(["analytics", "game_results"]),
        AssetKey(["analytics", "standings"]),
        AssetKey(["analytics", "player_game_stats"]),
        AssetKey(["analytics", "player_tournament_stats"]),
    ],
    description="Embeds analytics data via local all-MiniLM-L6-v2 (SentenceTransformer) and upserts into vectors.embeddings.",
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