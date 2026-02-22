"""EDD (Evaluation-Driven Development) test suite for the Football RAG pipeline.

Replaces tests/evaluate_pipeline.py with:
- pytest-runnable parametrized tests
- opik.evaluate() for experiment logging to Opik dashboard
- Opik native AnswerRelevance metric
- Custom CoT tactical judge (component scoring, few-shot, json.loads)
- Custom retrieval accuracy scorer (Recall@1 — exact match)

Run:
    uv run pytest tests/test_edd.py -v -m edd
    uv run pytest tests/test_edd.py -v -m edd --run-edd   # actually calls LLM
"""

import json
import logging
import os
from pathlib import Path
from typing import Any

import pytest
from dotenv import load_dotenv

load_dotenv()

from opik import Opik
from opik.evaluation import evaluate
from opik.evaluation.metrics import AnswerRelevance
from opik.evaluation.metrics.score_result import ScoreResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths & constants
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).parent.parent
EVAL_PATH = PROJECT_ROOT / "data" / "eval_datasets" / "tactical_analysis_eval.json"
TACTICAL_THRESHOLD = 0.7      # 7/10 production threshold from EDD article
OPIK_PROJECT = os.getenv("OPIK_PROJECT_NAME", "football-rag-intelligence")

# Golden dataset version — bump when eval queries change to avoid stale item accumulation
GOLDEN_DATASET_NAME = "football-rag-golden-v3"

# ---------------------------------------------------------------------------
# Provider configuration — swap via env vars, no code changes needed
#
# PIPELINE_PROVIDER: controls _rag_task (the system under test)
#   "anthropic" → Claude via Anthropic SDK
#   "modal"     → Modal-hosted inference (Phase 3c)
#
# JUDGE_PROVIDER: controls tactical_insight custom scorer
#   Same values as PIPELINE_PROVIDER
#
# JUDGE_MODEL_OPIK: controls Opik native metrics (AnswerRelevance)
#   LiteLLM provider/model format: "anthropic/claude-haiku-4-5-20251001"
#   Modal example (future): "modal/llama-3-70b"
# ---------------------------------------------------------------------------

PIPELINE_PROVIDER = os.getenv("PIPELINE_PROVIDER", "anthropic")
JUDGE_PROVIDER = os.getenv("JUDGE_PROVIDER", "anthropic")
JUDGE_MODEL_OPIK = os.getenv("JUDGE_MODEL_OPIK", "anthropic/claude-haiku-4-5-20251001")

EXPERIMENT_NAME = f"{PIPELINE_PROVIDER}-baseline-v1"

# ---------------------------------------------------------------------------
# Few-shot calibration examples for the tactical judge
# Two scored examples prevent score drift between runs (from LLM-as-a-Judge ebook)
# ---------------------------------------------------------------------------

_FEW_SHOT = """
CALIBRATION EXAMPLE 1 (score: high — 0.85)
Query: "Analyze PEC Zwolle's dominant performance"
Report: "PEC Zwolle produced a stunning 8-2 demolition of Heracles. Their 24 shots overwhelmed \
a Heracles side that managed only 7 attempts. The xG overperformance (1.14 xG → 8 goals) reflects \
clinical finishing rather than luck. Heracles' PPDA of 5.8 showed passive defending."
Why high: cites exact metrics, explains xG paradox, uses correct tactical terminology.

CALIBRATION EXAMPLE 2 (score: low — 0.25)
Query: "Analyze the shot efficiency paradox in Heracles vs AZ"
Report: "It was an exciting match. Both teams fought hard. Heracles won 2-1 despite having fewer \
chances. The game was decided by individual brilliance."
Why low: no specific metrics cited, no xG analysis, no tactical explanation, generic language.
"""

# ---------------------------------------------------------------------------
# Custom scorers
# ---------------------------------------------------------------------------


def retrieval_accuracy(dataset_item: dict, task_outputs: dict) -> ScoreResult:
    """Recall@1 — exact match between expected and retrieved match_id."""
    expected = str(dataset_item["match_id"])
    retrieved = str(task_outputs.get("match_id", ""))
    hit = retrieved == expected
    return ScoreResult(
        name="retrieval_accuracy",
        value=1.0 if hit else 0.0,
        reason=f"Expected {expected}, got '{retrieved}'",
    )


