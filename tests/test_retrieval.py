"""
Test retrieval on ingested data.

Quick validation that semantic search works on the football match data.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from football_rag.storage.vector_store import VectorStore


def test_queries():
    """Test various query patterns."""

    print("=" * 80)
    print("TESTING RETRIEVAL ON INGESTED DATA")
    print("=" * 80)

    # Initialize VectorStore
    store = VectorStore(host="localhost", port=8000)

    # Get stats
    stats = store.get_stats()
    print(f"\nCollection: {stats['collection_name']}")
    print(f"Total documents: {stats['document_count']}")
    print(f"Embedding model: {stats['embedding_model']}")

    # Test queries
    test_cases = [
        ("PSV match results", 3),
        ("Feyenoord attacking performance", 3),
        ("shot quality and xG", 3),
        ("NEC Nijmegen", 2),
        ("teams with high expected goals", 3),
    ]

    print("\n" + "=" * 80)
    print("QUERY TESTS")
    print("=" * 80)

    for query, k in test_cases:
        print(f"\nQuery: '{query}' (top {k})")
        print("-" * 80)

        results = store.search(query, k=k)

        for i, result in enumerate(results, 1):
            print(f"\n[{i}] ID: {result['id']}")
            print(f"    Distance: {result['distance']:.4f}")
            print(f"    Teams: {result['metadata'].get('home_team', 'N/A')} vs {result['metadata'].get('away_team', 'N/A')}")
            print(f"    Type: {result['metadata'].get('chunk_type', 'N/A')}")
            print(f"    Preview: {result['document'][:150]}...")

    # Test metadata filtering
    print("\n" + "=" * 80)
    print("METADATA FILTERING TESTS")
    print("=" * 80)

    print("\nFilter: chunk_type='match_summary'")
    print("-" * 80)
    results = store.search(
        "match result",
        k=3,
        where={"chunk_type": "match_summary"}
    )
    print(f"Found {len(results)} match summary chunks")
    for result in results:
        print(f"  - {result['metadata']['home_team']} vs {result['metadata']['away_team']}")

    print("\nFilter: chunk_type='shots_analysis'")
    print("-" * 80)
    results = store.search(
        "shooting",
        k=3,
        where={"chunk_type": "shots_analysis"}
    )
    print(f"Found {len(results)} shots analysis chunks")
    for result in results:
        xg_home = result['metadata'].get('home_xg', 0)
        xg_away = result['metadata'].get('away_xg', 0)
        print(f"  - {result['metadata']['home_team']} vs {result['metadata']['away_team']}")
        print(f"    xG: {xg_home:.2f} - {xg_away:.2f}")

    print("\n" + "=" * 80)
    print("✅ RETRIEVAL TESTS COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    test_queries()
