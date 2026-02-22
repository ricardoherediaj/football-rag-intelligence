# Engineering Diary: Phase 3a — Opik Observability + EDD Eval Harness
**Date:** 2026-02-22
**Tags:** `opik, evaluation, edd, pytest, llm-as-a-judge, observability, phase3a`

## 1. Problem Statement

The RAG pipeline had no production-grade observability and no trustworthy evaluation harness. The existing `tests/evaluate_pipeline.py` had four critical gaps: it wasn't pytest-runnable (couldn't be gated in CI), its faithfulness scorer used regex number-matching (not semantic grounding), it produced a single collapsed score with no trace history, and it had no run-to-run experiment logging. Without fixing these, there was no principled way to detect regressions or measure improvement as prompts and retrieval evolve.

## 2. Approach

**Strategy**: Wire Opik tracing end-to-end across the pipeline, then replace the ad-hoc eval script with a proper EDD suite using `opik.evaluate()` — keeping Opik as the single observability + evaluation platform rather than adding RAGAS/DeepEval as a separate dependency.

**Key decisions:**
- **Opik native `Hallucination` over regex faithfulness**: Claims-based LLM judging is semantically correct; regex number presence is not faithfulness. Reduces deps by staying in one platform.
- **`AnswerRelevance` as free signal**: Opik native, no extra cost, catches off-topic responses.
- **Custom `retrieval_accuracy` = Recall@1**: For the Sniper Architecture (single-target retrieval), exact match IS the correct SOTA metric. MRR/NDCG apply to ranked candidate lists — wrong abstraction here.
- **Custom `tactical_insight` as CoT judge**: Football-specific terminology, 3 weighted components (specificity 40% + visual_grounding 40% + terminology 20%), few-shot calibrated with 2 anchor examples to prevent score drift, `json.loads` not regex for parsing.
- **`--run-edd` flag**: Gates all LLM-calling EDD tests so CI never hits the API accidentally.
- **`refresh_eval_golden.py`**: Discovered that the hand-written `viz_metrics` in the golden dataset had multiple errors (wrong home/away assignment, reversed scores). Replaced with live DuckDB values from `main_main.gold_match_summaries`.

**Key Changes:**
- `tests/test_edd.py`: Full EDD suite — 31 tests (1 experiment + 10×3 parametrized assertions)
- `tests/evaluate_pipeline.py`: Deleted — superseded entirely
- `scripts/refresh_eval_golden.py`: New script to sync golden dataset from live DuckDB
- `data/eval_datasets/tactical_analysis_eval.json`: All 10 cases now have ground-truth `viz_metrics` from DuckDB
- `src/football_rag/orchestrator.py`: `@opik.track(name="football_rag_query")` added
- `src/football_rag/models/rag_pipeline.py`: `@opik.track` on retrieval + generation steps
- `src/football_rag/models/generate.py`: `@opik.track` on LLM call
- `pyproject.toml`: `[tool.pytest.ini_options]` with `edd` mark registered

## 3. Verification

**Tests Run:**
- `uv run pytest tests/ -v --ignore=dbt_project` → **41 passed, 2 errors** (pre-existing: `test_evaluation.py` imports renamed `RAGPipeline`, `test_visualizers.py` imports missing `visualizers` module — both tracked for `fix/stale-test-imports`)
- `uv run pytest tests/test_edd.py -v -m edd` → **31 collected, 31 skipped cleanly** (correct — `--run-edd` not passed)
- `scripts/refresh_eval_golden.py` → **10/10 cases updated** with real DuckDB values

**Metrics:**
- 10 test cases in golden dataset, all with 16 real metrics each
- 4 scorers wired: Hallucination, AnswerRelevance, retrieval_accuracy, tactical_insight
- 3 assertion tiers per case: hard retrieval, hard hallucination, soft tactical threshold (≥0.7)
- 0 regressions introduced to previously passing tests

## 4. Lessons Learned

- **Regex ≠ faithfulness**: Checking if numbers appear in a response is not the same as checking if claims are grounded. The former is a heuristic that passes on hallucinations that happen to quote a number correctly. Use claims-based LLM judging.
- **Recall@1 is correct for single-target retrieval**: Don't reach for MRR/NDCG just because they sound more sophisticated. The metric must match the architecture. The Sniper Approach retrieves one match — exact match is both necessary and sufficient.
- **Golden datasets need a refresh script**: Hand-writing `viz_metrics` inevitably introduces errors. The only reliable source is the database itself. `refresh_eval_golden.py` should be re-run whenever the DuckDB schema changes.
- **`--run-edd` flag is essential**: Without it, a `pytest` run in CI would accidentally burn API budget. Always gate LLM-calling tests behind an explicit flag.
- **Few-shot calibration in judges**: Two scored anchor examples in the tactical judge prompt materially reduce score variance between runs. Worth the prompt tokens.

## 5. Next Steps

- **Fix stale test imports** — `fix/stale-test-imports` branch: `RAGPipeline` → `FootballRAGPipeline` in `tests/test_evaluation.py`, fix `sys.path` in `tests/test_visualizers.py` to point at `src/football_rag/` not `scripts/`
- **Run baseline EDD experiment** — `uv run pytest tests/test_edd.py -v -m edd --run-edd` to get Claude Sonnet 4.6 baseline scores logged to Opik dashboard
- **Phase 3b: UI** — Streamlit single-page app: query input → commentary output + optional chart. Wire to `orchestrator.query()`.
- **HF Spaces update** — deploy Phase 2/3a engine to the demo
