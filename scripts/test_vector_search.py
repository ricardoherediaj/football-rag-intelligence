"""
Test vector similarity search on gold_match_embeddings.

Verifies DuckDB VSS extension is working and embeddings are meaningful.
"""

from pathlib import Path

import duckdb
from sentence_transformers import SentenceTransformer

# Paths
PROJECT_ROOT = Path(__file__).parents[1]
DUCKDB_PATH = PROJECT_ROOT / "data" / "lakehouse.duckdb"

# Model
MODEL_NAME = "sentence-transformers/all-mpnet-base-v2"


def test_vector_search():
    """Test semantic search for tactical patterns."""
    print("=" * 80)
    print("VECTOR SIMILARITY SEARCH TEST")
    print("=" * 80)

    # Load model
    print(f"\nLoading model: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME)

    # Connect to DuckDB
    print(f"Connecting to: {DUCKDB_PATH}")
    db = duckdb.connect(str(DUCKDB_PATH))
    db.execute("LOAD vss")

    # Verify embeddings exist
    count = db.execute("SELECT COUNT(*) FROM gold_match_embeddings").fetchone()[0]
    print(f"✓ Found {count} embeddings in database")

    # Test queries
    queries = [
        "High pressing, aggressive defense, many tackles in opponent half",
        "Patient possession, vertical passes, build-up from the back",
        "Many shots on target, high expected goals, clinical finishing",
    ]

    for i, query in enumerate(queries, 1):
        print(f"\n{'=' * 80}")
        print(f"Query {i}: '{query}'")
        print("=" * 80)

        # Encode query
        query_emb = model.encode(query)

        # Semantic search
        results = db.execute(
            """
            SELECT
                match_id,
                summary_text,
                array_distance(embedding, ?::FLOAT[768]) AS distance
            FROM gold_match_embeddings
            ORDER BY distance
            LIMIT 5
        """,
            [query_emb.tolist()],
        ).fetchall()

        # Display results
        for rank, (match_id, summary, dist) in enumerate(results, 1):
            print(f"\n{rank}. Match ID: {match_id} (distance: {dist:.4f})")
            print(f"   {summary[:200]}...")

    print("\n" + "=" * 80)
    print("✅ Vector search test completed successfully")
    print("=" * 80)

    db.close()


if __name__ == "__main__":
    test_vector_search()
