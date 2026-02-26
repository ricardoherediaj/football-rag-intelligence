# Phase 4a — Hybrid Pipeline Automation
**Date**: 2026-02-26
**Status**: COMPLETE

## What We Built

Closed the last gap in the end-to-end pipeline: after scraping and embedding, the fresh `lakehouse.duckdb` now automatically uploads to HF Dataset and restarts the public Space — all orchestrated by Dagster running as a macOS LaunchAgent.

## Problem

After Phase 3b, the app was live but served static data. The pipeline had no mechanism to push updated embeddings to HF Spaces. Each refresh required manual `huggingface-cli upload` + `restart_space()` calls. The daemon also required a manual `dagster dev` command to start.

## Solution

**Two new Dagster assets** in `orchestration/assets/hf_deploy_assets.py`:
- `hf_lakehouse_upload` — uploads `lakehouse.duckdb` (536MB) to `rheredia8/football-rag-data` via `huggingface_hub.HfApi`
- `hf_space_restart` — calls `api.restart_space()` so the Space re-downloads fresh embeddings at next cold start

**New job + sensor** in `orchestration/schedules.py`:
- `deploy_job` — selects both deploy assets
- `post_transform_deploy_sensor` — `run_status_sensor` that fires `deploy_job` when `transform_job` succeeds

**macOS LaunchAgent** (`~/Library/LaunchAgents/com.football-rag.dagster-daemon.plist`):
- Starts `dagster-daemon` automatically at login via `launchd`
- Uses a wrapper script (`ops/start_dagster_daemon.sh`) to `source .env` before launching
- Points to `ops/dagster_home_local/dagster.yaml` — SQLite-based, no Postgres/Docker dependency

## Automated Chain

```
macOS login → launchd → dagster-daemon (background, ~50MB RAM)
  Schedule Mon/Thu 7am UTC
    → scrape_and_load_job (Playwright: WhoScored + FotMob)
        → [sensor] transform_job (dbt → MotherDuck + lakehouse.duckdb embeddings)
            → [sensor] deploy_job (upload DuckDB → HF Dataset → restart Space)
```

## Key Decision: launchd vs Docker

Removed Docker dependency for the pipeline daemon. Rationale:
- Docker overhead (~600-800MB RAM for compose stack) is disproportionate for a twice-weekly local scraper
- `dagster-daemon` as a LaunchAgent uses ~50MB idle
- SQLite state is sufficient for a single-user pipeline
- Docker still valid for team reproducibility (fork/clone scenario) — documented in README

The daemon doesn't run the scraper continuously — it only wakes up on schedule (Mon/Thu 7am) or when triggered manually. Between runs: ~50MB RAM idle.

## Why Not GitHub Actions?

Playwright (headless Chrome) can technically run in GitHub Actions, but:
1. WhoScored has bot detection that requires real browser sessions with realistic timing
2. FotMob uses in-browser fetch tokens that are harder to replicate in headless CI
3. Scraping JavaScript-heavy sites from CI IPs gets flagged faster than residential IPs
4. The scraper requires ~30-60 min for full incremental runs — too long for CI

The right boundary: **scraping is a local concern** (your laptop, your IP, your session). **CI is for tests and dbt deployment** (stateless, fast, no browser needed).

## Verification

```bash
uv run python -c "from orchestration.defs import defs; print(len(defs.assets), 'assets')"
# → 12 assets, 3 jobs, 2 sensors

launchctl list | grep football-rag
# → 36404  0  com.football-rag.dagster-daemon  (stable PID, not restarting)
```

## Files Changed

| File | Change |
|---|---|
| `orchestration/assets/hf_deploy_assets.py` | NEW — hf_lakehouse_upload + hf_space_restart |
| `orchestration/schedules.py` | Added deploy_job + post_transform_deploy_sensor |
| `orchestration/defs.py` | Registered new module, job, sensor |
| `ops/dagster_home_local/dagster.yaml` | NEW — local SQLite Dagster home |
| `ops/start_dagster_daemon.sh` | NEW — env-loading wrapper for launchd |
| `~/Library/LaunchAgents/com.football-rag.dagster-daemon.plist` | NEW — macOS LaunchAgent |
| `.gitignore` | Added dagster_home_local runtime dirs |

## Next

- Prompt v4.0_tactical: LLM interprets tactically, not just recites metrics
- EDD in CI: `pytest tests/test_edd.py --run-edd` in GitHub Actions
- HF_TOKEN in GitHub Secrets for CI-triggered deploys
