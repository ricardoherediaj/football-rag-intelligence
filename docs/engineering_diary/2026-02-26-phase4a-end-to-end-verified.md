# 2026-02-26 — Phase 4a: Pipeline End-to-End Verification + MLOps Foundation

## Context

Session goal: run the complete Eredivisie pipeline end-to-end with 9 new matches from Jornada 23 (Feb 20-22), fix incremental scraping, and establish a solid automation + CI foundation.

## What We Built

### 1. WhoScored Stale-Counter Bug Fix

Root cause: `_collect_direction` used a stale counter based on "no new URLs" (after filtering already-scraped matches). This meant that if the last 3 calendar weeks were all already scraped, traversal stopped even if there were newer weeks beyond them.

Fix: `collect_matches_from_page` now returns `(page_urls, total_on_page)`. The `empty_weeks` counter only increments when `total_on_page == 0` — a truly empty calendar page with no finished matches.

Result: 9 new matches from Jornada 23 found and scraped correctly.

### 2. Dagster workspace.yaml + DAGSTER_HOME

Critical discovery: the `dagster-daemon` requires `workspace.yaml` in `DAGSTER_HOME` to resolve code locations via gRPC. Without it:
- Sensors always return "empty result"
- `dagster job launch` queues runs but daemon can't execute them

Fix: symlink `ops/dagster_home_local/workspace.yaml` -> `workspace.yaml` (root).
Must use `python_module` + `working_directory` (not `python_file` with relative path).

Key distinction between CLI modes:
- `dagster job execute` = in-process, NOT registered in daemon's SQLite, sensors DO NOT fire
- `dagster job launch` = queued in SQLite, daemon picks up, sensors fire

### 3. HF_TOKEN in .env

`deploy_job` failed with `HF_TOKEN env var not set`. The daemon subprocess loads vars from `.env` via `start_dagster_daemon.sh`, but `HF_TOKEN` wasn't there. Added it (same value as `HF_SPACES`).

### 4. CI/CD Separation (GitHub Actions vs Dagster)

Rewrote GitHub Actions workflow from "Matchday Pipeline" (dbt run on cron) to "CI — Code Quality" (pytest on push/PR). Eliminated redundant `dbt run --target prod` from CI.

Discovered test categorization issue: several test files require local infrastructure not available in GH runner:
- `test_duckdb_pipeline.py` / `test_phase1_pipeline.py`: need `data/raw/` and `lakehouse.duckdb`
- `test_whoscored_scraper.py` / `test_fotmob_scraper.py`: need Playwright/Chromium

Temporary fix: `--ignore` flags. Permanent fix (next session): `@pytest.mark.integration` + `@pytest.mark.local_data` markers with `conftest.py` skip logic.

### 5. Full Pipeline Run (verified end-to-end)

```
scrape_and_load_job  RUN_SUCCESS (430 bronze, 214/214 mapped)
transform_job        RUN_SUCCESS (dbt silver + gold + 214 embeddings, HNSW index)
deploy_job           RUN_SUCCESS (575MB to HF Dataset + Space restart)
GitHub Actions CI    PASS (1m13s)
```

## Decisions Made

- `dagster job execute` is OK for ad-hoc debugging but `dagster job launch` is required for sensor chain to work
- workspace.yaml must live in DAGSTER_HOME, not just project root
- HF_TOKEN and HF_SPACES can share the same token value (same HF account)
- CI tests: unit tests only — data/pipeline tests belong to local post-pipeline validation

## Lessons Learned

1. The daemon is "blind" without workspace.yaml — it can tick schedule/sensor loops but can't resolve or execute anything
2. `dagster job execute` vs `dagster job launch` is a critical distinction that's easy to miss
3. Test categorization should happen at project start, not when CI breaks
4. DuckDB file lock errors (when running concurrent Dagster jobs) are a sign of overlapping test/pipeline runs — not a bug in the code

## Next Steps

1. Test markers refactor: `@pytest.mark.integration` + `@pytest.mark.local_data` in conftest.py
2. pre-commit hooks: ruff + detect-secrets + sqlfluff (duckdb dialect)
3. Separate CI jobs: lint / unit-tests / type-check
4. Prompt v4.0_tactical: improve tactical_insight scorer (currently 0.91)
5. EDD in CI: `workflow_dispatch` gated job
