# Session Scratchpad

**Purpose**: Current session state only. Historical sessions → `docs/engineering_diary/`.
**Update constantly. Trim aggressively.**

---

## 📍 Current State (2026-02-23)

**Branch**: `feat/hf-spaces-deploy` (from `main`, PR #8 merged)
**Status**: Phase 3b COMPLETE ✅ — Starting HF Spaces deploy

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
| **HF Spaces Deploy** | 🚧 | In progress — `feat/hf-spaces-deploy` branch |

---

## 🎯 Current Session — Deploy Plan

### v1.0 "Properly Done" Checklist
```
[ ] Public URL live (HF Spaces)
[ ] Cold start < 90s (lakehouse.duckdb downloads on wake)
[ ] Secrets configured (MOTHERDUCK_TOKEN, ANTHROPIC_API_KEY, HF_TOKEN)
[ ] README has live URL + screenshot
[ ] EDD runs in CI (not just locally)
```

### Tasks (in order)
1. **HF Spaces deploy** (current)
   - Upload `lakehouse.duckdb` to HF Dataset repo via git-lfs
   - Add `requirements.txt` (pip format for HF)
   - Add `app.py` entrypoint (HF Spaces uses `app.py` by default)
   - Add startup download of `lakehouse.duckdb` from HF Dataset
   - Set secrets: `MOTHERDUCK_TOKEN`, `ANTHROPIC_API_KEY`, `HF_TOKEN`
   - Verify public URL + cold start time
2. **Prompt v4.0_tactical** — after live URL confirmed, tune LLM to interpret metrics tactically, not recite them. Edit `prompts/prompt_versions.yaml`.
3. **EDD in CI** — add `pytest tests/test_edd.py --run-edd` to GitHub Actions after deploy confirmed.
4. **Update cron script** — after scrape+embed: `huggingface-cli upload` lakehouse.duckdb → HF Dataset, restart HF Space.

### 🔑 DEPLOY ARCHITECTURE (confirmed)
- **MotherDuck**: silver_events, silver_fotmob_shots, match_mapping, gold_match_summaries ✅ (stateless)
- **lakehouse.duckdb**: 536MB, HNSW embeddings index — HF Dataset repo (git-lfs), downloaded at startup
- **xT_grid.csv**: 1KB static file, stays in repo ✅
- **Secrets in HF Spaces**: `MOTHERDUCK_TOKEN`, `ANTHROPIC_API_KEY`, `HF_TOKEN` (for dataset download)
- **Run command for HF**: `streamlit run app.py --server.port 7860`
- **Branch strategy**: `feat/hf-spaces-deploy` → push to `space/main` remote (HF Spaces)
- **`main` stays clean** — HF-specific files (`app.py`, `requirements.txt`) live on deploy branch only

### Why HF Spaces over Modal
Modal = serverless GPU inference, not app hosting. HF Spaces = native Streamlit, 5GB git-lfs, free tier.
Modal becomes relevant only for Phase 4 (local Llama 3 inference). Not now.

---

### Viz column mapping (do not revert)
`silver_fotmob_shots` → `visualizers.py` requires:
- `event_type` → `eventType`
- `player_name` → `playerName`
- `shot_type` → `shotType`
- `is_on_target` → `isOnTarget`

`silver_events` → `visualizers.py` requires:
- `event_row_id AS id` (for groupby count in `calculate_player_defensive_positions`)

`silver_fotmob_shots.match_id` = fotmob_match_id (NOT whoscored). Join via match_mapping.

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
- [2026-02-23](docs/engineering_diary/2026-02-23-phase3b-streamlit-deploy.md) — Phase 3b complete: Streamlit UI, MotherDuck viz migration, all 7 viz types verified, HF deploy strategy decided

**Completed milestones**:
- Phase 1: Bronze → Match Mapping → Silver → Gold → Embeddings → Vector Search → MotherDuck + CI
- Phase 2: RAG engine rewired to DuckDB VSS, orchestrator built, viz dispatch wired, 25/25 tests passing
- Phase 3a: Opik `@opik.track` end-to-end, EDD 3 scorers + 21 tests, golden dataset ground-truthed from DuckDB
- Phase 3b: Streamlit UI live locally, all 7 viz types working, viz fully migrated to MotherDuck, stale branches cleaned

**Last Updated**: 2026-02-23
