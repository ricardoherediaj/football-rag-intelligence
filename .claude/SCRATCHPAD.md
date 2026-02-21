# Session Scratchpad

**Purpose**: Current session state only. Historical sessions → `docs/engineering_diary/`.
**Update constantly. Trim aggressively.**

---

## 📍 Current State (2026-02-19)

**Branch**: `main` (Phase 1 merged)
**Status**: Phase 1 COMPLETE ✅ — starting Phase 2

### Pipeline Status
| Layer | Status | Count |
|---|---|---|
| Bronze | ✅ | 412 matches in MinIO + MotherDuck |
| Match Mapping | ✅ | 205/205 (100% coverage) |
| dbt Silver | ✅ | 279,104 events, 378 team performances |
| dbt Gold | ✅ | 205 match summaries in MotherDuck |
| GitHub Actions | ✅ | `dbt run --target prod` → PASS=3 in CI |
| Embeddings | ✅ | 205 match embeddings, 768-dim HNSW index |

---

## 🎯 Next Session — Start Here (Phase 2)

**Step 1 — Rewire RAG engine to DuckDB VSS**
- File: `src/football_rag/models/rag_pipeline.py`
- Problem: hardcoded to ChromaDB (`data/chroma`), which is disconnected from the pipeline
- Fix: replace ChromaDB retrieval with `array_distance()` query on `gold_match_embeddings`
- Reference: `scripts/test_vector_search.py` has the working DuckDB VSS query pattern

**Step 2 — Build query router**
- File: `src/football_rag/router.py` (exists, needs wiring)
- Classify query: SQL (stats lookup) vs semantic (similar matches) vs hybrid
- SQL path → DuckDB `gold_match_summaries`; semantic path → DuckDB VSS

**Step 3 — Wire visualizers into LLM response**
- File: `src/football_rag/visualizers.py`
- Goal: LLM response can include plots (shot maps, pass maps, pressure maps)
- Pattern: render plot → return as base64 or file path alongside text

**Step 4 — UI**
- Gradio (preferred, minimal) or Streamlit
- Single input box → router → retrieval → LLM → text + optional plot

---

## 📚 Historical Reference

Full session logs in engineering diary:
- [2026-02-14](docs/engineering_diary/2026-02-14-phase1-diagnosis.md) — Two parallel pipelines discovered, chose Hybrid architecture
- [2026-02-15](docs/engineering_diary/2026-02-15-phase1-silver-layer-complete.md) — dbt wired, 24 metrics, xG fix via match_mapping.json
- [2026-02-16](docs/engineering_diary/2026-02-16-phase1-complete.md) — Phase 1 declared complete (188 matches, 15/15 tests, vector search working)
- [2026-02-18](docs/engineering_diary/2026-02-18-fotmob-rewrite.md) — FotMob scraper rewritten (SSR extraction), 205/205 match mapping
- [2026-02-19](docs/engineering_diary/2026-02-19-phase1-motherduck-complete.md) — Phase 1 complete: MotherDuck migration, CI green, 205 embeddings

**Completed milestones**:
- Phase 1 pipeline operational: Bronze → Match Mapping → Silver → Gold → Embeddings → Vector Search
- FotMob rewritten to bypass x-mas auth header (SSR `__NEXT_DATA__` extraction)
- Match coverage expanded: 188 → 205 matches at 100% coverage
- Tech stack: Dagster + dbt + DuckDB + MinIO + sentence-transformers

**Last Updated**: 2026-02-19
