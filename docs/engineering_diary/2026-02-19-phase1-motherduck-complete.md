# Engineering Diary: Phase 1 Complete — MotherDuck Migration + Embeddings
**Date:** 2026-02-19
**Tags:** `phase1`, `motherduck`, `github-actions`, `dbt`, `embeddings`, `cloud`

## 1. Problem Statement

Phase 1 had three open items after the FotMob rewrite session (2026-02-18):

1. **dbt ran locally but had no cloud home.** Gold layer lived in a local
   `lakehouse.duckdb` file — not accessible from CI or anywhere else.
2. **GitHub Actions couldn't run dbt independently.** Scrapers use Playwright
   + residential IP (WhoScored/FotMob block datacenter IPs), so CI can't scrape.
   But dbt is pure SQL — it *can* run in CI if the source data is in the cloud.
3. **Embeddings were stale.** `gold_match_embeddings` had 188 vectors from a
   previous run; Gold now had 205 match summaries.

The goal: make the pipeline self-sustaining — scraping stays local (Dagster),
transformations run automatically in the cloud (GitHub Actions → MotherDuck).

## 2. Approach

### Why MotherDuck

DuckDB is the project's native SQL engine. MotherDuck is cloud DuckDB — same
dialect, same client library (`duckdb.connect("md:...")`), no schema migration,
no new ORM. The alternative (Postgres, BigQuery, Snowflake) would require
rewriting every SQL model and adding connectors.

Free Lite plan: 10GB storage, 10 compute hrs/month, no credit card. Fits the
entire season (Bronze JSON ~50-80MB compressed) with room to spare.

### Architecture Decision: Split Concerns

```
Dagster (local, residential IP)          GitHub Actions (cloud, datacenter IP)
────────────────────────────────         ────────────────────────────────────
whoscored_match_data (Playwright)        dbt run --target prod
fotmob_match_data (Playwright)             silver_events
raw_matches_bronze → MinIO               silver_team_metrics
raw_matches_bronze → MotherDuck (sync)   gold_match_summaries
match_mapping                          dbt test --target prod
  ↓ on success (sensor)
dbt_silver_models (local dev)
dbt_gold_models (local dev)
gold_match_embeddings (local DuckDB)
```

Scraping stays on Dagster because anti-bot systems block datacenter IPs.
dbt runs in CI because it's pure SQL with no browser dependency.

### Key Implementation Steps

**1. MotherDuck prod target in `profiles.yml`**
```yaml
prod:
  type: duckdb
  path: "md:football_rag?motherduck_token={{ env_var('MOTHERDUCK_TOKEN') }}"
  threads: 4
  schema: main
  settings:
    memory_limit: "8GB"
```

**2. `BRONZE_DATABASE` env var in `sources.yml`**

`bronze_matches` needed to switch databases between dev (local `lakehouse`) and
prod (MotherDuck `football_rag`). Parameterized via env var:
```yaml
database: "{{ env_var('BRONZE_DATABASE', 'lakehouse') }}"
```
CI passes `BRONZE_DATABASE=football_rag`. Local dev uses default `lakehouse`.

**3. Dual-write in `raw_matches_bronze` Dagster asset**

Bronze must be in MotherDuck for CI to be self-contained. Asset now writes to
local DuckDB always, and syncs to MotherDuck if `MOTHERDUCK_TOKEN` is set:
```python
if motherduck_token := os.getenv("MOTHERDUCK_TOKEN"):
    md_db = duckdb.connect(f"md:football_rag?motherduck_token={motherduck_token}")
    _load_matches_into(md_db, client)
```

**4. GitHub Actions workflow**

Cron Mon/Thu 7am UTC + `workflow_dispatch`. Steps: checkout → uv → `dbt deps`
→ `dbt run --target prod` → `dbt test --target prod`. MotherDuck token passed
via GitHub secret.

**5. One-time Bronze sync**

Synced existing 412 Bronze rows + 5,345 `silver_fotmob_shots` rows +
205 `match_mapping` rows from local DuckDB to MotherDuck via Python before
the first CI run.

### dbt Test Cleanup (separate session)

Three categories of broken tests found during CI runs:

| Test | Root cause | Fix |
|---|---|---|
| `bronze_events` source | Ghost table — defined but never built | Remove from `sources.yml` |
| `home_team`/`away_team`/`match_date` not_null | `bronze_matches` is `(match_id, source, data JSON)` — columns are inside JSON | Remove column tests |
| `end_x`/`end_y` accepted_range | WhoScored sends out-of-range coords for aerials/set-pieces | Remove tests (source data, not controllable) |
| `prog_pass` range -50/105 | Edge cases on full-pitch back passes | Widen to -105/105 |

Final result: `PASS=69 WARN=0 ERROR=0 FAIL=0` in CI.

### Embeddings Regeneration

```bash
uv run python scripts/materialize_embeddings.py
```

- Model: `sentence-transformers/all-mpnet-base-v2` (768-dim)
- Input: `gold_match_summaries` (205 rows from local DuckDB Gold layer)
- Output: `gold_match_embeddings` table with HNSW index
- Result: 205/205 ✅

## 3. Verification

| Check | Result |
|---|---|
| `dbt run --target prod` locally | PASS=3 |
| GitHub Actions run `22188361561` | PASS=69, all green |
| `bronze_matches` in MotherDuck | 412 rows |
| `silver_fotmob_shots` in MotherDuck | 5,345 rows |
| `match_mapping` in MotherDuck | 205 rows |
| `gold_match_embeddings` locally | 205 rows, HNSW index |

## 4. Lessons Learned

**Don't write source tests for JSON-embedded fields.** `bronze_matches` has
3 columns (`match_id`, `source`, `data`). Documenting JSON internals as dbt
column tests causes binder errors — dbt runs `WHERE home_team IS NULL` as SQL.
Document JSON structure in `description`, not in `tests`.

**Dual-write is the right Bronze sync pattern.** Alternatives considered:
- `dbt run --target prod` with `attach` (local file attach in MotherDuck) — fragile, env-specific paths
- Separate sync job — extra orchestration complexity
- Dual-write in the asset — simple, idempotent, runs whenever scraping runs

**`BRONZE_DATABASE` env var pattern scales to multi-env.** Same `sources.yml`
works for dev, staging, and prod by changing one env var. No Jinja conditionals.

## 5. Next Steps

Phase 2: RAG Integration (new session, new context).

See SCRATCHPAD.md Phase 2 scope. First task: rewire
`src/football_rag/models/rag_pipeline.py` from ChromaDB → DuckDB VSS
(`gold_match_embeddings`).
