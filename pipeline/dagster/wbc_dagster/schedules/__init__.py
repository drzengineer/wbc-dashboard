from dagster import ScheduleDefinition, define_asset_job

pipeline_job = define_asset_job(
    name="wbc_pipeline_job",
    selection="*",
)

pipeline_schedule = ScheduleDefinition(
    job=pipeline_job,
    cron_schedule=["17 3 */5 1,2,4,5,6,7,8,9,10,11,12 *", "17 3 * 3 *"],
    name="wbc_pipeline_schedule",
)