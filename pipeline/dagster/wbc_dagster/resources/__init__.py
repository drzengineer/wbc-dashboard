import os
from pathlib import Path
from dagster_dbt import DbtCliResource

DBT_PROJECT_DIR = Path(
    os.environ.get(
        "DBT_PROJECT_DIR",
        Path(__file__).resolve().parents[3] / "dbt" / "wbc_dbt"
    )
).resolve()

dbt_resource = DbtCliResource(
    project_dir=str(DBT_PROJECT_DIR),
)