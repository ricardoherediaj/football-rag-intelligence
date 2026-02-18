# Session Scratchpad

**Purpose**: Current session state only. Historical sessions → `docs/engineering_diary/`.
**Update constantly. Trim aggressively.**

---

## 📍 Current State (2026-02-18)

**Branch**: `feat/phase1-data-pipeline`
**Status**: Phase 1 ~95% — one blocker left (dbt Silver OOM in Docker)

### Pipeline Status
| Layer | Status | Count |
|---|---|---|
| Bronze | ✅ | 412 matches (205 WhoScored + 207 FotMob) |
| Match Mapping | ✅ | 205/205 (100% coverage) |
| dbt Silver | ❌ OOM in Docker | works locally (101s) |
| dbt Gold | ⏳ blocked by Silver | — |
| Embeddings | ⏳ blocked by Gold | — |

---

## 🔥 Active Blocker

**dbt Silver OOM in Docker**
- Container capped at ~3.82 GiB; DuckDB + Python overhead exceeds it
- `profiles.yml` already fixed: `memory_limit: env_var('DUCKDB_MEMORY_LIMIT', '2GB')`
- Container NOT rebuilt yet after this change
- Works perfectly on host: `uv run dbt run` → PASS=2

**Options to unblock**:
1. `docker compose up -d --build` → test if 2GB is enough
2. If still OOM → drop to `1GB` (spill-to-disk, slower but works)
3. Skip Docker for dbt entirely → run on host, use GitHub Actions for prod

---

## 🎯 Next Decision: Architecture Direction

**Agreed**: Move to GitHub Actions + MotherDuck instead of fixing Docker for prod.

**Plan**:
1. Run `dbt run` on host → validate Silver + Gold pass (already works)
2. Add `prod` target in `profiles.yml` pointing to MotherDuck (`md:`)
3. `dbt run --target prod` → Gold layer lives in MotherDuck
4. GitHub Actions workflow (cron Monday post-matchday) with `uv` + MotherDuck secrets
5. Dagster stays for local dev / scraping orchestration only
6. Delete dagster_webserver/daemon from Docker — only MinIO stays as container

**Phase 1 definition of done** (revised):
- [ ] dbt Silver + Gold run locally without OOM
- [ ] Gold layer in MotherDuck (cloud)
- [ ] GitHub Actions pipeline running
- [ ] Embeddings generated (205 matches)

---

## 🔧 Tech Debt Backlog

**TD-001**: Incremental scrape check via filesystem is fragile — breaks on fresh container.
- Fix: Query `bronze_matches` table for existing IDs instead of local `data/raw/`
- File: `orchestration/assets/scrapers.py`
- Priority: Medium

---

## 📚 Historical Reference

Full session logs in engineering diary:
- [2026-02-14](docs/engineering_diary/2026-02-14-phase1-diagnosis.md) — Two parallel pipelines discovered, chose Hybrid architecture
- [2026-02-15](docs/engineering_diary/2026-02-15-phase1-silver-layer-complete.md) — dbt wired, 24 metrics, xG fix via match_mapping.json
- [2026-02-16](docs/engineering_diary/2026-02-16-phase1-complete.md) — Phase 1 declared complete (188 matches, 15/15 tests, vector search working)
- [2026-02-18](docs/engineering_diary/2026-02-18-fotmob-rewrite.md) — FotMob scraper rewritten (SSR extraction), 205/205 match mapping

**Completed milestones**:
- Phase 1 pipeline operational: Bronze → Match Mapping → Silver → Gold → Embeddings → Vector Search
- FotMob rewritten to bypass x-mas auth header (SSR `__NEXT_DATA__` extraction)
- Match coverage expanded: 188 → 205 matches at 100% coverage
- Tech stack: Dagster + dbt + DuckDB + MinIO + sentence-transformers

**Last Updated**: 2026-02-18
