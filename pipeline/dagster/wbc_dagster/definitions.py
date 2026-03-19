from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parents[3] / ".env.local"
load_dotenv(env_path)

from dagster import Definitions, load_assets_from_modules
from wbc_dagster.assets import ingestion, dbt_assets, embeddings
from wbc_dagster.resources import dbt_resource
from wbc_dagster.schedules import pipeline_schedule

all_assets = load_assets_from_modules([ingestion, dbt_assets, embeddings])

defs = Definitions(
    assets=all_assets,
    resources={
        "dbt": dbt_resource,
    },
    schedules=[pipeline_schedule],
)