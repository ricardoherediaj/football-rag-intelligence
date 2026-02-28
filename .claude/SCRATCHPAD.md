# Session Scratchpad

**Purpose**: Current session state only. Historical sessions → `docs/engineering_diary/`.
**Update constantly. Trim aggressively.**

---

## Current State (2026-02-28)

**Branch**: `main`
**Status**: Wordalisation v4.0 COMPLETE — uncommitted changes staged, ready to commit

### Pipeline Status
| Layer | Status | Count |
|---|---|---|
| Bronze | ✅ | 430 matches in MinIO + MotherDuck |
| Match Mapping | ✅ | 214/214 (100% coverage) |
| dbt Silver | ✅ | 279,104 events, 378 team performances |
| dbt Gold | ✅ | 214 match summaries in MotherDuck |
| GitHub Actions | ✅ | lint + unit-tests jobs, 17 passed, 62 deselected |
| Embeddings | ✅ | 214 match embeddings, 768-dim HNSW index |
| RAG Engine | ✅ | DuckDB VSS, orchestrator wired, viz dispatch working |
| Observability | ✅ | `@opik.track` on orchestrator + rag_pipeline + generate |
| EDD Eval Harness | ✅ | 28 pytest tests, 4 scorers, 13-case golden dataset (v4) |
| Wordalisation | ✅ | `classify_metrics()` + `v4.0_tactical` + football prose output |
| **HF Spaces** | ✅ | **Live at https://rheredia8-football-rag-intelligence.hf.space/** |
| **BYOK + Rate Limit** | ✅ | **5 free queries/session, unlimited with own API key** |
| **Hybrid Automation** | ✅ | **dagster-daemon auto-starts at login via launchd** |
| **HF Deploy Assets** | ✅ | **hf_lakehouse_upload + hf_space_restart in deploy_job** |
| **MLOps Foundation** | ✅ | **pytest markers + pre-commit + detect-secrets + CI split + skills** |

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

### 1. Commit this session's work
- 7 modified files + 2 new skills + 1 new diary — commit as `feat(wordalisation): v4.0 classify_metrics + v4.0_tactical prompt + 13-case EDD`
- Then check CI is green (`gh run list --limit 1`)

### 2. First Formal Release — v0.4.0
- Use `/release` skill to tag Phase 4a + MLOps Foundation + Wordalisation as `v0.4.0`
- **Do not tag until CI is green after above commit**

### 3. Run Full EDD — Score v4.0_tactical
- `uv run pytest tests/test_edd.py -v -m edd --run-edd`
- Update `v4.0_tactical: score:` in `prompt_versions.yaml` with actual result
- If `tactical_insight` < 0.75 on any case → use `/prompt-workshop` to iterate

### 4. EDD in CI (GitHub Actions)
- Add `workflow_dispatch`-gated job to CI workflow
- Requires `ANTHROPIC_API_KEY` + `MOTHERDUCK_TOKEN` + `OPIK_API_KEY` as GitHub secrets

### 5. HF_TOKEN in GitHub Secrets
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
- [2026-02-26](docs/engineering_diary/2026-02-26-phase4a-end-to-end-verified.md) — Phase 4a complete: hybrid pipeline + workspace.yaml fix
- [2026-02-27](docs/engineering_diary/2026-02-27-mlops-foundation.md) — MLOps foundation: markers + pre-commit + CI split + skills
- [2026-02-28](docs/engineering_diary/2026-02-28-wordalisation-v4-football-language.md) — Wordalisation v4.0: classify_metrics + v4.0_tactical prompt + 13-case EDD + prompt-workshop skill

**Last Updated**: 2026-02-28

---

## Dagster Daemon Gotchas (critical)
- workspace.yaml MUST be in DAGSTER_HOME (symlink to root works)
- Use python_module + working_directory (NOT python_file with relative path)
- dagster job execute = in-process, invisible to daemon, sensors DO NOT fire
- dagster job launch = registered in SQLite, daemon picks up, sensors fire

## Key fixes 2026-02-26
- WhoScored stale-counter: empty_weeks counts only calendar pages with zero matches total
- workspace.yaml in DAGSTER_HOME: daemon gRPC resolves code locations
- HF_TOKEN in .env: deploy_job works from daemon subprocess
- Pipeline status: 430 bronze, 214/214 mapped, 214 embeddings, HF Space updated

## MLOps Foundation (2026-02-27) — COMPLETE
- pytest markers: unit / integration / local_data / edd tiers with addopts default
- conftest.py: skip logic + --run-* flags
- .pre-commit-config.yaml: ruff + detect-private-key + debug-statements + detect-secrets
- .secrets.baseline: committed (11 false-positives, all in archive/)
- CI: lint job + unit-tests job (gated)
- Skills: /release (CalVer tagging) + /health-check (6-layer system table)
- Diary: docs/engineering_diary/2026-02-27-mlops-foundation.md
