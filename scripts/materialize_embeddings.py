"""
Materialize gold_match_embeddings asset directly.

Bypasses Dagster UI for direct execution.
"""

from pathlib import Path

import duckdb
from sentence_transformers import SentenceTransformer

# Paths
PROJECT_ROOT = Path(__file__).parents[1]
DUCKDB_PATH = PROJECT_ROOT / "data" / "lakehouse.duckdb"

# Model
MODEL_NAME = "sentence-transformers/all-mpnet-base-v2"


def materialize_embeddings():
    """Generate embeddings for gold_match_summaries."""
    print("=" * 80)
    print("MATERIALIZING gold_match_embeddings")
    print("=" * 80)

    # Load model
    print(f"\n[1/6] Loading model: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME)
    print("✓ Model loaded")

    # Connect to DuckDB
    print(f"\n[2/6] Connecting to: {DUCKDB_PATH}")
    db = duckdb.connect(str(DUCKDB_PATH))
    print("✓ Connected")

    # Install VSS extension
    print("\n[3/6] Setting up DuckDB VSS extension")
    db.execute("INSTALL vss")
    db.execute("LOAD vss")
    db.execute("SET hnsw_enable_experimental_persistence = true")
    print("✓ VSS extension loaded")

    # Fetch summaries
    print("\n[4/6] Fetching match summaries")
    summaries = db.execute("""
        SELECT match_id, summary_text
        FROM main_main.gold_match_summaries
        ORDER BY match_id
    """).fetchall()
    print(f"✓ Found {len(summaries)} match summaries")

    # Generate embeddings
    print(f"\n[5/6] Generating {len(summaries)} embeddings (768-dim vectors)")
    match_ids = [s[0] for s in summaries]
    texts = [s[1] for s in summaries]
    embeddings = model.encode(texts, show_progress_bar=True)
    print("✓ Embeddings generated")

    # Create table and insert
    print("\n[6/6] Creating table and HNSW index")
    db.execute("""
        CREATE OR REPLACE TABLE gold_match_embeddings (
            match_id VARCHAR PRIMARY KEY,
            embedding FLOAT[768],
            summary_text TEXT
        )
    """)

    for match_id, text, emb in zip(match_ids, texts, embeddings):
        db.execute(
            "INSERT INTO gold_match_embeddings VALUES (?, ?, ?)",
            [match_id, emb.tolist(), text],
        )

    db.execute("""
        CREATE INDEX match_vss_idx
        ON gold_match_embeddings
        USING HNSW (embedding)
    """)

    # Verify
    count = db.execute("SELECT COUNT(*) FROM gold_match_embeddings").fetchone()[0]
    print(f"✓ Created {count} embeddings with HNSW index")

    print("\n" + "=" * 80)
    print("✅ gold_match_embeddings materialized successfully")
    print("=" * 80)

    db.close()


if __name__ == "__main__":
    materialize_embeddings()
