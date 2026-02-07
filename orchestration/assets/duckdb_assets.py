import json
import logging
from pathlib import Path

import duckdb
from dagster import AssetExecutionContext, Config, asset

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
    """Load raw JSON files into DuckDB bronze_matches (idempotent)."""
    db = duckdb.connect(config.database_path)
    db.execute(
        "CREATE OR REPLACE TABLE bronze_matches "
        "(match_id VARCHAR, source VARCHAR, data JSON)"
    )

    raw_dir_ws = Path("data/raw/whoscored_matches")
    raw_dir_fm = Path("data/raw/fotmob_matches")
    count = 0

    for json_file in raw_dir_ws.rglob("*.json"):
        with open(json_file) as f:
            data = json.load(f)
        match_id = str(data.get("match_id", "unknown"))
        db.execute(
            "INSERT INTO bronze_matches VALUES (?, 'whoscored', ?)",
            [match_id, json.dumps(data)],
        )
        count += 1

    for json_file in raw_dir_fm.rglob("*.json"):
        with open(json_file) as f:
            raw = _sanitize_json(f.read())
        data = json.loads(raw)
        # Handle both flat and nested (match_info) formats
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
    context.log.info(f"Bronze: loaded {count} matches")
    context.add_output_metadata({"matches_loaded": count})
    return count


@asset(deps=[raw_matches_bronze], compute_kind="duckdb")
def events_silver(config: DuckDBConfig) -> None:
    """Flatten WhoScored events from Bronze JSON into Silver table."""
    db = duckdb.connect(config.database_path)
    db.execute("""
        CREATE OR REPLACE TABLE silver_events AS
        WITH raw_events AS (
            SELECT
                match_id,
                unnest(
                    from_json(json_extract(data, '$.events'), '["json"]')
                ) AS event
            FROM bronze_matches
            WHERE source = 'whoscored'
        )
        SELECT
            match_id,
            CAST(json_extract_string(event, '$.id') AS BIGINT) AS event_row_id,
            CAST(json_extract_string(event, '$.event_id') AS INTEGER) AS event_id,
            json_extract_string(event, '$.type_display_name') AS event_type,
            json_extract_string(event, '$.outcome_type_display_name') AS outcome,
            json_extract_string(event, '$.period_display_name') AS period,
            CAST(json_extract_string(event, '$.player_id') AS INTEGER) AS player_id,
            CAST(json_extract_string(event, '$.team_id') AS INTEGER) AS team_id,
            CAST(json_extract_string(event, '$.x') AS DOUBLE) AS x,
            CAST(json_extract_string(event, '$.y') AS DOUBLE) AS y,
            CAST(json_extract_string(event, '$.end_x') AS DOUBLE) AS end_x,
            CAST(json_extract_string(event, '$.end_y') AS DOUBLE) AS end_y,
            CAST(json_extract_string(event, '$.minute') AS INTEGER) AS minute,
            CAST(json_extract_string(event, '$.second') AS DOUBLE) AS second,
            json_extract_string(event, '$.is_shot') = 'true' AS is_shot,
            json_extract_string(event, '$.is_goal') = 'true' AS is_goal,
            json_extract_string(event, '$.is_touch') = 'true' AS is_touch
        FROM raw_events
    """)
    db.close()


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


@asset(deps=[events_silver, silver_fotmob], compute_kind="duckdb")
def gold_match_summary(config: DuckDBConfig) -> None:
    """Aggregate match-level stats combining WhoScored events and FotMob xG."""
    db = duckdb.connect(config.database_path)
    db.execute("""
        CREATE OR REPLACE TABLE gold_match_summary AS
        WITH ws_stats AS (
            SELECT
                match_id,
                team_id,
                COUNT(*) AS total_events,
                SUM(CASE WHEN event_type = 'Pass' THEN 1 ELSE 0 END) AS passes,
                SUM(CASE WHEN is_shot THEN 1 ELSE 0 END) AS shots,
                SUM(CASE WHEN is_goal THEN 1 ELSE 0 END) AS goals,
                SUM(CASE WHEN event_type = 'Tackle' THEN 1 ELSE 0 END) AS tackles
            FROM silver_events
            GROUP BY match_id, team_id
        ),
        fm_stats AS (
            SELECT
                match_id,
                team_id,
                home_team,
                away_team,
                match_date,
                COUNT(*) AS fm_shots,
                SUM(CASE WHEN is_goal THEN 1 ELSE 0 END) AS fm_goals,
                ROUND(SUM(xg), 2) AS total_xg,
                SUM(CASE WHEN is_on_target THEN 1 ELSE 0 END) AS shots_on_target
            FROM silver_fotmob_shots
            GROUP BY match_id, team_id, home_team, away_team, match_date
        )
        SELECT
            ws.match_id,
            ws.team_id,
            fm.home_team,
            fm.away_team,
            fm.match_date,
            ws.total_events,
            ws.passes,
            ws.shots,
            ws.goals,
            ws.tackles,
            fm.total_xg,
            fm.shots_on_target
        FROM ws_stats ws
        LEFT JOIN fm_stats fm
            ON ws.match_id = fm.match_id AND ws.team_id = fm.team_id
    """)
    db.close()


@asset(deps=[events_silver], compute_kind="duckdb")
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
