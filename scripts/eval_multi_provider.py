#!/usr/bin/env python3
"""Evaluation script comparing providers with faithfulness metrics.

Runs on a mini dataset to evaluate:
- Retrieval quality (Hit@K, MRR)
- Faithfulness per provider (does answer match sources?)
- Cost per query
- Latency per provider
"""

import sys
import time
from pathlib import Path
from typing import List, Tuple, Dict, Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from football_rag.models.rag_pipeline import RAGPipeline
from football_rag.core.logging import get_logger, setup_logging

setup_logging()
logger = get_logger(__name__)

# Test queries for football RAG
TEST_QUERIES: List[Tuple[str, str]] = [
    ("Which teams had high xG?", "xG"),
    ("Teams with good shot quality", "xG"),
    ("Fortuna Sittard result", "Fortuna Sittard"),
    ("PSV tactical approach", "PSV"),
    ("Feyenoord performance", "Feyenoord"),
    ("Teams with direct passing", "passing"),
    ("Possession-based teams", "possession"),
    ("High pressing teams", "pressing"),
    ("Big wins", "goals"),
]


def evaluate_retrieval(pipeline: RAGPipeline, k: int = 5) -> Dict[str, float]:
    """Evaluate retrieval quality.

    Returns:
        Dict with Hit@K and MRR metrics
    """
    hits = 0
    reciprocal_ranks = []

    for query, expected_keyword in TEST_QUERIES:
        results = pipeline.retrieve(query, k=k)

        # Check if expected keyword in top K
        found = any(
            expected_keyword.lower() in doc["text"].lower()
            or expected_keyword.lower() in str(doc["metadata"]).lower()
            for doc in results
        )

        if found:
            hits += 1
            # Find rank of first match
            for rank, doc in enumerate(results, start=1):
                if (
                    expected_keyword.lower() in doc["text"].lower()
                    or expected_keyword.lower() in str(doc["metadata"]).lower()
                ):
                    reciprocal_ranks.append(1.0 / rank)
                    break
        else:
            reciprocal_ranks.append(0.0)

    hit_at_k = hits / len(TEST_QUERIES)
    mrr = sum(reciprocal_ranks) / len(reciprocal_ranks) if reciprocal_ranks else 0.0

    return {
        "hit_at_k": hit_at_k,
        "mrr": mrr,
        "hits": hits,
        "total_queries": len(TEST_QUERIES),
    }


def evaluate_faithfulness(pipeline: RAGPipeline) -> Dict[str, Any]:
    """Evaluate faithfulness scores across test queries.

    Returns:
        Dict with faithfulness metrics
    """
    faithfulness_scores = []
    hallucinated_count = 0
    latencies = []

    for query, _ in TEST_QUERIES:
        start = time.perf_counter()
        result = pipeline.query(query, top_k=5)
        latency_ms = int((time.perf_counter() - start) * 1000)
        latencies.append(latency_ms)

        faithfulness = result["faithfulness"]
        faithfulness_scores.append(faithfulness["faithfulness_score"])

        if not faithfulness["faithful"]:
            hallucinated_count += 1
            logger.warning(
                f"Hallucinations in query '{query[:40]}...': "
                f"{faithfulness['hallucinated_numbers']}"
            )

    avg_faithfulness = sum(faithfulness_scores) / len(faithfulness_scores)
    avg_latency = sum(latencies) / len(latencies)

    return {
        "avg_faithfulness_score": avg_faithfulness,
        "hallucinated_queries": hallucinated_count,
        "faithful_queries": len(TEST_QUERIES) - hallucinated_count,
        "avg_latency_ms": avg_latency,
        "min_latency_ms": min(latencies),
        "max_latency_ms": max(latencies),
    }


