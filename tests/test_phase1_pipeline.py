"""
Phase 1 Pipeline End-to-End Verification Tests.

Tests the complete data flow from Bronze → Silver → Gold → Embeddings.
"""

from pathlib import Path

import duckdb
import pytest

# Paths
PROJECT_ROOT = Path(__file__).parents[1]
DUCKDB_PATH = PROJECT_ROOT / "data" / "lakehouse.duckdb"


@pytest.fixture
def db():
    """DuckDB connection fixture."""
    conn = duckdb.connect(str(DUCKDB_PATH))
    yield conn
    conn.close()


class TestBronzeLayer:
    """Test Bronze Layer - Raw Scraped Data."""

    def test_bronze_matches_exist(self, db):
        """Bronze matches table should have 379 rows."""
        count = db.execute("SELECT COUNT(*) FROM main.bronze_matches").fetchone()[0]
        assert count == 379, f"Expected 379 bronze matches, got {count}"

    def test_bronze_has_json_data(self, db):
        """Bronze matches should contain JSON data."""
        sample = db.execute("""
            SELECT match_id, data::VARCHAR
            FROM main.bronze_matches
            LIMIT 1
        """).fetchone()

        assert sample is not None, "No bronze matches found"
        assert sample[0] is not None, "Match ID is null"
        assert sample[1] is not None, "Match data is null"
        assert len(sample[1]) > 100, "Match data too small"


class TestMatchMapping:
    """Test Match Mapping - WhoScored ↔ FotMob."""

    def test_match_mapping_coverage(self, db):
        """Match mapping should have 99%+ coverage (188/189 matches)."""
        count = db.execute("SELECT COUNT(*) FROM main.match_mapping").fetchone()[0]
        coverage = (count / 189) * 100

        assert count >= 188, f"Expected ≥188 mapped matches, got {count}"
        assert coverage >= 99.0, f"Coverage {coverage:.1f}% below 99%"

    def test_match_mapping_completeness(self, db):
        """Mapped matches should have all required fields."""
        sample = db.execute("""
            SELECT whoscored_match_id, fotmob_match_id, home_team, away_team
            FROM main.match_mapping
            LIMIT 1
        """).fetchone()

        assert sample is not None, "No mapped matches found"
        assert all(sample), "Incomplete mapping data"
        assert sample[0] != sample[1], "WhoScored and FotMob IDs should differ"


