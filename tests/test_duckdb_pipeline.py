"""
Tests for the DuckDB Medallion pipeline (Bronze -> Silver -> Gold).

Uses actual data files on disk to validate the full pipeline end-to-end.
Writes to a temporary DuckDB database so production data is not affected.
"""

import json
from pathlib import Path

import duckdb
import pytest


def _sanitize_json(raw: str) -> str:
    """Replace NaN with null so DuckDB can parse the JSON."""
    return raw.replace(": NaN", ": null").replace(":NaN", ":null")

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

RAW_WS_DIR = Path("data/raw/whoscored_matches")
RAW_FM_DIR = Path("data/raw/fotmob_matches")


def _count_json_files(directory: Path) -> int:
    if not directory.exists():
        return 0
    return len(list(directory.rglob("*.json")))


@pytest.fixture(scope="module")
def db_path(tmp_path_factory) -> Path:
    """Create a temp DuckDB database and load the full pipeline."""
    db_file = tmp_path_factory.mktemp("duckdb") / "test_lakehouse.duckdb"
    db = duckdb.connect(str(db_file))

    # Bronze
    db.execute(
        "CREATE TABLE bronze_matches "
        "(match_id VARCHAR, source VARCHAR, data JSON)"
    )

    for json_file in RAW_WS_DIR.rglob("*.json"):
        with open(json_file) as f:
            data = json.load(f)
        match_id = str(data.get("match_id", "unknown"))
        db.execute(
            "INSERT INTO bronze_matches VALUES (?, 'whoscored', ?)",
            [match_id, json.dumps(data)],
        )

    for json_file in RAW_FM_DIR.rglob("*.json"):
        with open(json_file) as f:
            raw = _sanitize_json(f.read())
        data = json.loads(raw)
        match_id = str(
            data.get("match_id")
            or data.get("match_info", {}).get("match_id", "unknown")
        )
        db.execute(
            "INSERT INTO bronze_matches VALUES (?, 'fotmob', ?)",
            [match_id, json.dumps(data)],
        )

    # Silver: WhoScored events
    db.execute("""
        CREATE TABLE silver_events AS
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

    # Silver: FotMob shots
    db.execute("""
        CREATE TABLE silver_fotmob_shots AS
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
            match_id, home_team, away_team, match_date,
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

    # Gold: Match summary
    db.execute("""
        CREATE TABLE gold_match_summary AS
        WITH ws_stats AS (
            SELECT match_id, team_id,
                COUNT(*) AS total_events,
                SUM(CASE WHEN event_type = 'Pass' THEN 1 ELSE 0 END) AS passes,
                SUM(CASE WHEN is_shot THEN 1 ELSE 0 END) AS shots,
                SUM(CASE WHEN is_goal THEN 1 ELSE 0 END) AS goals,
                SUM(CASE WHEN event_type = 'Tackle' THEN 1 ELSE 0 END) AS tackles
            FROM silver_events GROUP BY match_id, team_id
        ),
        fm_stats AS (
            SELECT match_id, team_id, home_team, away_team, match_date,
                COUNT(*) AS fm_shots,
                SUM(CASE WHEN is_goal THEN 1 ELSE 0 END) AS fm_goals,
                ROUND(SUM(xg), 2) AS total_xg,
                SUM(CASE WHEN is_on_target THEN 1 ELSE 0 END) AS shots_on_target
            FROM silver_fotmob_shots
            GROUP BY match_id, team_id, home_team, away_team, match_date
        )
        SELECT ws.match_id, ws.team_id, fm.home_team, fm.away_team, fm.match_date,
            ws.total_events, ws.passes, ws.shots, ws.goals, ws.tackles,
            fm.total_xg, fm.shots_on_target
        FROM ws_stats ws
        LEFT JOIN fm_stats fm ON ws.match_id = fm.match_id AND ws.team_id = fm.team_id
    """)

    # Gold: Player stats
    db.execute("""
        CREATE TABLE gold_player_stats AS
        SELECT player_id, team_id,
            COUNT(DISTINCT match_id) AS matches_played,
            COUNT(*) AS total_events,
            SUM(CASE WHEN event_type = 'Pass' THEN 1 ELSE 0 END) AS passes,
            SUM(CASE WHEN is_shot THEN 1 ELSE 0 END) AS shots,
            SUM(CASE WHEN is_goal THEN 1 ELSE 0 END) AS goals,
            SUM(CASE WHEN event_type = 'Tackle' THEN 1 ELSE 0 END) AS tackles
        FROM silver_events GROUP BY player_id, team_id
    """)

    db.close()
    return db_file


# ---------------------------------------------------------------------------
# Bronze Layer Tests
# ---------------------------------------------------------------------------


class TestBronzeLayer:
    def test_bronze_has_data(self, db_path: Path):
        db = duckdb.connect(str(db_path))
        total = db.execute("SELECT COUNT(*) FROM bronze_matches").fetchone()[0]
        db.close()
        assert total > 0, "Bronze layer is empty"

    def test_bronze_has_both_sources(self, db_path: Path):
        db = duckdb.connect(str(db_path))
        sources = db.execute(
            "SELECT DISTINCT source FROM bronze_matches ORDER BY source"
        ).fetchall()
        db.close()
        source_names = [s[0] for s in sources]
        assert "fotmob" in source_names
        assert "whoscored" in source_names

    def test_bronze_whoscored_count(self, db_path: Path):
        db = duckdb.connect(str(db_path))
        count = db.execute(
            "SELECT COUNT(*) FROM bronze_matches WHERE source = 'whoscored'"
        ).fetchone()[0]
        db.close()
        ws_files = _count_json_files(RAW_WS_DIR)
        assert count == ws_files, f"Expected {ws_files} WS matches, got {count}"

    def test_bronze_fotmob_count(self, db_path: Path):
        db = duckdb.connect(str(db_path))
        count = db.execute(
            "SELECT COUNT(*) FROM bronze_matches WHERE source = 'fotmob'"
        ).fetchone()[0]
        db.close()
        fm_files = _count_json_files(RAW_FM_DIR)
        assert count == fm_files, f"Expected {fm_files} FM matches, got {count}"

    def test_bronze_no_unknown_match_ids(self, db_path: Path):
        db = duckdb.connect(str(db_path))
        unknowns = db.execute(
            "SELECT COUNT(*) FROM bronze_matches WHERE match_id = 'unknown'"
        ).fetchone()[0]
        db.close()
        assert unknowns == 0, f"Found {unknowns} matches with unknown ID"


# ---------------------------------------------------------------------------
# Silver Layer Tests
# ---------------------------------------------------------------------------


class TestSilverEvents:
    def test_silver_events_not_empty(self, db_path: Path):
        db = duckdb.connect(str(db_path))
        count = db.execute("SELECT COUNT(*) FROM silver_events").fetchone()[0]
        db.close()
        assert count > 0

    def test_silver_events_has_required_columns(self, db_path: Path):
        db = duckdb.connect(str(db_path))
        cols = [
            row[0]
            for row in db.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'silver_events'"
            ).fetchall()
        ]
        db.close()
        required = [
            "match_id", "event_type", "player_id", "team_id",
            "x", "y", "minute", "is_shot", "is_goal",
        ]
        for col in required:
            assert col in cols, f"Missing column: {col}"

    def test_silver_events_coordinates_in_range(self, db_path: Path):
        """x and y should be 0-100 (pitch percentage)."""
        db = duckdb.connect(str(db_path))
        result = db.execute(
            "SELECT MIN(x), MAX(x), MIN(y), MAX(y) FROM silver_events"
        ).fetchone()
        db.close()
        min_x, max_x, min_y, max_y = result
        assert min_x >= 0, f"min_x={min_x} < 0"
        assert max_x <= 100, f"max_x={max_x} > 100"
        assert min_y >= 0, f"min_y={min_y} < 0"
        assert max_y <= 100, f"max_y={max_y} > 100"

    def test_silver_events_minutes_reasonable(self, db_path: Path):
        """Match minutes should be between 0 and ~130 (extra time)."""
        db = duckdb.connect(str(db_path))
        max_min = db.execute(
            "SELECT MAX(minute) FROM silver_events"
        ).fetchone()[0]
        min_min = db.execute(
            "SELECT MIN(minute) FROM silver_events"
        ).fetchone()[0]
        db.close()
        assert min_min >= 0
        assert max_min <= 130, f"Max minute {max_min} > 130"

    def test_silver_goals_less_than_shots(self, db_path: Path):
        """Total goals must be <= total shots."""
        db = duckdb.connect(str(db_path))
        result = db.execute(
            "SELECT SUM(CASE WHEN is_shot THEN 1 ELSE 0 END), "
            "SUM(CASE WHEN is_goal THEN 1 ELSE 0 END) "
            "FROM silver_events"
        ).fetchone()
        db.close()
        total_shots, total_goals = result
        assert total_goals <= total_shots, (
            f"Goals ({total_goals}) > Shots ({total_shots})"
        )

    def test_silver_events_per_match_reasonable(self, db_path: Path):
        """Each match should have between 500 and 2500 events."""
        db = duckdb.connect(str(db_path))
        results = db.execute(
            "SELECT match_id, COUNT(*) AS cnt "
            "FROM silver_events GROUP BY match_id"
        ).fetchall()
        db.close()
        for match_id, cnt in results:
            assert 500 <= cnt <= 2500, (
                f"Match {match_id} has {cnt} events (expected 500-2500)"
            )


