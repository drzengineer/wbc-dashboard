import sys
from pathlib import Path
from dagster import get_dagster_logger, AssetKey, AssetOut, Output, multi_asset

# parents[0] = assets/
# parents[1] = wbc_dagster/
# parents[2] = dagster/
# parents[3] = pipeline/
INGESTION_DIR = Path(__file__).resolve().parents[3] / "ingestion"
sys.path.insert(0, str(INGESTION_DIR))

import ingest  # type: ignore  # noqa: E402

@multi_asset(
    name="fetch_mlb_data",
    outs={
        "games":    AssetOut(key=AssetKey(["raw", "games"])),
        "players":  AssetOut(key=AssetKey(["raw", "players"])),
        "schedule": AssetOut(key=AssetKey(["raw", "schedule"])),
    },
    description=(
        "Runs the MLB Stats API ingestion pipeline. "
        "Scheduled every 5 days to keep the Supabase free tier active."
    )
)
def fetch_mlb_data():
    log = get_dagster_logger()
    log.info("Starting MLB data ingestion...")
    ingest.run()
    log.info("Ingestion complete.")
    yield Output(value=None, output_name="games")
    yield Output(value=None, output_name="players")
    yield Output(value=None, output_name="schedule")