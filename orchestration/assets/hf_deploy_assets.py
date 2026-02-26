"""
Hugging Face deploy assets: upload lakehouse.duckdb and restart Space.

Runs after gold_match_embeddings to push fresh data to the public app.
Requires HF_TOKEN env var with write access to rheredia8/football-rag-data
and rheredia8/football-rag-intelligence.
"""

import os
from pathlib import Path

from dagster import AssetExecutionContext, asset
from huggingface_hub import HfApi

DUCKDB_PATH = Path(__file__).parents[2] / "data" / "lakehouse.duckdb"
HF_DATASET_REPO = "rheredia8/football-rag-data"
HF_SPACE_REPO = "rheredia8/football-rag-intelligence"


@asset(
    deps=["gold_match_embeddings"],
    compute_kind="huggingface",
    group_name="deploy",
)
def hf_lakehouse_upload(context: AssetExecutionContext) -> None:
    """Upload lakehouse.duckdb to the private HF Dataset repo.

    The HF Space downloads this file at cold start, so uploading it
    here ensures the app serves fresh embeddings after every pipeline run.
    """
    token = os.environ.get("HF_TOKEN")
    if not token:
        raise EnvironmentError("HF_TOKEN env var not set — cannot upload to HF Dataset")

    size_mb = DUCKDB_PATH.stat().st_size / (1024 * 1024)
    context.log.info(f"Uploading {DUCKDB_PATH.name} ({size_mb:.1f} MB) → {HF_DATASET_REPO}")

    api = HfApi(token=token)
    api.upload_file(
        path_or_fileobj=str(DUCKDB_PATH),
        path_in_repo="lakehouse.duckdb",
        repo_id=HF_DATASET_REPO,
        repo_type="dataset",
        commit_message="chore: pipeline refresh — updated embeddings",
    )
    context.log.info(f"✅ Uploaded lakehouse.duckdb to {HF_DATASET_REPO}")


@asset(
    deps=["hf_lakehouse_upload"],
    compute_kind="huggingface",
    group_name="deploy",
)
def hf_space_restart(context: AssetExecutionContext) -> None:
    """Restart the HF Space so it re-downloads the fresh lakehouse.duckdb.

    Without a restart the Space serves the cached (stale) DuckDB file
    from its previous cold start.
    """
    token = os.environ.get("HF_TOKEN")
    if not token:
        raise EnvironmentError("HF_TOKEN env var not set — cannot restart HF Space")

    context.log.info(f"Restarting HF Space: {HF_SPACE_REPO}")
    api = HfApi(token=token)
    api.restart_space(repo_id=HF_SPACE_REPO, token=token)
    context.log.info(f"✅ Space restart triggered — {HF_SPACE_REPO} will reload fresh data")
