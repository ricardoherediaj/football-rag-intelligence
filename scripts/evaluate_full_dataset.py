"""Evaluate RAG on 53-match dataset using LlamaIndex evaluation framework.

Uses LlamaIndex native components:
- RetrieverEvaluator: Hit@K, MRR for retrieval metrics
- FaithfulnessChecker: Generation validation (from rag_pipeline.py)
- Manual dataset with predefined queries + expected_ids
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict

from llama_index.core.evaluation import RetrieverEvaluator

from football_rag.models.rag_pipeline import RAGPipeline
from football_rag.storage.minio_client import MinIOClient
from football_rag.config.settings import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Golden Context Dataset: queries with expected node IDs (ground truth)
EVAL_DATASET = {
    "queries": {
        "q1": "PSV Eindhoven attacking performance and xG",
        "q2": "Feyenoord tactical style verticality",
        "q3": "Ajax matches results",
        "q4": "teams with highest expected goals",
        "q5": "NEC Nijmegen possession style",
        "q6": "FC Twente shot quality xG per shot",
        "q7": "matches with high verticality direct play",
        "q8": "Go Ahead Eagles defensive stats"
    },
    "relevant_docs": {
        "q1": ["match_summary_unified_match_005", "match_summary_unified_match_016", "match_summary_unified_match_020",
               "match_summary_unified_match_030", "match_summary_unified_match_037", "match_summary_unified_match_052"],
        "q2": ["match_summary_unified_match_003", "match_summary_unified_match_012", "match_summary_unified_match_033",
               "match_summary_unified_match_038", "match_summary_unified_match_044", "match_summary_unified_match_053"],
        "q3": ["match_summary_unified_match_007", "match_summary_unified_match_014", "match_summary_unified_match_026",
               "match_summary_unified_match_028", "match_summary_unified_match_052"],
        "q4": ["match_summary_unified_match_002", "match_summary_unified_match_024", "match_summary_unified_match_045",
               "match_summary_unified_match_052"],
        "q5": ["match_summary_unified_match_002", "match_summary_unified_match_013", "match_summary_unified_match_024",
               "match_summary_unified_match_037", "match_summary_unified_match_051"],
        "q6": ["match_summary_unified_match_006", "match_summary_unified_match_016", "match_summary_unified_match_023",
               "match_summary_unified_match_031", "match_summary_unified_match_039", "match_summary_unified_match_045"],
        "q7": ["match_summary_unified_match_045", "match_summary_unified_match_002", "match_summary_unified_match_024"],
        "q8": ["match_summary_unified_match_001", "match_summary_unified_match_014", "match_summary_unified_match_019",
               "match_summary_unified_match_029", "match_summary_unified_match_036", "match_summary_unified_match_050"]
    }
}


def evaluate_retrieval(rag: RAGPipeline) -> Dict:
    """Evaluate retrieval using LlamaIndex RetrieverEvaluator."""
    logger.info("Evaluating retrieval with LlamaIndex RetrieverEvaluator...")

    # Get retriever from RAG pipeline
    retriever = rag.index.as_retriever(similarity_top_k=10)

    # Create RetrieverEvaluator
    retriever_evaluator = RetrieverEvaluator.from_metric_names(
        ["hit_rate", "mrr"], retriever=retriever
    )

    # Evaluate each query
    eval_results = []
    for query_id, query in EVAL_DATASET['queries'].items():
        expected_ids = EVAL_DATASET['relevant_docs'][query_id]

        # Evaluate single query
        eval_result = retriever_evaluator.evaluate(query, expected_ids)
        eval_results.append(eval_result)

        logger.info(f"{query_id}: Hit={eval_result.metric_vals_dict['hit_rate']:.0f}, MRR={eval_result.metric_vals_dict['mrr']:.3f}")

    # Calculate aggregate metrics
    metric_dicts = [er.metric_vals_dict for er in eval_results]
    hit_rates = [m['hit_rate'] for m in metric_dicts]
    mrrs = [m['mrr'] for m in metric_dicts]

    return {
        "hit_rate": sum(hit_rates) / len(hit_rates),
        "mrr": sum(mrrs) / len(mrrs),
        "num_queries": len(eval_results),
        "detailed_results": [
            {
                "query_id": qid,
                "query": q,
                "expected_ids": EVAL_DATASET['relevant_docs'][qid],
                "hit_rate": metric_dicts[i]['hit_rate'],
                "mrr": metric_dicts[i]['mrr']
            }
            for i, (qid, q) in enumerate(EVAL_DATASET['queries'].items())
        ]
    }


def evaluate_generation(rag: RAGPipeline) -> Dict:
    """Evaluate generation with FaithfulnessChecker from rag_pipeline."""
    logger.info("Evaluating generation with FaithfulnessChecker...")

    results = []

    for query_id, query in EVAL_DATASET['queries'].items():
        # Generate answer using RAG
        response = rag.query(query, top_k=5)

        # Extract faithfulness metrics
        faithfulness = response['faithfulness']

        results.append({
            "query_id": query_id,
            "query": query,
            "answer": response['answer'],
            "faithfulness_score": faithfulness['faithfulness_score'],
            "faithful": faithfulness['faithful'],
            "hallucinated_numbers": faithfulness['hallucinated_numbers'],
            "valid_numbers": faithfulness['valid_numbers'],
            "retrieved_node_ids": [n['node_id'] for n in response['source_nodes']]
        })

        logger.info(f"{query_id}: Faithfulness={faithfulness['faithfulness_score']:.1%}, Faithful={faithfulness['faithful']}")

    # Calculate aggregate metrics
    faithfulness_scores = [r['faithfulness_score'] for r in results]

    return {
        "avg_faithfulness": sum(faithfulness_scores) / len(faithfulness_scores),
        "median_faithfulness": sorted(faithfulness_scores)[len(faithfulness_scores) // 2],
        "faithful_count": sum(1 for r in results if r['faithful']),
        "hallucination_count": sum(1 for r in results if not r['faithful']),
        "num_queries": len(results),
        "detailed_results": results
    }


def validate_source_data(generation_results: List[Dict], minio: MinIOClient) -> List[Dict]:
    """Compare generated numbers with original MinIO data."""
    logger.info("Validating against MinIO source data...")

    validated = []

    for item in generation_results:
        # Extract match_id from first retrieved node
        if not item['retrieved_node_ids']:
            validated.append({**item, "source_validation": None})
            continue

        node_id = item['retrieved_node_ids'][0]
        match_id = node_id.replace('match_summary_', '')

        try:
            # Download Fotmob data
            fotmob_path = f"fotmob/eredivisie/2025-2026/match_{match_id.replace('unified_match_', '')}.json"
            fotmob_obj = minio.download_file(fotmob_path)
            fotmob_data = json.loads(fotmob_obj.read())

            # Calculate ground truth xG
            home_xg = sum([
                s.get('expectedGoals', 0) for s in fotmob_data.get('shots', [])
                if s.get('teamId') == fotmob_data.get('home_team_id')
            ])
            away_xg = sum([
                s.get('expectedGoals', 0) for s in fotmob_data.get('shots', [])
                if s.get('teamId') == fotmob_data.get('away_team_id')
            ])

            validation = {
                "match_id": match_id,
                "source_xg_home": round(home_xg, 2),
                "source_xg_away": round(away_xg, 2),
                "generated_numbers": item['valid_numbers'],
                "numbers_match": all(
                    any(abs(gen - src) < 0.15 for src in [home_xg, away_xg])
                    for gen in item['valid_numbers']
                ) if item['valid_numbers'] else True
            }

            validated.append({**item, "source_validation": validation})

        except Exception as e:
            logger.warning(f"Could not validate {match_id}: {e}")
            validated.append({**item, "source_validation": {"error": str(e)}})

    return validated


def save_results(results: Dict, output_dir: Path):
    """Save evaluation results to JSON."""
    output_dir.mkdir(parents=True, exist_ok=True)

    filename = f"evaluation_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_path = output_dir / filename

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    logger.info(f"Results saved to {output_path}")
    return output_path


def main():
    """Run complete evaluation pipeline."""
    logger.info("="*80)
    logger.info("RAG EVALUATION - 53 MATCHES - LlamaIndex Framework")
    logger.info("="*80)

    # Initialize
    rag = RAGPipeline()
    minio = MinIOClient(
        endpoint=settings.database.minio_endpoint,
        access_key=settings.database.minio_access_key,
        secret_key=settings.database.minio_secret_key
    )

    logger.info(f"\nDataset: 53 documents")
    logger.info(f"LLM: {settings.llm_model}")
    logger.info(f"Queries: {len(EVAL_DATASET['queries'])}\n")

    # Step 1: Retrieval evaluation (LlamaIndex RetrieverEvaluator)
    logger.info("STEP 1: RETRIEVAL EVALUATION (LlamaIndex)")
    logger.info("-" * 80)
    retrieval_metrics = evaluate_retrieval(rag)

    # Step 2: Generation evaluation (FaithfulnessChecker)
    logger.info("\nSTEP 2: GENERATION EVALUATION (FaithfulnessChecker)")
    logger.info("-" * 80)
    generation_metrics = evaluate_generation(rag)

    # Step 3: Validate with source data
    logger.info("\nSTEP 3: SOURCE DATA VALIDATION (MinIO)")
    logger.info("-" * 80)
    validated_results = validate_source_data(
        generation_metrics['detailed_results'],
        minio
    )

    # Build final output
    output = {
        "metadata": {
            "evaluation_date": datetime.now().isoformat(),
            "dataset_size": 53,
            "num_queries": len(EVAL_DATASET['queries']),
            "llm_model": settings.llm_model,
            "embedding_model": "all-mpnet-base-v2",
            "framework": "LlamaIndex",
            "metrics_used": ["hit_rate", "mrr", "faithfulness"]
        },
        "retrieval_metrics": {
            "hit_rate": retrieval_metrics['hit_rate'],
            "mrr": retrieval_metrics['mrr']
        },
        "generation_metrics": {
            "avg_faithfulness": generation_metrics['avg_faithfulness'],
            "median_faithfulness": generation_metrics['median_faithfulness'],
            "faithful_rate": generation_metrics['faithful_count'] / generation_metrics['num_queries'],
            "hallucination_rate": generation_metrics['hallucination_count'] / generation_metrics['num_queries']
        },
        "detailed_results": {
            "retrieval": retrieval_metrics['detailed_results'],
            "generation": validated_results
        }
    }

    # Save to JSON
    output_path = save_results(output, Path("data/processed"))

    # Print summary
    logger.info("\n" + "="*80)
    logger.info("EVALUATION SUMMARY")
    logger.info("="*80)

    print(f"\n📊 RETRIEVAL METRICS (LlamaIndex RetrieverEvaluator)")
    print(f"  Hit Rate:  {output['retrieval_metrics']['hit_rate']:.1%}")
    print(f"  MRR:       {output['retrieval_metrics']['mrr']:.3f}")

    print(f"\n🤖 GENERATION METRICS (FaithfulnessChecker)")
    print(f"  Avg Faithfulness:   {output['generation_metrics']['avg_faithfulness']:.1%}")
    print(f"  Median Faithfulness: {output['generation_metrics']['median_faithfulness']:.1%}")
    print(f"  Faithful Rate:       {output['generation_metrics']['faithful_rate']:.1%}")
    print(f"  Hallucination Rate:  {output['generation_metrics']['hallucination_rate']:.1%}")

    print(f"\n💾 Results saved to: {output_path}")
    print(f"✅ Evaluation complete\n")

    return output


if __name__ == "__main__":
    results = main()
