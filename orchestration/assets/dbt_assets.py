"""dbt transformation assets orchestrated by Dagster."""
import subprocess
from pathlib import Path

from dagster import AssetExecutionContext, asset

DBT_PROJECT_DIR = Path(__file__).parents[2] / "dbt_project"


@asset(
    deps=["raw_matches_bronze"],
    compute_kind="dbt",
    group_name="transformations",
)
def dbt_silver_models(context: AssetExecutionContext) -> None:
    """Run dbt Silver layer transformations (silver_events, silver_team_metrics)."""
    result = subprocess.run(
        ["uv", "run", "dbt", "run", "--select", "silver.*"],
        cwd=DBT_PROJECT_DIR,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        context.log.error(f"dbt Silver failed:\n{result.stderr}")
        raise RuntimeError(f"dbt Silver models failed: {result.stderr}")

    context.log.info(f"dbt Silver output:\n{result.stdout}")


@asset(
    deps=["dbt_silver_models"],
    compute_kind="dbt",
    group_name="transformations",
)
def dbt_gold_models(context: AssetExecutionContext) -> None:
    """Run dbt Gold layer transformations (gold_match_summaries)."""
    result = subprocess.run(
        ["uv", "run", "dbt", "run", "--select", "gold.*"],
        cwd=DBT_PROJECT_DIR,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        context.log.error(f"dbt Gold failed:\n{result.stderr}")
        raise RuntimeError(f"dbt Gold models failed: {result.stderr}")

    context.log.info(f"dbt Gold output:\n{result.stdout}")


@asset(
    deps=["dbt_silver_models"],
    compute_kind="dbt",
    group_name="quality",
)
def dbt_tests(context: AssetExecutionContext) -> None:
    """Run dbt data quality tests."""
    result = subprocess.run(
        ["uv", "run", "dbt", "test"],
        cwd=DBT_PROJECT_DIR,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        context.log.error(f"dbt tests failed:\n{result.stderr}")
        raise RuntimeError(f"dbt tests failed: {result.stderr}")

    context.log.info(f"dbt test output:\n{result.stdout}")
