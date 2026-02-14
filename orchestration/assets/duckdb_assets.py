import json
import logging

import duckdb
from dagster import AssetExecutionContext, Config, asset

from football_rag.storage.minio_client import MinIOClient, DEFAULT_BUCKET

logger = logging.getLogger(__name__)


class DuckDBConfig(Config):
    database_path: str = "data/lakehouse.duckdb"


def _sanitize_json(raw: str) -> str:
    """Replace NaN with null so DuckDB can parse the JSON."""
    return raw.replace(": NaN", ": null").replace(":NaN", ":null")


@asset(compute_kind="python")
def raw_matches_bronze(
    context: AssetExecutionContext, config: DuckDBConfig
) -> int:
    """Load raw JSON from MinIO into DuckDB bronze_matches (idempotent)."""
    db = duckdb.connect(config.database_path)
    db.execute(
        "CREATE OR REPLACE TABLE bronze_matches "
        "(match_id VARCHAR, source VARCHAR, data JSON)"
    )

    client = MinIOClient()
    count = 0

    # WhoScored matches from MinIO
    for key in client.list_objects(DEFAULT_BUCKET, prefix="whoscored/"):
        if not key.endswith(".json"):
            continue
        raw = client.download_raw(DEFAULT_BUCKET, key)
        data = json.loads(raw)
        match_id = str(data.get("match_id", "unknown"))
        db.execute(
            "INSERT INTO bronze_matches VALUES (?, 'whoscored', ?)",
            [match_id, json.dumps(data)],
        )
        count += 1

    # FotMob matches from MinIO
    for key in client.list_objects(DEFAULT_BUCKET, prefix="fotmob/"):
        if not key.endswith(".json"):
            continue
        raw = _sanitize_json(client.download_raw(DEFAULT_BUCKET, key))
        data = json.loads(raw)
        match_id = str(
            data.get("match_id")
            or data.get("match_info", {}).get("match_id", "unknown")
        )
        db.execute(
            "INSERT INTO bronze_matches VALUES (?, 'fotmob', ?)",
            [match_id, json.dumps(data)],
        )
        count += 1

    db.close()
    context.log.info(f"Bronze: loaded {count} matches from MinIO")
    context.add_output_metadata({"matches_loaded": count})
    return count


@asset(deps=[raw_matches_bronze], compute_kind="duckdb")
def silver_fotmob(config: DuckDBConfig) -> None:
    """Flatten FotMob shot data from Bronze JSON into Silver table."""
    db = duckdb.connect(config.database_path)
    db.execute("""
        CREATE OR REPLACE TABLE silver_fotmob_shots AS
        WITH raw_shots AS (
            SELECT
                match_id,
                COALESCE(
                    json_extract_string(data, '$.home_team'),
                    json_extract_string(data, '$.match_info.home_team')
                ) AS home_team,
                COALESCE(
                    json_extract_string(data, '$.away_team'),
                    json_extract_string(data, '$.match_info.away_team')
                ) AS away_team,
                COALESCE(
                    json_extract_string(data, '$.match_date'),
                    json_extract_string(data, '$.match_info.utc_time')
                ) AS match_date,
                unnest(
                    from_json(json_extract(data, '$.shots'), '["json"]')
                ) AS shot
            FROM bronze_matches
            WHERE source = 'fotmob'
        )
        SELECT
            match_id,
            home_team,
            away_team,
            match_date,
            CAST(json_extract_string(shot, '$.id') AS BIGINT) AS shot_id,
            json_extract_string(shot, '$.eventType') AS event_type,
            json_extract_string(shot, '$.playerName') AS player_name,
            CAST(json_extract_string(shot, '$.playerId') AS INTEGER) AS player_id,
            CAST(json_extract_string(shot, '$.teamId') AS INTEGER) AS team_id,
            CAST(json_extract_string(shot, '$.x') AS DOUBLE) AS x,
            CAST(json_extract_string(shot, '$.y') AS DOUBLE) AS y,
            CAST(json_extract_string(shot, '$.min') AS INTEGER) AS minute,
            CAST(json_extract_string(shot, '$.expectedGoals') AS DOUBLE) AS xg,
            json_extract_string(shot, '$.shotType') AS shot_type,
            json_extract_string(shot, '$.situation') AS situation,
            json_extract_string(shot, '$.isOnTarget') = 'true' AS is_on_target,
            json_extract_string(shot, '$.eventType') = 'Goal' AS is_goal
        FROM raw_shots
    """)
    db.close()


@asset(deps=[raw_matches_bronze], compute_kind="duckdb")
def gold_player_stats(config: DuckDBConfig) -> None:
    """Aggregate player-level shooting and passing stats."""
    db = duckdb.connect(config.database_path)
    db.execute("""
        CREATE OR REPLACE TABLE gold_player_stats AS
        SELECT
            player_id,
            team_id,
            COUNT(DISTINCT match_id) AS matches_played,
            COUNT(*) AS total_events,
            SUM(CASE WHEN event_type = 'Pass' THEN 1 ELSE 0 END) AS passes,
            SUM(CASE WHEN is_shot THEN 1 ELSE 0 END) AS shots,
            SUM(CASE WHEN is_goal THEN 1 ELSE 0 END) AS goals,
            SUM(CASE WHEN event_type = 'Tackle' THEN 1 ELSE 0 END) AS tackles
        FROM silver_events
        GROUP BY player_id, team_id
    """)
    db.close()
