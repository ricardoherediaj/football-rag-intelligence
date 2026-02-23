# Session Scratchpad

**Purpose**: Current session state only. Historical sessions → `docs/engineering_diary/`.
**Update constantly. Trim aggressively.**

---

## 📍 Current State (2026-02-23)

**Branch**: `feat/phase3b-streamlit-ui` — PR #8 open, ready to merge
**Status**: Phase 3b COMPLETE ✅ — Streamlit UI working locally, all 7 viz types verified

### Pipeline Status
| Layer | Status | Count |
|---|---|---|
| Bronze | ✅ | 412 matches in MinIO + MotherDuck |
| Match Mapping | ✅ | 205/205 (100% coverage) |
| dbt Silver | ✅ | 279,104 events, 378 team performances |
| dbt Gold | ✅ | 205 match summaries in MotherDuck |
| GitHub Actions | ✅ | `dbt run --target prod` → PASS=3 in CI |
| Embeddings | ✅ | 205 match embeddings, 768-dim HNSW index |
| RAG Engine | ✅ | DuckDB VSS, orchestrator wired, viz dispatch working |
| Observability | ✅ | `@opik.track` on orchestrator + rag_pipeline + generate |
| EDD Eval Harness | ✅ | 21 pytest tests, 3 scorers, 10-case golden dataset |
| **EDD Baseline** | ✅ | **retrieval_accuracy=1.0000, tactical_insight=0.9142, answer_relevance=0.8380** |
| **Streamlit UI** | ✅ | **All 7 viz types + text commentary working locally** |

---

## 🎯 Next Session — Start Here

**Immediate**: Merge PR #8 `feat/phase3b-streamlit-ui` → `main`

**Next tasks (in order)**:
1. **Prompt improvement** — Make LLM more tactical analyst, less metric reciter. Edit `prompts/prompt_versions.yaml` v3.5_balanced → v4.0_tactical. Focus: interpret numbers, not report them.
2. **HF Spaces deploy** — Upload `lakehouse.duckdb` to HF Dataset repo (supports >100MB via git-lfs), configure app to download at startup, add `requirements.txt` + `app.py` entrypoint for HF.
3. **Update cron script** — After scrape+embed cycle: `huggingface-cli upload` lakehouse.duckdb → HF Dataset, then restart HF Space.

### 🔑 DEPLOY ARCHITECTURE (confirmed)
- **MotherDuck**: silver_events, silver_fotmob_shots, match_mapping, gold_match_summaries ✅ (already stateless)
- **lakehouse.duckdb**: 536MB, contains HNSW embeddings index — must go to HF Dataset repo (git-lfs)
- **xT_grid.csv**: 1KB static file, stays in repo ✅
- **Secrets needed in HF Spaces**: MOTHERDUCK_TOKEN, ANTHROPIC_API_KEY, HF_TOKEN (for dataset download)
- **Run command for HF**: `streamlit run src/football_rag/app/main.py --server.port 7860`

### Viz column mapping (implemented, do not revert)
`silver_fotmob_shots` → `visualizers.py` requires these renames:
- `event_type` → `eventType`
- `player_name` → `playerName`
- `shot_type` → `shotType`
- `is_on_target` → `isOnTarget`

`silver_events` → `visualizers.py` requires:
- `event_row_id AS id` (for groupby count in calculate_player_defensive_positions)

### EDD Maintenance
When eval queries change:
```python
GOLDEN_DATASET_NAME = "football-rag-golden-v3"  # Bump to v4, v5, etc.
```

---

## 🗺️ Schema Reference (DuckDB — `main_main.*`)

**gold_match_summaries**:
- Scores: `home_goals`, `away_goals` (NOT `home_score`/`away_score`)
- xG: `home_total_xg`, `away_total_xg`
- Position: `home_median_position`, `away_median_position`
- All aliased in SQL to match `TacticalMetrics` field names

**gold_match_embeddings**: `match_id`, `embedding FLOAT[768]` — HNSW indexed

---

## 📚 Historical Reference

Full session logs in engineering diary:
- [2026-02-14](docs/engineering_diary/2026-02-14-phase1-diagnosis.md) — Two parallel pipelines discovered, chose Hybrid architecture
- [2026-02-15](docs/engineering_diary/2026-02-15-phase1-silver-layer-complete.md) — dbt wired, 24 metrics, xG fix via match_mapping.json
- [2026-02-16](docs/engineering_diary/2026-02-16-phase1-complete.md) — Phase 1 declared complete (188 matches, 15/15 tests, vector search working)
- [2026-02-19](docs/engineering_diary/2026-02-19-phase1-motherduck-complete.md) — Phase 1 complete: MotherDuck migration, CI green, 205 embeddings
- [2026-02-21](docs/engineering_diary/2026-02-21-phase2-rag-engine.md) — Phase 2 complete: ChromaDB → DuckDB VSS, orchestrator, end-to-end verified
- [2026-02-22](docs/engineering_diary/2026-02-22-phase3a-opik-edd.md) — Phase 3a complete: Opik tracing, EDD eval harness, golden dataset refreshed from DuckDB

**Completed milestones**:
- Phase 1: Bronze → Match Mapping → Silver → Gold → Embeddings → Vector Search → MotherDuck + CI
- Phase 2: RAG engine rewired to DuckDB VSS, orchestrator built, viz dispatch wired, 25/25 tests passing
- Phase 3a: Opik `@opik.track` end-to-end, EDD 3 scorers + 21 tests, golden dataset ground-truthed from DuckDB
- Phase 3b: Streamlit UI live locally, all 7 viz types working, viz fully migrated to MotherDuck

**Last Updated**: 2026-02-23
