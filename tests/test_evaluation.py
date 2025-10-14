"""RAG Evaluation Suite - Course MVP Requirement

Tests retrieval quality with metrics:
- Hit@K: Is relevant doc in top K results?
- MRR: Mean Reciprocal Rank of first relevant result
- Tactical Accuracy: Do results make football sense?
"""

import logging
from typing import List, Tuple
from football_rag.models.rag_pipeline import RAGPipeline

logging.basicConfig(level=logging.WARNING)


# Test dataset: (query, expected_keyword_in_result)
TEST_QUERIES: List[Tuple[str, str]] = [
    # xG and scoring queries
    ("Which teams had high xG?", "xG"),
    ("Teams with good shot quality", "xG"),

    # Specific match queries
    ("Fortuna Sittard result", "Fortuna Sittard"),
    ("PSV tactical approach", "PSV Eindhoven"),
    ("Feyenoord performance", "Feyenoord"),

    # Tactical queries
    ("Teams with direct passing", "verticality"),
    ("Possession-based teams", "possession"),
    ("High pressing teams", "possession"),

    # Score queries
    ("Big wins", "6-1"),
    ("Close matches", "1-1"),
]


def evaluate_hit_at_k(rag: RAGPipeline, queries: List[Tuple[str, str]], k: int = 5) -> float:
    """Calculate Hit@K metric.

    Args:
        rag: RAG pipeline instance
        queries: List of (query, expected_keyword) tuples
        k: Number of top results to check

    Returns:
        Hit rate (0.0 to 1.0)
    """
    hits = 0

    for query, expected in queries:
        results = rag.retrieve(query, k=k)

        # Check if expected keyword appears in any of top K results
        found = any(
            expected.lower() in doc['text'].lower() or
            expected.lower() in str(doc['metadata']).lower()
            for doc in results
        )

        if found:
            hits += 1

    return hits / len(queries)


def evaluate_mrr(rag: RAGPipeline, queries: List[Tuple[str, str]]) -> float:
    """Calculate Mean Reciprocal Rank.

    MRR measures average rank of first relevant result.
    MRR = 1 means relevant doc always at rank 1.

    Args:
        rag: RAG pipeline instance
        queries: List of (query, expected_keyword) tuples

    Returns:
        MRR score (0.0 to 1.0)
    """
    reciprocal_ranks = []

    for query, expected in queries:
        results = rag.retrieve(query, k=10)

        # Find rank of first relevant result
        for rank, doc in enumerate(results, start=1):
            if (expected.lower() in doc['text'].lower() or
                expected.lower() in str(doc['metadata']).lower()):
                reciprocal_ranks.append(1.0 / rank)
                break
        else:
            reciprocal_ranks.append(0.0)

    return sum(reciprocal_ranks) / len(reciprocal_ranks)


def evaluate_tactical_accuracy(rag: RAGPipeline) -> dict:
    """Validate tactical accuracy with specific queries.

    Returns:
        Dict with tactical validation results
    """
    results = {}

    # Test 1: High xG query should return matches with xG > 1.5
    query = "Which teams had high expected goals?"
    docs = rag.retrieve(query, k=3)

    high_xg_matches = [
        doc for doc in docs
        if doc['metadata'].get('xg_home', 0) > 1.5 or
           doc['metadata'].get('xg_away', 0) > 1.5
    ]
    results['high_xg_accuracy'] = len(high_xg_matches) / len(docs)

    # Test 2: Specific team query returns correct team
    query = "PSV Eindhoven match"
    docs = rag.retrieve(query, k=1)

    psv_found = any(
        'PSV' in doc['metadata'].get('home_team', '') or
        'PSV' in doc['metadata'].get('away_team', '')
        for doc in docs
    )
    results['team_query_accuracy'] = 1.0 if psv_found else 0.0

    return results


def run_evaluation():
    """Run full evaluation suite."""
    print("="*60)
    print("🎯 RAG EVALUATION - Course MVP")
    print("="*60)

    # Initialize RAG
    rag = RAGPipeline()

    # Hit@5
    print("\n📊 Hit@5 Metric")
    print("-" * 60)
    hit_at_5 = evaluate_hit_at_k(rag, TEST_QUERIES, k=5)
    print(f"Hit@5: {hit_at_5:.2%} ({int(hit_at_5 * len(TEST_QUERIES))}/{len(TEST_QUERIES)} queries)")

    # MRR
    print("\n📊 Mean Reciprocal Rank (MRR)")
    print("-" * 60)
    mrr = evaluate_mrr(rag, TEST_QUERIES)
    print(f"MRR: {mrr:.3f}")

    # Tactical Accuracy
    print("\n📊 Tactical Accuracy")
    print("-" * 60)
    tactical = evaluate_tactical_accuracy(rag)
    print(f"High xG Query Accuracy: {tactical['high_xg_accuracy']:.2%}")
    print(f"Team Query Accuracy: {tactical['team_query_accuracy']:.2%}")

    # Overall Assessment
    print("\n" + "="*60)
    print("✅ EVALUATION SUMMARY")
    print("="*60)

    all_pass = hit_at_5 >= 0.80 and mrr >= 0.75

    if all_pass:
        print("✅ All metrics PASS - Ready to scale to 54 matches")
    else:
        print("⚠️  Some metrics below threshold - Review retrieval strategy")

    print(f"\nTest Dataset: {len(TEST_QUERIES)} queries")
    print(f"Target: Hit@5 ≥ 80%, MRR ≥ 0.75")
    print("="*60)

    return {
        'hit_at_5': hit_at_5,
        'mrr': mrr,
        'tactical_accuracy': tactical,
        'pass': all_pass
    }


if __name__ == "__main__":
    results = run_evaluation()
    print(f"\n📝 Results: {results}")
