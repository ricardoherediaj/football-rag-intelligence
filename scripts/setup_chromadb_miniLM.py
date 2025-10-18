#!/usr/bin/env python3
"""Setup ChromaDB with all-MiniLM-L6-v2 (ChromaDB default, already cached)."""

import chromadb
from chromadb.utils import embedding_functions

print("=" * 60)
print("SETUP: ChromaDB with all-MiniLM-L6-v2 (fast)")
print("=" * 60)

client = chromadb.HttpClient(host="localhost", port=8000)

# Delete old collection if exists
try:
    client.delete_collection("football_matches_eredivisie_2025")
    print("✅ Deleted old collection")
except:
    print("⚠️  No existing collection to delete")

# Create with default embedding (all-MiniLM-L6-v2)
print("\nCreating collection with all-MiniLM-L6-v2 (ChromaDB default)...")

# Use default embedding function (no need to specify, it's already cached)
collection = client.create_collection(
    name="football_matches_eredivisie_2025",
    metadata={
        "description": "Football match data with semantic search",
        "embedding_model": "all-MiniLM-L6-v2",
        "note": "Using ChromaDB default for MVP. Upgrade to bge-small-en-v1.5 for production.",
    },
)

print(f"✅ Collection created: {collection.name}")
print(f"   Documents: {collection.count()}")
print(f"   Metadata: {collection.metadata}")

print("\n" + "=" * 60)
print("✅ READY - Now run ingestion")
print("=" * 60)
