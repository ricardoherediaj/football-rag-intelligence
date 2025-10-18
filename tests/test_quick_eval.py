#!/usr/bin/env python3
"""Quick eval - tests only retrieval (no LLM, fast)."""

import os
from dotenv import load_dotenv
import chromadb

load_dotenv()


def test_chromadb():
    """Test ChromaDB connection and retrieval."""
    print("=" * 60)
    print("QUICK EVAL - ChromaDB Retrieval Only")
    print("=" * 60)

    # Connect to ChromaDB
    print("\n1. Connecting to ChromaDB...")
    client = chromadb.HttpClient(host="localhost", port=8000)

    # Get collection
    print("2. Getting collection...")
    collection = client.get_collection("football_matches_eredivisie_2025")
    print(f"   ✅ Collection exists with {collection.count()} documents")

    # Test queries
    test_queries = [
        "Which teams had high xG?",
        "PSV Eindhoven performance",
        "Feyenoord result",
    ]

    print(f"\n3. Testing {len(test_queries)} retrieval queries...")
    for query in test_queries:
        results = collection.query(query_texts=[query], n_results=3)
        print(f"   ✅ '{query[:40]}...' -> {len(results['ids'][0])} results")

    print("\n" + "=" * 60)
    print("✅ CHROMADB WORKING - Ready for full eval")
    print("=" * 60)


if __name__ == "__main__":
    test_chromadb()
