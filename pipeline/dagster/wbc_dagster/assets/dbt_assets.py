from dagster import AssetExecutionContext
from dagster_dbt import DbtCliResource, dbt_assets
from wbc_dagster.resources import DBT_PROJECT_DIR

DBT_MANIFEST_PATH = DBT_PROJECT_DIR / "target" / "manifest.json"

@dbt_assets(
    manifest=DBT_MANIFEST_PATH,
)
def run_dbt_transforms(context: AssetExecutionContext, dbt: DbtCliResource):
    """
    Runs all dbt models and tests against the Supabase analytics schema.
    Each dbt model surfaces as an individual asset in the Dagster UI,
    giving model-level lineage rather than a single opaque 'dbt run' step.
    On any dbt test failure, the asset materializes as failed — no silent passes.
    """
    yield from dbt.cli(["run"], context=context).stream()
    yield from dbt.cli(["test"], context=context).stream()