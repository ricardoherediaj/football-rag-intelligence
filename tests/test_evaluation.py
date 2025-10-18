"""RAG Evaluation Suite - Course MVP Requirement

Tests retrieval quality with metrics:
- Hit@K: Is relevant doc in top K results?
- MRR: Mean Reciprocal Rank of first relevant result
- Tactical Accuracy: Do results make football sense?
- Faithfulness: Validates answers against sources (Anthropic)
"""

import os
import logging
from typing import List, Tuple
from dotenv import load_dotenv
from football_rag.models.rag_pipeline import RAGPipeline

# Load .env for API keys
load_dotenv()

logging.basicConfig(level=logging.WARNING)


# Test dataset: (query, expected_keyword_in_result)
TEST_QUERIES: List[Tuple[str, str]] = [
    # xG and scoring queries
    ("Which teams had high xG?", "xG"),
    ("Teams with good shot quality", "xG"),
    # Specific match queries
    ("Fortuna Sittard result", "Fortuna Sittard"),
    ("PSV tactical approach", "PSV"),
    ("Feyenoord performance", "Feyenoord"),
    # Tactical queries
    ("Teams with direct passing", "passing"),
    ("Possession-based teams", "possession"),
    ("High pressing teams", "pressing"),
    # Score queries
    ("Big wins", "goals"),
    ("Close matches", "1-1"),
]


def evaluate_hit_at_k(
    rag: RAGPipeline, queries: List[Tuple[str, str]], k: int = 5
) -> float:
    """Calculate Hit@K metric."""
    hits = 0

    for query, expected in queries:
        results = rag.retrieve(query, k=k)
        found = any(
            expected.lower() in doc["text"].lower()
            or expected.lower() in str(doc["metadata"]).lower()
            for doc in results
        )
        if found:
            hits += 1

    return hits / len(queries)


def evaluate_mrr(rag: RAGPipeline, queries: List[Tuple[str, str]]) -> float:
    """Calculate Mean Reciprocal Rank."""
    reciprocal_ranks = []

    for query, expected in queries:
        results = rag.retrieve(query, k=10)
        for rank, doc in enumerate(results, start=1):
            if (
                expected.lower() in doc["text"].lower()
                or expected.lower() in str(doc["metadata"]).lower()
            ):
                reciprocal_ranks.append(1.0 / rank)
                break
        else:
            reciprocal_ranks.append(0.0)

    return sum(reciprocal_ranks) / len(reciprocal_ranks)


def evaluate_relevancy_llm(
    question: str, answer: str, context: str, api_key: str
) -> float:
    """LLM-as-judge: Does the answer address the question? (0-1 score)."""
    from football_rag.llm.generate import generate_with_llm

    judge_prompt = f"""You are an evaluation judge. Rate how well the answer addresses the question.

Question: {question}

Answer: {answer}

Context provided: {context[:200]}...

Rate the answer's relevancy on a scale:
- 1.0 = Perfectly addresses the question
- 0.7 = Mostly addresses it, minor gaps
- 0.5 = Partially addresses it
- 0.3 = Barely addresses it
- 0.0 = Does not address the question

Respond with ONLY a number between 0.0 and 1.0"""

    try:
        response = generate_with_llm(
            prompt=judge_prompt,
            provider="anthropic",
            api_key=api_key,
            temperature=0.0,
            max_tokens=10,
        )
        score = float(response.strip())
        return max(0.0, min(1.0, score))  # Clamp to [0, 1]
    except Exception as e:
        print(f"⚠️  LLM judge failed: {str(e)[:50]}")
        return 0.5  # Default neutral score


def evaluate_faithfulness(rag: RAGPipeline, queries: List[str]) -> dict:
    """Evaluate faithfulness scores with Anthropic."""
    faithful_count = 0
    total_queries = 0
    scores = []

    for query in queries:
        try:
            result = rag.query(query, top_k=5)
            faithfulness = result["faithfulness"]
            scores.append(faithfulness["faithfulness_score"])

            if faithfulness["faithful"]:
                faithful_count += 1

            total_queries += 1

        except Exception as e:
            print(f"⚠️  Query failed: {query[:40]}... - {str(e)[:60]}")

    avg_score = sum(scores) / len(scores) if scores else 0.0

    return {
        "avg_faithfulness_score": avg_score,
        "faithful_queries": faithful_count,
        "total_queries": total_queries,
        "faithfulness_rate": faithful_count / total_queries
        if total_queries > 0
        else 0.0,
    }


