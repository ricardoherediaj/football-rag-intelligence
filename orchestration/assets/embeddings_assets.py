"""
Generate vector embeddings for match summaries using sentence-transformers.

Enables semantic search over tactical narratives via DuckDB VSS extension.
"""

from pathlib import Path

import duckdb
from dagster import AssetExecutionContext, asset
from sentence_transformers import SentenceTransformer

# Path to DuckDB lakehouse
DUCKDB_PATH = Path(__file__).parents[2] / "data" / "lakehouse.duckdb"

# Embedding model (768-dim, same as MVP)
MODEL_NAME = "sentence-transformers/all-mpnet-base-v2"


@asset(
    deps=["dbt_gold_models"],
    compute_kind="embeddings",
    group_name="vectorization",
)
def gold_match_embeddings(context: AssetExecutionContext) -> None:
    """
    Generate embeddings for gold_match_summaries and create HNSW index.

    Creates table: gold_match_embeddings
    Columns:
    - match_id (VARCHAR): WhoScored match identifier
    - embedding (FLOAT[768]): Dense vector representation
    - summary_text (TEXT): Source text for debugging/display

    Enables vector similarity search with DuckDB VSS extension.
    """
    context.log.info(f"Loading embedding model: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME)

    # Connect to DuckDB
    db = duckdb.connect(str(DUCKDB_PATH))

    # Install and load VSS extension
    context.log.info("Setting up DuckDB VSS extension")
    db.execute("INSTALL vss")
    db.execute("LOAD vss")
    db.execute("SET hnsw_enable_experimental_persistence = true")

    # Fetch match summaries
    context.log.info("Fetching match summaries from gold_match_summaries")
    summaries = db.execute("""
        SELECT match_id, summary_text
        FROM main_main.gold_match_summaries
        ORDER BY match_id
    """).fetchall()

    context.log.info(f"Found {len(summaries)} match summaries")

    # Generate embeddings
    match_ids = [s[0] for s in summaries]
    texts = [s[1] for s in summaries]

    context.log.info("Encoding summaries to 768-dim vectors")
    embeddings = model.encode(texts, show_progress_bar=False)

    # Create embeddings table
    context.log.info("Creating gold_match_embeddings table")
    db.execute("""
        CREATE OR REPLACE TABLE gold_match_embeddings (
            match_id VARCHAR PRIMARY KEY,
            embedding FLOAT[768],
            summary_text TEXT
        )
    """)

    # Insert embeddings
    context.log.info("Inserting embeddings")
    for match_id, text, emb in zip(match_ids, texts, embeddings):
        db.execute(
            "INSERT INTO gold_match_embeddings VALUES (?, ?, ?)",
            [match_id, emb.tolist(), text],
        )

    # Create HNSW index for fast similarity search
    context.log.info("Creating HNSW index on embeddings")
    db.execute("""
        CREATE INDEX match_vss_idx
        ON gold_match_embeddings
        USING HNSW (embedding)
    """)

    # Verify
    count = db.execute("SELECT COUNT(*) FROM gold_match_embeddings").fetchone()[0]
    context.log.info(f"✅ Created {count} embeddings with HNSW index")

    db.close()
