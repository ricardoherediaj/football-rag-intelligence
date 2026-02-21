# Engineering Diary: Phase 2 — RAG Engine Rewire
**Date:** 2026-02-21
**Tags:** `rag`, `duckdb-vss`, `orchestrator`, `chromadb-migration`, `phase2`

## 1. Problem Statement

The RAG engine (`rag_pipeline.py`) was wired to ChromaDB (`data/chroma`) — a separate index built during the MVP that was now disconnected from the live Gold layer. Phase 1 had produced `gold_match_embeddings` (205 × 768-dim HNSW in DuckDB) and `gold_match_summaries` (205 matches with full tactical metrics), but the query engine was still reading from a stale, different index format (2-chunk ChromaDB doc per match). The pipeline was split in two: world-class data foundation, MVP-era retrieval.

Additionally, there was no single entry point — the router, pipeline, and viz tools existed as disconnected modules with no orchestration layer.

## 2. Approach

Complete replacement of the ChromaDB retrieval layer with direct DuckDB queries. No new infrastructure — the Gold layer already had everything needed.

**Key decisions:**
- `array_distance(embedding, ?::FLOAT[768])` for L2 similarity on the HNSW index — equivalent to cosine on unit-normalized vectors from `all-mpnet-base-v2`
- AND logic when 2 teams are mentioned in the query (OR was causing wrong match returns)
- Thin orchestrator pattern: `query()` → intent classification → RAG text path or viz dispatch
- `prompts/prompt_versions.yaml` created to give `prompts_loader.py` the machine-readable format it required (previously only `.md` human-readable docs existed)

**Key Changes:**
- `src/football_rag/models/rag_pipeline.py`: Complete rewrite — ChromaDB → DuckDB VSS
- `src/football_rag/orchestrator.py`: New thin entry point wiring router + pipeline + viz tools
- `src/football_rag/config/settings.py`: Removed `DatabaseSettings`, added `duckdb_path`
- `src/football_rag/models/generate.py`: Updated deprecated model to `claude-haiku-4-5-20251001`
- `prompts/prompt_versions.yaml`: New machine-readable prompt file
- `scripts/test_rag.py`: CLI harness for end-to-end verification

## 3. Verification

**Tests Run:**
- `uv run python scripts/test_rag.py "Analyze the Heracles vs PEC Zwolle match"` → correct match (2-8), Claude commentary with all 4 sections (Match Overview, xG & Shot Efficiency, Pressing & Progression, Key Tactical Insight)
- `uv run python scripts/test_rag.py "Show shot map for Heracles vs PEC Zwolle"` → `data/outputs/shot_map_1904034.png` saved
- `uv run pytest` → 25/25 passing

**Column mapping discovered (institutional knowledge):**

| TacticalMetrics field | gold_match_summaries column |
|---|---|
| `home_xg` | `home_total_xg` |
| `away_xg` | `away_total_xg` |
| `home_position` | `home_median_position` |
| `away_position` | `away_median_position` |
| `home_score` | `home_goals` |
| `away_score` | `away_goals` |

**Schema:** dbt tables live under `main_main.` prefix when both target schema and DB schema are named `main`.

## 4. Lessons Learned

- Test with real team+match queries immediately — the OR vs AND team filter bug only surfaces when two teams produce the wrong match, not in unit tests
- `array_distance` on unit-normalized vectors = cosine similarity: no need for a different distance function
- ChromaDB's metadata-per-chunk pattern doesn't scale — embedding + metrics in one DuckDB table with a JOIN is simpler and more queryable
- Always check the actual column names in the DB before writing the TacticalMetrics model mapping

## 5. Next Steps

- Open and merge PR `feat/phase2-rag-engine` → `main`
- Phase 3: Streamlit/Reflex UI + Opik observability + RAGAS/DeepEval evaluation
- Update HF Spaces demo with Phase 2 engine
- Router edge case: question words (`what`, `how`) currently short-circuit viz queries — fix in Phase 3