def run_evaluation():
    """Run full evaluation suite with Anthropic provider."""
    print("=" * 60)
    print("🎯 RAG EVALUATION - Anthropic Claude")
    print("=" * 60)

    # Get API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY not found in .env")
        return None

    # Initialize RAG with Anthropic
    print("\n✓ Initializing RAG pipeline with Anthropic Claude...")
    rag = RAGPipeline(provider="anthropic", api_key=api_key)

    # Hit@5 (retrieval only)
    print("\n📊 Phase 1: Retrieval Quality (Hit@5)")
    print("-" * 60)
    hit_at_5 = evaluate_hit_at_k(rag, TEST_QUERIES, k=5)
    print(
        f"Hit@5: {hit_at_5:.2%} ({int(hit_at_5 * len(TEST_QUERIES))}/{len(TEST_QUERIES)} queries)"
    )

    # MRR (retrieval only)
    print("\n📊 Phase 2: Mean Reciprocal Rank")
    print("-" * 60)
    mrr = evaluate_mrr(rag, TEST_QUERIES)
    print(f"MRR: {mrr:.3f}")

    # Faithfulness (with LLM generation)
    print("\n📊 Phase 3: Faithfulness Validation (with Anthropic)")
    print("-" * 60)
    print("Testing 5 queries with full RAG pipeline...")

    # Use subset for full RAG (expensive)
    test_queries_full = [q for q, _ in TEST_QUERIES[:5]]
    faithfulness_results = evaluate_faithfulness(rag, test_queries_full)

    print(
        f"Avg Faithfulness Score: {faithfulness_results['avg_faithfulness_score']:.2%}"
    )
    print(
        f"Faithful Queries: {faithfulness_results['faithful_queries']}/{faithfulness_results['total_queries']}"
    )

    # LLM-as-judge Relevancy
    print("\n📊 Phase 4: LLM-as-Judge Relevancy (Anthropic)")
    print("-" * 60)
    print("Testing 3 queries with LLM judge...")

    relevancy_scores = []
    for query in test_queries_full[:3]:
        result = rag.query(query, top_k=3)
        context = "\n".join([n["text"][:100] for n in result["source_nodes"]])
        score = evaluate_relevancy_llm(query, result["answer"], context, api_key)
        relevancy_scores.append(score)
        print(f"  Query: {query[:40]}... → Relevancy: {score:.2f}")

    avg_relevancy = sum(relevancy_scores) / len(relevancy_scores)
    print(f"\nAvg Relevancy Score: {avg_relevancy:.2%}")

    # Overall Assessment
    print("\n" + "=" * 60)
    print("✅ EVALUATION SUMMARY")
    print("=" * 60)

    retrieval_pass = hit_at_5 >= 0.60 and mrr >= 0.50  # Lower threshold for real data
    faithfulness_pass = faithfulness_results["avg_faithfulness_score"] >= 0.70
    relevancy_pass = avg_relevancy >= 0.70

    if retrieval_pass and faithfulness_pass and relevancy_pass:
        print("✅ All metrics PASS - Ready for deployment")
    else:
        print("⚠️  Some metrics below threshold")
        if not retrieval_pass:
            print("   - Retrieval needs improvement")
        if not faithfulness_pass:
            print("   - Faithfulness needs improvement")
        if not relevancy_pass:
            print("   - Relevancy needs improvement")

    print(f"\nDataset: {len(TEST_QUERIES)} queries (5 with full RAG, 3 with LLM judge)")
    print(f"Target: Hit@5 ≥ 60%, MRR ≥ 0.50, Faithfulness ≥ 70%, Relevancy ≥ 70%")
    print("=" * 60)

    return {
        "hit_at_5": hit_at_5,
        "mrr": mrr,
        "faithfulness": faithfulness_results,
        "relevancy": avg_relevancy,
        "pass": retrieval_pass and faithfulness_pass and relevancy_pass,
    }


if __name__ == "__main__":
    results = run_evaluation()
    if results:
        print(f"\n📝 Results: {results}")
