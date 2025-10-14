"""LlamaIndex-native evaluation for RAG retrieval quality.

Uses RetrieverEvaluator with manual dataset to establish professional
evaluation foundations alongside custom script baseline.
"""

import asyncio
import logging
from typing import List, Tuple

from llama_index.core.evaluation import RetrieverEvaluator
from llama_index.core.schema import QueryBundle
from llama_index.core.evaluation import EmbeddingQAFinetuneDataset

from football_rag.models.rag_pipeline import RAGPipeline
from football_rag.config.settings import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Same 10 queries from custom script
TEST_QUERIES: List[Tuple[str, str]] = [
    ("Which teams had high xG?", "xG"),
    ("Fortuna Sittard result", "Fortuna Sittard"),
    ("PSV tactical approach", "PSV Eindhoven"),
    ("Teams with direct passing", "verticality"),
    ("Ajax performance", "Ajax"),
    ("High possession teams", "possession"),
    ("Shot quality analysis", "xG/Shot"),
    ("Go Ahead Eagles match", "Go Ahead Eagles"),
    ("Defensive performances", "xG"),
    ("Tactical patterns", "Tactical Summary")
]


def create_manual_dataset(queries: List[Tuple[str, str]]) -> EmbeddingQAFinetuneDataset:
    """Create manual dataset by mapping queries to relevant doc IDs.

    Args:
        queries: List of (query, expected_term) tuples

    Returns:
        EmbeddingQAFinetuneDataset with query-docid mappings
    """
    import chromadb

    dataset_dict = {"queries": {}, "relevant_docs": {}, "corpus": {}}

    # Access ChromaDB directly to get all documents
    chroma_client = chromadb.HttpClient(
        host=settings.database.chroma_host,
        port=settings.database.chroma_port
    )
    collection = chroma_client.get_collection("football_matches_eredivisie_2025")

    # Get all documents from collection
    all_data = collection.get(include=["documents", "metadatas"])

    # Build corpus
    for doc_id, text in zip(all_data['ids'], all_data['documents']):
        dataset_dict["corpus"][doc_id] = text

    logger.info(f"Built corpus with {len(dataset_dict['corpus'])} documents")

    # Map each query to relevant doc IDs (skip queries with no relevant docs)
    for i, (query, expected_term) in enumerate(queries):
        query_id = f"query_{i}"

        # Find relevant docs by matching expected term
        relevant_ids = []
        for doc_id, text in dataset_dict["corpus"].items():
            if expected_term.lower() in text.lower():
                relevant_ids.append(doc_id)

        # Only include query if it has relevant docs
        if relevant_ids:
            dataset_dict["queries"][query_id] = query
            dataset_dict["relevant_docs"][query_id] = relevant_ids
            logger.info(f"Query '{query[:30]}...' → {len(relevant_ids)} relevant docs")
        else:
            logger.warning(f"Query '{query[:30]}...' → 0 relevant docs (skipping)")

    return EmbeddingQAFinetuneDataset(
        queries=dataset_dict["queries"],
        corpus=dataset_dict["corpus"],
        relevant_docs=dataset_dict["relevant_docs"]
    )


async def run_llamaindex_evaluation(rag: RAGPipeline, dataset: EmbeddingQAFinetuneDataset) -> dict:
    """Run async batch evaluation with RetrieverEvaluator.

    Args:
        rag: RAGPipeline instance
        dataset: Manual dataset with query-docid mappings

    Returns:
        Dict with metrics (hit_rate, mrr)
    """
    # Create evaluator with Hit Rate and MRR metrics
    evaluator = RetrieverEvaluator.from_metric_names(
        ["hit_rate", "mrr"],
        retriever=rag.retriever
    )

    # Batch evaluate all queries
    eval_results = await evaluator.aevaluate_dataset(dataset, workers=4)

    # Aggregate metrics
    hit_rate = sum(r.metric_vals_dict["hit_rate"] for r in eval_results) / len(eval_results)
    mrr = sum(r.metric_vals_dict["mrr"] for r in eval_results) / len(eval_results)

    logger.info(f"LlamaIndex Evaluation Results:")
    logger.info(f"  Hit Rate@5: {hit_rate:.1%}")
    logger.info(f"  MRR: {mrr:.3f}")

    return {
        "hit_rate": hit_rate,
        "mrr": mrr,
        "eval_results": eval_results
    }


def compare_with_baseline(llamaindex_metrics: dict, num_queries_evaluated: int):
    """Compare LlamaIndex results with custom script baseline.

    Args:
        llamaindex_metrics: Results from LlamaIndex evaluation
        num_queries_evaluated: Number of queries actually evaluated (after filtering)
    """
    logger.info("\n" + "="*60)
    logger.info("COMPARISON: LlamaIndex vs Custom Baseline")
    logger.info("="*60)

    logger.info(f"Dataset:")
    logger.info(f"  Total queries:       10")
    logger.info(f"  Evaluated queries:   {num_queries_evaluated} (queries with relevant docs)")
    logger.info(f"  Filtered out:        {10 - num_queries_evaluated} (no ground truth)")

    logger.info(f"\nHit Rate@5:")
    logger.info(f"  Custom (10q):     100.0%")
    logger.info(f"  LlamaIndex ({num_queries_evaluated}q): {llamaindex_metrics['hit_rate']:.1%}")

    logger.info(f"\nMRR:")
    logger.info(f"  Custom (10q):     0.875")
    logger.info(f"  LlamaIndex ({num_queries_evaluated}q): {llamaindex_metrics['mrr']:.3f}")

    # Validation
    if llamaindex_metrics['hit_rate'] == 1.0 and llamaindex_metrics['mrr'] >= 0.875:
        logger.info("\n✅ VALIDATION PASSED: LlamaIndex evaluation shows excellent retrieval quality")
        logger.info("   Note: Higher MRR due to filtering queries without ground truth")
    else:
        logger.warning("\n⚠️  VALIDATION WARNING: Metrics below expected threshold")

    logger.info("="*60 + "\n")


async def main():
    """Main evaluation workflow."""
    logger.info("Starting LlamaIndex-native evaluation...")

    # Initialize RAG pipeline
    rag = RAGPipeline()

    # Create manual dataset
    logger.info("Creating manual dataset from 10 test queries...")
    dataset = create_manual_dataset(TEST_QUERIES)

    # Run evaluation
    logger.info("Running async batch evaluation...")
    metrics = await run_llamaindex_evaluation(rag, dataset)

    # Compare with baseline
    num_evaluated = len(dataset.queries)
    compare_with_baseline(metrics, num_evaluated)

    return metrics


if __name__ == "__main__":
    results = asyncio.run(main())
    print(f"\n✅ Evaluation complete: Hit Rate={results['hit_rate']:.1%}, MRR={results['mrr']:.3f}")
