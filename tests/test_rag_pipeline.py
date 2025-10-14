"""Test RAG pipeline with LlamaIndex."""

import logging
from football_rag.models.rag_pipeline import RAGPipeline

logging.basicConfig(level=logging.INFO)


def test_retrieval():
    """Test retrieval only."""
    rag = RAGPipeline()

    query = "Which teams played with direct vertical passing?"
    results = rag.retrieve(query, k=3)

    print(f"\n🔍 Query: {query}\n")
    for i, doc in enumerate(results, 1):
        print(f"Result {i} (score: {doc['score']:.3f})")
        print(f"Team: {doc['metadata'].get('home_team')} vs {doc['metadata'].get('away_team')}")
        vert = doc['metadata'].get('verticality')
        if vert is not None:
            print(f"Verticality: {vert:.1f}%")
        print(f"Text preview: {doc['text'][:200]}...\n")


def test_query():
    """Test full RAG query."""
    rag = RAGPipeline()

    question = "How did PSV play tactically?"
    response = rag.query(question, top_k=2)

    print(f"\n💬 Question: {question}\n")
    print(f"Answer: {response['answer']}\n")
    print(f"Sources ({len(response['source_nodes'])}):")
    for i, node in enumerate(response['source_nodes'], 1):
        print(f"  {i}. {node['metadata'].get('home_team')} vs {node['metadata'].get('away_team')} (score: {node['score']:.3f})")


if __name__ == "__main__":
    print("=" * 60)
    print("TEST 1: Retrieval Only")
    print("=" * 60)
    test_retrieval()

    print("\n" + "=" * 60)
    print("TEST 2: Full RAG Query")
    print("=" * 60)
    test_query()
