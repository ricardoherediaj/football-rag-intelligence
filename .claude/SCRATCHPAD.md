# Session Scratchpad

**Purpose**: Current session state only. Historical sessions → `docs/engineering_diary/`.
**Update constantly. Trim aggressively.**

---

## Current State (2026-02-26)

**Branch**: `main`
**Status**: Phase 4a COMPLETE — hybrid pipeline fully automated

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
| **HF Spaces** | ✅ | **Live at https://rheredia8-football-rag-intelligence.hf.space/** |
| **BYOK + Rate Limit** | ✅ | **5 free queries/session, unlimited with own API key** |
| **Hybrid Automation** | ✅ | **dagster-daemon auto-starts at login via launchd** |
| **HF Deploy Assets** | ✅ | **hf_lakehouse_upload + hf_space_restart in deploy_job** |

### Automated Flow (now working end-to-end)
```
macOS login → launchd → dagster-daemon (background)
  Schedule Mon/Thu 7am UTC
    → scrape_and_load_job
        → [sensor] transform_job  (dbt → MotherDuck + lakehouse.duckdb)
            → [sensor] deploy_job  (upload DuckDB → HF Dataset → restart Space)
```

---

## Next Session — TODO (priority order)

### 1. Prompt v4.0_tactical
- Current LLM recites metrics instead of interpreting them tactically
- Edit `prompts/prompt_versions.yaml` — new system prompt emphasizing "why" over "what"
- Re-run EDD to measure improvement on `tactical_insight` (currently 0.91)

### 2. EDD in CI (GitHub Actions)
- Add `pytest tests/test_edd.py --run-edd` step to CI workflow
- Requires `ANTHROPIC_API_KEY` + `MOTHERDUCK_TOKEN` + `OPIK_API_KEY` as GitHub secrets

### 3. HF_TOKEN in GitHub Secrets
- deploy_job needs HF_TOKEN — add to repo secrets so CI can also trigger deploys

---

## Deploy Architecture (reference)
- **MotherDuck**: silver_events, silver_fotmob_shots, match_mapping, gold_match_summaries (stateless)
- **lakehouse.duckdb**: 536MB, HNSW embeddings index — HF Dataset repo (git-lfs), downloaded at startup
- **HF Space remote**: `space` → `https://huggingface.co/spaces/rheredia8/football-rag-intelligence`
- **HF Dataset**: `rheredia8/football-rag-data` (private, contains lakehouse.duckdb)
- **Secrets**: `MOTHERDUCK_TOKEN`, `ANTHROPIC_API_KEY`, `HF_TOKEN`
- **Deploy flow**: edit app.py locally → `upload_file()` → `restart_space()`

### HF Spaces gotchas (learned 2026-02-23)
- Hardcodes `streamlit==1.32.0`, `numpy<2` required
- Must `INSTALL vss` before `LOAD vss`
- `motherduck_token` (lowercase) not `MOTHERDUCK_TOKEN`
- `use_column_width` not `use_container_width` (pre-1.40)
- Must upload ALL changed source files (not just app.py) — orchestrator.py broke when missed

---

## Historical Reference

Full session logs in engineering diary:
- [2026-02-14](docs/engineering_diary/2026-02-14-phase1-diagnosis.md) — Two parallel pipelines discovered
- [2026-02-15](docs/engineering_diary/2026-02-15-phase1-silver-layer-complete.md) — dbt wired, 24 metrics
- [2026-02-16](docs/engineering_diary/2026-02-16-phase1-complete.md) — Phase 1 complete (188 matches)
- [2026-02-19](docs/engineering_diary/2026-02-19-phase1-motherduck-complete.md) — MotherDuck migration, CI green
- [2026-02-21](docs/engineering_diary/2026-02-21-phase2-rag-engine.md) — Phase 2 complete: ChromaDB → DuckDB VSS
- [2026-02-22](docs/engineering_diary/2026-02-22-phase3a-opik-edd.md) — Phase 3a complete: Opik + EDD
- [2026-02-23](docs/engineering_diary/2026-02-23-phase3b-streamlit-deploy.md) — Phase 3b complete: Streamlit + HF deploy

**Last Updated**: 2026-02-24