def tactical_insight(dataset_item: dict, task_outputs: dict) -> ScoreResult:
    """CoT LLM judge for domain-specific tactical quality.

    Scores 3 components (weights from EDD article):
    - specificity      (0.40): concrete metrics, exact numbers, player IDs
    - visual_grounding (0.40): references actual viz data (shots, xG, PPDA, etc.)
    - terminology      (0.20): correct football language (PPDA, high line, xG, pressing)

    Uses json.loads (not regex) to parse structured output.
    Few-shot calibrated to prevent score drift.
    Logs response length for verbosity bias detection.
    """
    from football_rag.models.generate import generate_with_llm

    commentary = task_outputs.get("commentary", "")
    viz_metrics = dataset_item.get("viz_metrics", {})
    expected_insights = dataset_item.get("expected_insights", [])
    response_length = len(commentary.split())

    prompt = f"""You are a senior football analyst auditing an automated match report.
Your task: score the report on 3 components. Think step by step before scoring.

{_FEW_SHOT}

--- GROUND TRUTH METRICS ---
{json.dumps(viz_metrics, indent=2)}

--- EXPECTED INSIGHTS ---
{json.dumps(expected_insights, indent=2)}

--- REPORT TO EVALUATE ---
{commentary}

--- SCORING INSTRUCTIONS ---
Think through each component carefully, then output JSON.

Components:
1. specificity (0.0-1.0): Does the report cite concrete metrics with exact numbers from the \
ground truth? Penalise vague claims like "they dominated" without evidence.
2. visual_grounding (0.0-1.0): Does it correctly interpret the actual data (shots, xG, PPDA, \
defensive line, progressive passes)? Penalise misquoted or missing key stats.
3. terminology (0.0-1.0): Does it use correct football tactical language (PPDA, xG, high press, \
defensive line, progressive passes, verticality)? Penalise generic sports commentary.

Output ONLY valid JSON, no markdown:
{{
  "reasoning": "your step-by-step analysis",
  "specificity": <float 0.0-1.0>,
  "visual_grounding": <float 0.0-1.0>,
  "terminology": <float 0.0-1.0>
}}"""

    try:
        raw = generate_with_llm(prompt, provider=JUDGE_PROVIDER, temperature=0, max_tokens=2048)
        # Strip markdown code fences that some models wrap around JSON output
        clean = raw.strip()
        if clean.startswith("```"):
            clean = clean.split("```", 2)[1]
            if clean.startswith("json"):
                clean = clean[4:]
            clean = clean.rsplit("```", 1)[0].strip()
        parsed = json.loads(clean)
        score = (
            parsed["specificity"] * 0.40
            + parsed["visual_grounding"] * 0.40
            + parsed["terminology"] * 0.20
        )
        reason = (
            f"specificity={parsed['specificity']:.2f}, "
            f"visual_grounding={parsed['visual_grounding']:.2f}, "
            f"terminology={parsed['terminology']:.2f} | "
            f"response_words={response_length} | "
            f"{parsed.get('reasoning', '')[:200]}"
        )
        return ScoreResult(name="tactical_insight", value=round(score, 3), reason=reason)
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning("tactical_insight judge parse error: %s | clean=%s", e, clean[:200])
        return ScoreResult(name="tactical_insight", value=0.5, reason=f"parse_error: {e}")
    except Exception as e:
        logger.error("tactical_insight judge failed: %s", e)
        return ScoreResult(name="tactical_insight", value=0.5, reason=f"error: {e}")


# ---------------------------------------------------------------------------
# Opik dataset + evaluation task
# ---------------------------------------------------------------------------


def _load_opik_dataset() -> Any:
    """Push golden dataset to Opik and return dataset object.

    GOLDEN_DATASET_NAME is versioned — bump the constant when eval queries change.
    A new version name means a clean dataset; no delete/recreate needed.
    insert() is idempotent within the same version (Opik deduplicates by content).
    """
    client = Opik()
    dataset = client.get_or_create_dataset(
        name=GOLDEN_DATASET_NAME,
        description="10 tactical analysis test cases with real DuckDB viz_metrics",
    )
    raw = json.loads(EVAL_PATH.read_text())
    items = [
        {
            "test_id": tc["test_id"],
            "query": tc["query"],
            "match_id": tc["match_id"],
            "viz_metrics": tc["viz_metrics"],
            "expected_insights": tc["expected_insights"],
        }
        for tc in raw["test_cases"]
    ]
    dataset.insert(items)
    logger.info("Loaded %d items into Opik dataset '%s'", len(items), GOLDEN_DATASET_NAME)
    return dataset