class TestSilverFotmob:
    def test_silver_fotmob_not_empty(self, db_path: Path):
        db = duckdb.connect(str(db_path))
        count = db.execute("SELECT COUNT(*) FROM silver_fotmob_shots").fetchone()[0]
        db.close()
        assert count > 0

    def test_silver_fotmob_xg_range(self, db_path: Path):
        """xG per shot should be between 0 and 1."""
        db = duckdb.connect(str(db_path))
        result = db.execute(
            "SELECT MIN(xg), MAX(xg) FROM silver_fotmob_shots WHERE xg IS NOT NULL"
        ).fetchone()
        db.close()
        min_xg, max_xg = result
        assert min_xg >= 0, f"min xG={min_xg} < 0"
        assert max_xg <= 1.0, f"max xG={max_xg} > 1.0"

    def test_silver_fotmob_has_team_info(self, db_path: Path):
        db = duckdb.connect(str(db_path))
        nulls = db.execute(
            "SELECT COUNT(*) FROM silver_fotmob_shots "
            "WHERE home_team IS NULL OR away_team IS NULL"
        ).fetchone()[0]
        db.close()
        assert nulls == 0, f"{nulls} shots missing team info"

    def test_silver_fotmob_goals_match_event_type(self, db_path: Path):
        """is_goal should be True only when event_type = 'Goal'."""
        db = duckdb.connect(str(db_path))
        mismatch = db.execute(
            "SELECT COUNT(*) FROM silver_fotmob_shots "
            "WHERE is_goal != (event_type = 'Goal')"
        ).fetchone()[0]
        db.close()
        assert mismatch == 0, f"{mismatch} rows have mismatched is_goal"


