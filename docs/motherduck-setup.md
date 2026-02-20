# MotherDuck Setup Reference

**Purpose**: Operational reference for the MotherDuck cloud DuckDB integration.
Not a diary — this is the "how to operate it" doc.

---

## Why MotherDuck

- Cloud DuckDB: same SQL dialect, same Python client, zero schema migration
- Free Lite: 10GB storage, 10 compute hrs/month, no credit card
- Fits full Eredivisie season (~50-80MB compressed Bronze JSON)
- Enables GitHub Actions `dbt run` without local files

---

## Connection

```python
import duckdb
import os

# Direct connection
conn = duckdb.connect(f"md:football_rag?motherduck_token={os.getenv('MOTHERDUCK_TOKEN')}")

# dbt (profiles.yml prod target)
# path: "md:football_rag?motherduck_token={{ env_var('MOTHERDUCK_TOKEN') }}"
```

---

## Databases

| Database | Purpose |
|---|---|
| `football_rag` | All project data (Bronze + Silver sources + Gold) |

### Tables in `football_rag.main`

| Table | Rows | Written by |
|---|---|---|
| `bronze_matches` | 412 | `raw_matches_bronze` Dagster asset (dual-write) |
| `silver_fotmob_shots` | 5,345 | `raw_matches_bronze` Dagster asset (dual-write) |
| `match_mapping` | 205 | `match_mapping` Dagster asset |
| `silver_events` | 279,104 | `dbt run --target prod` |
| `silver_team_metrics` | 378 | `dbt run --target prod` |
| `gold_match_summaries` | 205 | `dbt run --target prod` |

> `gold_match_embeddings` lives in **local DuckDB only** (DuckDB VSS extension
> not supported in MotherDuck). Embeddings are regenerated locally after each
> `dbt run`.

---

## Environment Variables

```bash
MOTHERDUCK_TOKEN=<token>         # Required for prod writes
BRONZE_DATABASE=football_rag     # Used by dbt sources.yml in prod/CI
                                 # Default: lakehouse (local dev)
```

---

## dbt Targets

```bash
uv run dbt run                          # dev  → local lakehouse.duckdb
uv run dbt run --target prod            # prod → MotherDuck football_rag
uv run dbt test --target prod           # test against MotherDuck
```

---

## GitHub Actions

Workflow: `.github/workflows/matchday_pipeline.yml`
- Trigger: Mon/Thu 7am UTC + `workflow_dispatch`
- Secret: `MOTHERDUCK_TOKEN` (set in repo Settings → Secrets)
- Env: `BRONZE_DATABASE=football_rag`, `DUCKDB_MEMORY_LIMIT=6GB`

Manual trigger:
```bash
gh workflow run matchday_pipeline.yml
gh run watch  # follow live
```

---

## Sync Pattern (Bronze)

Bronze is written to MotherDuck by the `raw_matches_bronze` Dagster asset
via dual-write. Runs automatically whenever scraping runs (Mon/Thu via schedule
or manual Dagster trigger).

Manual re-sync if needed:
```python
import duckdb, os

local = duckdb.connect("data/lakehouse.duckdb")
md = duckdb.connect(f"md:football_rag?motherduck_token={os.getenv('MOTHERDUCK_TOKEN')}")

rows = local.execute("SELECT * FROM bronze_matches").fetchall()
md.execute("CREATE OR REPLACE TABLE bronze_matches (match_id VARCHAR, source VARCHAR, data JSON)")
md.executemany("INSERT INTO bronze_matches VALUES (?, ?, ?)", rows)
print(f"Synced {len(rows)} rows")
```
