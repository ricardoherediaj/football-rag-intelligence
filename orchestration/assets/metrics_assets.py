"""Silver team metrics: Python Dagster asset (single source of truth).

Replaces the former dbt silver_team_metrics.sql model. All metric calculations
live in football_rag.analytics.metrics.calculate_all_metrics() — this asset
calls that function for every match and writes the result to DuckDB.

Output: one row per (match_id, team_id) with unprefixed column names matching
the schema that gold_match_summaries.sql expects.

Daemon-compatible: uses Config class, env vars for MotherDuck, no interactive I/O.
"""

import logging
import os

import duckdb
import pandas as pd
from dagster import (
    AssetExecutionContext,
    Config,
    MaterializeResult,
    MetadataValue,
    asset,
)

from football_rag.analytics.metrics import calculate_all_metrics

logger = logging.getLogger(__name__)


class MetricsConfig(Config):
    database_path: str = "data/lakehouse.duckdb"


# Maps calculate_all_metrics() prefixed keys → dbt column names (unprefixed)
_COL_MAP = {
    "home_progressive_passes": "progressive_passes",
    "home_total_passes": "total_passes",
    "home_pass_accuracy": "pass_accuracy",
    "home_verticality": "verticality",
    "home_ppda": "ppda",
    "home_high_press": "high_press",
    "home_defensive_actions": "defensive_actions",
    "home_tackles": "successful_tackles",
    "home_interceptions": "interceptions",
    "home_shots": "shots",
    "home_shots_on_target": "shots_on_target",
    "home_goals": "goals",
    "home_xg": "total_xg",
    "home_position": "median_position",
    "home_defense_line": "defense_line",
    "home_forward_line": "forward_line",
    "home_compactness": "compactness",
    "home_possession": "possession",
    "home_field_tilt": "field_tilt",
    "home_clearances": "clearances",
    "home_aerials_won": "aerials_won",
    "home_fouls": "fouls",
}
_AWAY_COL_MAP = {k.replace("home_", "away_"): v for k, v in _COL_MAP.items()}


def _write_metrics(con: duckdb.DuckDBPyConnection, df: pd.DataFrame) -> None:
    """Write metrics DataFrame to silver_team_metrics table (idempotent).

    Writes to 'main' schema (same as match_mapping, silver_fotmob_shots, etc.)
    so that dbt source('football_rag', 'silver_team_metrics') resolves correctly
    (sources.yml: database=lakehouse, schema=main).
    """
    con.execute("CREATE OR REPLACE TABLE main.silver_team_metrics AS SELECT * FROM df")


@asset(
    deps=["dbt_silver_models"],
    group_name="silver",
    compute_kind="python",
)
def silver_team_metrics(
    context: AssetExecutionContext,
    config: MetricsConfig,
) -> MaterializeResult:
    """Compute tactical metrics per team per match.

    Reads silver_events + silver_fotmob_shots + match_mapping from local DuckDB,
    runs calculate_all_metrics() per match, outputs one row per (match_id, team_id).
    Syncs to MotherDuck if MOTHERDUCK_TOKEN is set (required for daemon pipeline).
    """
    con = duckdb.connect(config.database_path)

    # silver_events is in main_main (dbt schema), others in main (Dagster schema)
    events_df = con.execute("SELECT * FROM main_main.silver_events").df()
    fotmob_df = con.execute("SELECT * FROM main.silver_fotmob_shots").df()
    mapping_df = con.execute("SELECT * FROM main.match_mapping").df()

    context.log.info(
        f"Input: {len(events_df)} events, {len(fotmob_df)} shots, "
        f"{len(mapping_df)} mapped matches"
    )

    rows: list[dict] = []
    skipped = 0

    for _, match in mapping_df.iterrows():
        match_id = match["whoscored_match_id"]
        home_id = int(match["whoscored_team_id_1"])
        away_id = int(match["whoscored_team_id_2"])
        fotmob_mid = match["fotmob_match_id"]

        match_events = events_df[events_df["match_id"] == match_id]
        match_fotmob = fotmob_df[fotmob_df["match_id"] == fotmob_mid].to_dict("records")

        if match_events.empty:
            skipped += 1
            continue

        m = calculate_all_metrics(match_events, match_fotmob, home_id, away_id)

        # Home row
        home_row: dict = {"match_id": match_id, "team_id": home_id}
        for src, col in _COL_MAP.items():
            home_row[col] = m.get(src)
        rows.append(home_row)

        # Away row
        away_row: dict = {"match_id": match_id, "team_id": away_id}
        for src, col in _AWAY_COL_MAP.items():
            away_row[col] = m.get(src)
        rows.append(away_row)

    result_df = pd.DataFrame(rows)

    # Write to local DuckDB
    _write_metrics(con, result_df)
    con.close()
    context.log.info(
        f"silver_team_metrics: {len(result_df)} rows → local DuckDB "
        f"({skipped} matches skipped — no events)"
    )

    # Sync to MotherDuck (daemon pipeline needs this for dbt gold)
    md_token = os.getenv("MOTHERDUCK_TOKEN")
    if md_token:
        md_con = duckdb.connect(f"md:football_rag?motherduck_token={md_token}")
        _write_metrics(md_con, result_df)
        md_con.close()
        context.log.info("silver_team_metrics: synced to MotherDuck")
    else:
        context.log.warning("MOTHERDUCK_TOKEN not set — skipping MotherDuck sync")

    p50_pp = float(result_df["progressive_passes"].median()) if len(result_df) else 0
    p50_ppda = float(result_df["ppda"].median()) if len(result_df) else 0

    return MaterializeResult(
        metadata={
            "row_count": MetadataValue.int(len(result_df)),
            "skipped_matches": MetadataValue.int(skipped),
            "p50_progressive_passes": MetadataValue.float(p50_pp),
            "p50_ppda": MetadataValue.float(p50_ppda),
        }
    )
