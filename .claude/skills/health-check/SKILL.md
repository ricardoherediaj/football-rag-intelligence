---
name: health-check
description: Verify full system health — dagster daemon, MinIO, CI status, HF Space, MotherDuck row counts. Use at session start, before a release, or when something feels off. Examples: "health check", "is everything up?", "system status".
version: 1.0.0
metadata:
  author: Ricardo Heredia
  category: operations
  tags: [monitoring, health, dagster, minio, ci]
---

# System Health Check

Verifies every layer of the Football RAG Intelligence stack is alive and consistent.

## When to Use

Trigger when user:
- Starts a new session ("check if everything is up")
- Before launching a pipeline run
- Before creating a release
- After a system restart or long break
- When pipeline output seems wrong

## Checks (run in this order)

### 1. Dagster Daemon

```bash
launchctl list | grep football-rag
ps aux | grep dagster-daemon | grep -v grep
```

Expected: PID visible, exit code 0 in launchctl.

If dead: `launchctl start com.football-rag.dagster-daemon`

### 2. MinIO

```bash
launchctl list | grep football-rag
docker ps | grep minio
curl -s http://localhost:9000/minio/health/live && echo "MinIO OK"
```

Expected: `MinIO OK`

If dead: `launchctl start com.football-rag.minio`

### 3. GitHub Actions CI

```bash
gh run list --limit 3
```

Expected: latest run on `main` is `completed / success`.

If failing: check `gh run view <id> --log-failed`

### 4. HF Space

```bash
python3 -c "
from huggingface_hub import HfApi
api = HfApi()
info = api.get_space_runtime('rheredia8/football-rag-intelligence')
print('Space status:', info.stage)
"
```

Expected: `RUNNING`

If not running: run `deploy_job` to restart.

### 5. MotherDuck row counts

```bash
uv run python -c "
import duckdb
db = duckdb.connect('md:football_rag?motherduck_token=$(grep MOTHERDUCK_TOKEN .env | cut -d= -f2)')
tables = ['bronze_matches', 'silver_events', 'gold_match_summaries']
for t in tables:
    try:
        n = db.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]
        print(f'{t}: {n}')
    except Exception as e:
        print(f'{t}: ERROR - {e}')
"
```

Expected minimums:
- `bronze_matches` ≥ 420
- `silver_events` ≥ 270,000
- `gold_match_summaries` ≥ 210

### 6. lakehouse.duckdb embeddings

```bash
python3 -c "
import duckdb
db = duckdb.connect('data/lakehouse.duckdb')
n = db.execute('SELECT COUNT(*) FROM gold_match_embeddings').fetchone()[0]
print(f'Embeddings: {n}')
"
```

Expected: ≥ 210

## Output Format

Report results as a table:

```
System Health — 2026-02-26 14:00
─────────────────────────────────
Dagster daemon    ✅  PID 67965
MinIO             ✅  http://localhost:9000
CI (main)         ✅  ccadf14 — success (1m13s)
HF Space          ✅  RUNNING
MotherDuck        ✅  bronze=430, silver=279104, gold=214
Embeddings        ✅  214
─────────────────────────────────
All systems operational
```

Flag any check that fails with ❌ and suggest the fix.

## Rules

- Run ALL checks even if one fails — report the full picture
- Never modify anything — this is read-only observation
- If MotherDuck is unreachable, note it but don't block the report
- Update SCRATCHPAD.md Pipeline Status section if counts differ from what's recorded