def _rag_task(dataset_item: dict) -> dict:
    """Run the full RAG pipeline for one dataset item."""
    from football_rag.orchestrator import query as rag_query

    result = rag_query(dataset_item["query"], provider=PIPELINE_PROVIDER)
    return {
        "match_id": result.get("match_id", ""),
        "commentary": result.get("commentary", ""),
        "input": dataset_item["query"],
        "output": result.get("commentary", ""),
        "context": [json.dumps(dataset_item["viz_metrics"])],
    }


# ---------------------------------------------------------------------------
# pytest fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def eval_cases() -> list[dict]:
    raw = json.loads(EVAL_PATH.read_text())
    return raw["test_cases"]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.edd
class TestEDD:
    """EDD suite — runs opik.evaluate() and asserts on per-case scores.

    Split into two layers:
    1. test_opik_experiment  — runs the full 10-case evaluation via opik.evaluate(),
                               uploads results to dashboard, stores scores on self.
    2. test_retrieval_*      — fast parametrized assertions against stored scores.
    """

    _scores: dict[str, dict] = {}   # test_id → {metric: value}

    @pytest.fixture(autouse=True)
    def require_edd_flag(self, request):
        """Skip all EDD tests unless --run-edd is passed."""
        if not request.config.getoption("--run-edd"):
            pytest.skip("Pass --run-edd to run live LLM evaluation tests")

    def test_opik_experiment(self):
        """Run full 10-case evaluation, upload to Opik, store scores for assertions."""
        dataset = _load_opik_dataset()

        result = evaluate(
            dataset=dataset,
            task=_rag_task,
            scoring_metrics=[
                AnswerRelevance(model=JUDGE_MODEL_OPIK),
            ],
            scoring_functions=[
                retrieval_accuracy,
                tactical_insight,
            ],
            experiment_name=EXPERIMENT_NAME,
            project_name=OPIK_PROJECT,
            experiment_config={
                "pipeline_provider": PIPELINE_PROVIDER,
                "judge_provider": JUDGE_PROVIDER,
                "judge_model_opik": JUDGE_MODEL_OPIK,
            },
            task_threads=1,   # sequential — avoids rate limits
            verbose=1,
        )

        # Store scores indexed by test_id for downstream assertions
        for test_result in result.test_results:
            item = test_result.test_case.dataset_item_content
            tid = item.get("test_id", "unknown")
            scores = {s.name: s.value for s in (test_result.score_results or [])}
            TestEDD._scores[tid] = scores

        assert len(TestEDD._scores) == 10, "Expected 10 evaluated cases"
        logger.info("Opik experiment '%s' complete — %d cases", EXPERIMENT_NAME, len(TestEDD._scores))

    @pytest.mark.parametrize("test_id", [
        "match_01_blowout", "match_02_high_scoring", "match_03_stalemate",
        "match_04_narrow_win", "match_05_upset", "match_06_efficiency_study",
        "match_07_defensive_struggle", "match_08_counter_attack",
        "match_09_defensive_dominance", "match_10_tight_margins",
    ])
    def test_retrieval_exact_match(self, test_id: str):
        """Hard assertion: retrieval must be exact (Recall@1 = 1.0)."""
        scores = TestEDD._scores.get(test_id, {})
        value = scores.get("retrieval_accuracy", -1.0)
        assert value == 1.0, (
            f"{test_id}: retrieval_accuracy={value:.2f} — wrong match retrieved. "
            "Check DuckDB VSS index and query embedding."
        )

    @pytest.mark.parametrize("test_id", [
        "match_01_blowout", "match_02_high_scoring", "match_03_stalemate",
        "match_04_narrow_win", "match_05_upset", "match_06_efficiency_study",
        "match_07_defensive_struggle", "match_08_counter_attack",
        "match_09_defensive_dominance", "match_10_tight_margins",
    ])
    def test_tactical_insight_threshold(self, test_id: str):
        """Soft assertion: tactical insight must meet production threshold (≥0.7)."""
        scores = TestEDD._scores.get(test_id, {})
        value = scores.get("tactical_insight", -1.0)
        assert value >= TACTICAL_THRESHOLD, (
            f"{test_id}: tactical_insight={value:.2f} < threshold={TACTICAL_THRESHOLD}. "
            "Response lacks specificity, visual grounding, or correct terminology."
        )