# ---------------------------------------------------------------------------
# Gold Layer Tests
# ---------------------------------------------------------------------------


class TestGoldMatchSummary:
    def test_gold_match_summary_not_empty(self, db_path: Path):
        db = duckdb.connect(str(db_path))
        count = db.execute("SELECT COUNT(*) FROM gold_match_summary").fetchone()[0]
        db.close()
        assert count > 0

    def test_gold_two_teams_per_match(self, db_path: Path):
        """Each match should have exactly 2 team rows."""
        db = duckdb.connect(str(db_path))
        results = db.execute(
            "SELECT match_id, COUNT(DISTINCT team_id) AS teams "
            "FROM gold_match_summary GROUP BY match_id"
        ).fetchall()
        db.close()
        for match_id, teams in results:
            assert teams == 2, f"Match {match_id} has {teams} teams (expected 2)"

    def test_gold_goals_non_negative(self, db_path: Path):
        db = duckdb.connect(str(db_path))
        neg = db.execute(
            "SELECT COUNT(*) FROM gold_match_summary WHERE goals < 0"
        ).fetchone()[0]
        db.close()
        assert neg == 0


class TestGoldPlayerStats:
    def test_gold_player_stats_not_empty(self, db_path: Path):
        db = duckdb.connect(str(db_path))
        count = db.execute("SELECT COUNT(*) FROM gold_player_stats").fetchone()[0]
        db.close()
        assert count > 0

    def test_gold_player_goals_leq_shots(self, db_path: Path):
        """No player should have more goals than shots."""
        db = duckdb.connect(str(db_path))
        violations = db.execute(
            "SELECT COUNT(*) FROM gold_player_stats WHERE goals > shots"
        ).fetchone()[0]
        db.close()
        assert violations == 0, f"{violations} players have goals > shots"

    def test_gold_player_matches_positive(self, db_path: Path):
        db = duckdb.connect(str(db_path))
        zero = db.execute(
            "SELECT COUNT(*) FROM gold_player_stats WHERE matches_played <= 0"
        ).fetchone()[0]
        db.close()
        assert zero == 0


# ---------------------------------------------------------------------------
# NaN Sanitizer Tests
# ---------------------------------------------------------------------------


class TestSanitizeJson:
    def test_sanitize_nan_with_space(self):
        assert _sanitize_json('{"val": NaN}') == '{"val": null}'

    def test_sanitize_nan_without_space(self):
        assert _sanitize_json('{"val":NaN}') == '{"val":null}'

    def test_sanitize_no_nan(self):
        original = '{"val": 1.5}'
        assert _sanitize_json(original) == original
