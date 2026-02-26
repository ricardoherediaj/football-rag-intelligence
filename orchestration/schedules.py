from dagster import (
    AssetSelection,
    DefaultScheduleStatus,
    DefaultSensorStatus,
    RunConfig,
    RunRequest,
    ScheduleDefinition,
    SensorEvaluationContext,
    define_asset_job,
    run_status_sensor,
)
from dagster import DagsterRunStatus

from orchestration.assets.scrapers import ScraperConfig

# --- Asset Jobs ---

scrape_and_load_job = define_asset_job(
    name="scrape_and_load_job",
    selection=AssetSelection.assets(
        "whoscored_match_data",
        "fotmob_match_data",
        "raw_matches_bronze",
        "match_mapping",
    ),
)

transform_job = define_asset_job(
    name="transform_job",
    selection=AssetSelection.assets(
        "match_mapping",
        "dbt_silver_models",
        "dbt_gold_models",
        "gold_match_embeddings",
    ),
)

deploy_job = define_asset_job(
    name="deploy_job",
    selection=AssetSelection.assets(
        "hf_lakehouse_upload",
        "hf_space_restart",
    ),
)

# --- League Schedules ---

# --- Sensor: auto-trigger transform after successful scrape ---

@run_status_sensor(
    run_status=DagsterRunStatus.SUCCESS,
    monitored_jobs=[scrape_and_load_job],
    request_job=transform_job,
    default_status=DefaultSensorStatus.RUNNING,
    name="post_scrape_transform_sensor",
)
def post_scrape_transform_sensor(context: SensorEvaluationContext) -> RunRequest:
    """Automatically run transform_job whenever scrape_and_load_job succeeds."""
    return RunRequest(run_key=context.dagster_run.run_id)


@run_status_sensor(
    run_status=DagsterRunStatus.SUCCESS,
    monitored_jobs=[transform_job],
    request_job=deploy_job,
    default_status=DefaultSensorStatus.RUNNING,
    name="post_transform_deploy_sensor",
)
def post_transform_deploy_sensor(context: SensorEvaluationContext) -> RunRequest:
    """Automatically run deploy_job whenever transform_job succeeds.

    Uploads fresh lakehouse.duckdb to HF Dataset and restarts the Space
    so the public app serves up-to-date embeddings.
    """
    return RunRequest(run_key=context.dagster_run.run_id)


# --- League Schedules ---

eredivisie_scrape_schedule = ScheduleDefinition(
    name="eredivisie_post_matchday",
    job=scrape_and_load_job,
    cron_schedule=["0 7 * * 1", "0 7 * * 4"],  # Mon + Thu 7am UTC
    run_config=RunConfig(
        ops={
            "whoscored_match_data": ScraperConfig(mode="incremental"),
            "fotmob_match_data": ScraperConfig(mode="incremental"),
        }
    ),
    default_status=DefaultScheduleStatus.RUNNING,
    description="Scrape new Eredivisie matches after each matchday (Mon/Thu 7am UTC)",
)
