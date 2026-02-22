# Session Scratchpad

**Purpose**: Current session state only. Historical sessions → `docs/engineering_diary/`.
**Update constantly. Trim aggressively.**

---

## 📍 Current State (2026-02-22)

**Branch**: `main` (Phase 3a complete, ready to merge PR)
**Status**: Phase 3a COMPLETE + DEBUGGED ✅ — EDD baseline 21/21 passing, all metrics locked

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
| EDD Eval Harness | ✅ | 21 pytest tests, 3 scorers (no Hallucination), 10-case golden dataset |
| **EDD Baseline** | ✅ | **retrieval_accuracy=1.0000, tactical_insight=0.9142, answer_relevance=0.8380** |

### EDD Metrics (Final Stack)
1. **retrieval_accuracy** (custom): Perfect (1.0) — all 10 matches retrieved correctly
2. **tactical_insight** (custom CoT): 0.9142 — strong domain quality, well above 0.7 threshold
3. **answer_relevance** (Opik native): 0.8380 — solid query-output alignment
4. ~~Hallucination~~ **REMOVED** — design mismatch for numerical-context RAG (kept visual_grounding in tactical_insight instead)

---

## 🎯 Next Session — Start Here

**Immediate**: Merge PR `feat/phase3a-opik-edd` → `main`

**Next tasks (in order)**:
1. **Phase 3b: Streamlit UI** — Single-page app: query input → commentary + optional chart. Wire to `orchestrator.query(text|viz path)`. No external deps, pure Streamlit + DuckDB.
2. **Phase 4: REST API** — FastAPI wrapper on orchestrator, Modal inference backend (optional upgrade from local Claude)
3. **HF Spaces deploy** — Push Phase 2/3a engine to public demo after Streamlit works locally

### EDD Maintenance
When eval queries change:
```python
GOLDEN_DATASET_NAME = "football-rag-golden-v3"  # Bump to v4, v5, etc.
# That's it — new dataset name guarantees clean slate, no delete logic needed
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
- Phase 3a: Opik `@opik.track` end-to-end, `test_edd.py` with 4 scorers + 31 tests, golden dataset ground-truthed from DuckDB

**Last Updated**: 2026-02-22