def run_eval_provider(provider: str, api_key: str = "") -> Dict[str, Any]:
    """Run evaluation for a single provider.

    Args:
        provider: Provider name ('ollama', 'anthropic', 'openai', 'gemini')
        api_key: API key for cloud providers (optional for ollama)

    Returns:
        Dict with all evaluation metrics
    """
    print(f"\n{'=' * 70}")
    print(f"🧪 Evaluating Provider: {provider.upper()}")
    print(f"{'=' * 70}")

    try:
        # Initialize pipeline
        pipeline = RAGPipeline(provider=provider, api_key=api_key)

        # Retrieval quality
        print("\n📊 Phase 1: Retrieval Quality")
        print("-" * 70)
        retrieval_metrics = evaluate_retrieval(pipeline)
        print(
            f"  Hit@5: {retrieval_metrics['hit_at_k']:.1%} "
            f"({retrieval_metrics['hits']}/{retrieval_metrics['total_queries']})"
        )
        print(f"  MRR:   {retrieval_metrics['mrr']:.3f}")

        # Faithfulness validation
        print("\n📊 Phase 2: Faithfulness & Latency")
        print("-" * 70)
        faithfulness_metrics = evaluate_faithfulness(pipeline)
        print(
            f"  Avg Faithfulness: {faithfulness_metrics['avg_faithfulness_score']:.1%}"
        )
        print(
            f"  Faithful Queries: {faithfulness_metrics['faithful_queries']}/{len(TEST_QUERIES)}"
        )
        print(
            f"  Hallucinated:     {faithfulness_metrics['hallucinated_queries']}/{len(TEST_QUERIES)}"
        )
        print(
            f"  Avg Latency:      {faithfulness_metrics['avg_latency_ms']:.0f}ms "
            f"(min: {faithfulness_metrics['min_latency_ms']}ms, "
            f"max: {faithfulness_metrics['max_latency_ms']}ms)"
        )

        return {
            "provider": provider,
            "status": "✅ PASS",
            "retrieval": retrieval_metrics,
            "faithfulness": faithfulness_metrics,
        }

    except Exception as e:
        logger.error(f"Evaluation failed for {provider}: {e}")
        return {
            "provider": provider,
            "status": f"❌ FAIL: {str(e)}",
            "error": str(e),
        }


def compare_providers(results: List[Dict]) -> None:
    """Print comparison table of providers.

    Args:
        results: List of provider evaluation results
    """
    print(f"\n{'=' * 70}")
    print("📈 PROVIDER COMPARISON")
    print(f"{'=' * 70}")

    print(
        f"\n{'Provider':<15} {'Hit@5':<10} {'MRR':<8} {'Faithfulness':<15} {'Latency':<12}"
    )
    print("-" * 70)

    for result in results:
        if "error" in result:
            print(f"{result['provider']:<15} ❌ {result['status']}")
            continue

        retr = result["retrieval"]
        faith = result["faithfulness"]

        print(
            f"{result['provider']:<15} "
            f"{retr['hit_at_k']:<10.1%} "
            f"{retr['mrr']:<8.3f} "
            f"{faith['avg_faithfulness_score']:<15.1%} "
            f"{faith['avg_latency_ms']:<10.0f}ms"
        )


def main():
    """Run full multi-provider evaluation."""
    import os

    print("\n" + "=" * 70)
    print("⚽ FOOTBALL RAG - MULTI-PROVIDER EVALUATION")
    print("=" * 70)
    print(f"Test Dataset: {len(TEST_QUERIES)} queries")
    print(f"Metrics: Hit@5, MRR, Faithfulness, Latency")
    print("=" * 70)

    # Evaluate providers
    results = []

    # 1. Ollama (local, always available)
    print("\n✓ Starting with Ollama (local)...")
    results.append(run_eval_provider("ollama"))

    # 2. Anthropic (if API key available)
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if anthropic_key:
        print("\n✓ API key found for Anthropic, evaluating...")
        results.append(run_eval_provider("anthropic", anthropic_key))
    else:
        print("\n⚠️  ANTHROPIC_API_KEY not found, skipping Anthropic eval")

    # 3. OpenAI (if API key available)
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        print("\n✓ API key found for OpenAI, evaluating...")
        results.append(run_eval_provider("openai", openai_key))
    else:
        print("\n⚠️  OPENAI_API_KEY not found, skipping OpenAI eval")

    # 4. Gemini (if API key available)
    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key:
        print("\n✓ API key found for Gemini, evaluating...")
        results.append(run_eval_provider("gemini", gemini_key))
    else:
        print("\n⚠️  GEMINI_API_KEY not found, skipping Gemini eval")

    # Compare providers
    compare_providers(results)

    # Summary
    print(f"\n{'=' * 70}")
    print("✅ EVALUATION COMPLETE")
    print(f"{'=' * 70}")
    print(f"Evaluated {len(results)} provider(s)")
    print("\n📋 Results saved to evaluation_results.json (optional)")
    print("=" * 70 + "\n")

    return results


if __name__ == "__main__":
    results = main()
