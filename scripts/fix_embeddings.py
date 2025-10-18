#!/usr/bin/env python3
"""Fix embedding model mismatch by re-creating collection with all-mpnet-base-v2."""

import chromadb
from chromadb.utils import embedding_functions

print("=" * 60)
print("FIXING EMBEDDING MODEL MISMATCH")
print("=" * 60)

# Connect to ChromaDB
client = chromadb.HttpClient(host="localhost", port=8000)

# Get current collection
old_collection = client.get_collection("football_matches_eredivisie_2025")
print(f"\n1. Found existing collection with {old_collection.count()} documents")

# Get all data from old collection
print("2. Extracting all documents...")
all_data = old_collection.get(include=["documents", "metadatas", "embeddings"])
print(f"   ✅ Extracted {len(all_data['ids'])} documents")

# Delete old collection
print("3. Deleting old collection (wrong embeddings)...")
client.delete_collection("football_matches_eredivisie_2025")
print("   ✅ Deleted")

# Create new collection with correct embedding function
print("4. Creating new collection with all-mpnet-base-v2...")
sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-mpnet-base-v2"
)

new_collection = client.create_collection(
    name="football_matches_eredivisie_2025",
    embedding_function=sentence_transformer_ef,
    metadata={
        "description": "Football match data with semantic search",
        "embedding_model": "all-mpnet-base-v2",
    },
)
print("   ✅ Created with all-mpnet-base-v2")

# Re-add documents (will re-embed with correct model)
print("5. Re-adding documents with new embeddings...")
new_collection.add(
    ids=all_data["ids"],
    documents=all_data["documents"],
    metadatas=all_data["metadatas"],
)
print(f"   ✅ Added {new_collection.count()} documents")

print("\n" + "=" * 60)
print("✅ FIXED - Collection now uses all-mpnet-base-v2")
print("=" * 60)
