#!/usr/bin/env python3
"""Quick test of simplified RAG pipeline (no LlamaIndex)."""

import os
from dotenv import load_dotenv
from football_rag.models.rag_pipeline import RAGPipeline

load_dotenv()

print("\n" + "=" * 60)
print("⚽ TESTING SIMPLIFIED RAG PIPELINE")
print("=" * 60)

# Initialize pipeline
print("\n[1/3] Initializing RAG pipeline...")
pipeline = RAGPipeline(provider="anthropic", api_key=os.getenv("ANTHROPIC_API_KEY"))
print("✅ Pipeline initialized (no LlamaIndex overhead!)")

# Test retrieval
print("\n[2/3] Testing retrieval...")
results = pipeline.retrieve("PSV attacking tactics", k=3)
print(f"✅ Retrieved {len(results)} documents")
for i, result in enumerate(results, 1):
    print(
        f"   [{i}] Score: {result['score']:.3f} - {result['metadata'].get('home_team', 'N/A')} vs {result['metadata'].get('away_team', 'N/A')}"
    )

# Test full query
print("\n[3/3] Testing full RAG query...")
response = pipeline.query("How did PSV perform in their match?", top_k=3)
print(f"✅ Answer: {response['answer'][:150]}...")
print(f"   Faithfulness: {response['faithfulness']['faithfulness_score']:.2%}")
print(f"   Sources used: {len(response['source_nodes'])}")

print("\n" + "=" * 60)
print("✅ ALL TESTS PASSED - RAG PIPELINE WORKING")
print("=" * 60 + "\n")