class TestSilverLayer:
    """Test Silver Layer - Events with Tactical Metrics."""

    def test_silver_events_count(self, db):
        """Silver events should have 279K+ rows."""
        count = db.execute("SELECT COUNT(*) FROM main_main.silver_events").fetchone()[0]
        assert count >= 279000, f"Expected ≥279K events, got {count:,}"

    def test_silver_events_schema(self, db):
        """Silver events should have all required columns."""
        columns = db.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'main_main'
            AND table_name = 'silver_events'
        """).fetchall()

        col_names = [c[0] for c in columns]
        required = ['match_id', 'type_display_name', 'x', 'y', 'outcome_type_display_name']

        for col in required:
            assert col in col_names, f"Missing required column: {col}"

    def test_silver_team_metrics_exist(self, db):
        """Team metrics should have tactical data."""
        count = db.execute("SELECT COUNT(*) FROM main_main.silver_team_metrics").fetchone()[0]
        assert count >= 378, f"Expected ≥378 team metrics, got {count}"

        # Check metrics are not null
        sample = db.execute("""
            SELECT ppda, field_tilt, progressive_passes, shots_on_target
            FROM main_main.silver_team_metrics
            WHERE ppda IS NOT NULL
            LIMIT 1
        """).fetchone()

        assert sample is not None, "No team metrics found"
        assert sample[0] > 0, "PPDA should be > 0"
        assert 0 <= sample[1] <= 100, "Field tilt should be 0-100%"


class TestGoldLayer:
    """Test Gold Layer - Match Summaries."""

    def test_gold_match_summaries_count(self, db):
        """Gold layer should have 188 match summaries."""
        count = db.execute("SELECT COUNT(*) FROM main_main.gold_match_summaries").fetchone()[0]
        assert count == 188, f"Expected 188 gold summaries, got {count}"

    def test_gold_match_summaries_completeness(self, db):
        """Match summaries should have all key fields."""
        sample = db.execute("""
            SELECT
                fotmob_match_id,
                home_team,
                away_team,
                home_goals,
                away_goals,
                home_ppda,
                away_ppda
            FROM main_main.gold_match_summaries
            LIMIT 1
        """).fetchone()

        assert sample is not None, "No gold summaries found"
        assert all(x is not None for x in sample[:5]), "Missing required fields"
        assert sample[3] >= 0 and sample[4] >= 0, "Invalid scores"

    def test_gold_xg_coverage(self, db):
        """At least 50% of matches should have xG data."""
        xg_coverage = db.execute("""
            SELECT
                COUNT(*) FILTER (WHERE home_total_xg > 0) * 100.0 / COUNT(*) as pct
            FROM main_main.gold_match_summaries
        """).fetchone()[0]

        assert xg_coverage >= 50.0, f"xG coverage {xg_coverage:.1f}% below 50%"


class TestEmbeddingsLayer:
    """Test Embeddings Layer - Vector Search."""

    def test_embeddings_count_matches_gold(self, db):
        """Embeddings count should match gold layer count."""
        gold_count = db.execute("SELECT COUNT(*) FROM main_main.gold_match_summaries").fetchone()[0]
        emb_count = db.execute("SELECT COUNT(*) FROM main.gold_match_embeddings").fetchone()[0]

        assert emb_count == gold_count, f"Embeddings ({emb_count}) != Gold ({gold_count})"

    def test_embeddings_structure(self, db):
        """Embeddings should have correct structure."""
        sample = db.execute("""
            SELECT match_id, embedding, summary_text
            FROM main.gold_match_embeddings
            LIMIT 1
        """).fetchone()

        assert sample is not None, "No embeddings found"
        assert sample[0] is not None, "Match ID is null"
        assert sample[1] is not None, "Embedding is null"
        assert len(sample[1]) == 768, f"Embedding should be 768-dim, got {len(sample[1])}"
        assert sample[2] is not None, "Summary text is null"
        assert len(sample[2]) > 50, "Summary text too short"

    def test_vector_search_works(self, db):
        """VSS extension should enable vector search."""
        db.execute("LOAD vss")

        # Get a sample embedding
        sample = db.execute("""
            SELECT embedding
            FROM main.gold_match_embeddings
            LIMIT 1
        """).fetchone()

        assert sample is not None, "No embeddings to test with"

        # Test array_distance function works
        results = db.execute("""
            SELECT COUNT(*)
            FROM main.gold_match_embeddings
            WHERE array_distance(embedding, ?::FLOAT[768]) < 2.0
        """, [sample[0]]).fetchone()[0]

        assert results > 0, "Vector search returned no results"


class TestDataLineage:
    """Test Data Lineage - Flow Validation."""

    def test_lineage_integrity(self, db):
        """Data should flow correctly: Bronze → Mapping → Gold → Embeddings."""
        counts = db.execute("""
            SELECT
                (SELECT COUNT(*) FROM main.bronze_matches) as bronze,
                (SELECT COUNT(*) FROM main.match_mapping) as mapping,
                (SELECT COUNT(*) FROM main_main.gold_match_summaries) as gold,
                (SELECT COUNT(*) FROM main.gold_match_embeddings) as embeddings
        """).fetchone()

        bronze, mapping, gold, embeddings = counts

        # Mapping should be subset of Bronze
        assert mapping <= bronze, f"Mapping ({mapping}) > Bronze ({bronze})"

        # Gold should be subset of Mapping
        assert gold <= mapping, f"Gold ({gold}) > Mapping ({mapping})"

        # Embeddings should match Gold
        assert embeddings == gold, f"Embeddings ({embeddings}) != Gold ({gold})"

    def test_no_orphaned_records(self, db):
        """Gold layer should only contain mapped matches."""
        orphans = db.execute("""
            SELECT COUNT(*)
            FROM main_main.gold_match_summaries g
            WHERE g.fotmob_match_id NOT IN (
                SELECT fotmob_match_id FROM main.match_mapping
            )
        """).fetchone()[0]

        assert orphans == 0, f"Found {orphans} orphaned gold records"
