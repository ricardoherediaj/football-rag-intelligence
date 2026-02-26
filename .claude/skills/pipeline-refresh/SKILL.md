---
name: pipeline-refresh
description: Manually trigger full data refresh pipeline (scrape → dbt → embed → HF deploy). Use when the schedule missed a run, a job failed mid-way, or you want to force a refresh before the next scheduled run.
version: 1.0.0
disable-model-invocation: true
metadata:
  author: Ricardo Heredia
  category: pipeline-ops
  tags: [dagster, scraping, dbt, huggingface, pipeline]
---

# Pipeline Refresh

Trigger the full Eredivisie data refresh pipeline end-to-end.

## When to Use

- Laptop was closed Mon/Thu 7am UTC (missed scheduled run)
- A job failed mid-way and needs a clean re-run
- You want fresh data before the next scheduled run
- Verifying the pipeline is healthy after a code change

## Step 1: Verify dagster-daemon is Running

```bash
launchctl list | grep football-rag
```

Expected: a line with a PID and `com.football-rag.dagster-daemon`.

If missing, start it:
```bash
launchctl load ~/Library/LaunchAgents/com.football-rag.dagster-daemon.plist
```

## Step 2: Launch the Scrape Job

Runs incrementally — only downloads matches newer than what's already in Bronze.

```bash
uv run dagster job execute -m orchestration.defs -j scrape_and_load_job
```

Expected duration: ~15-30 min.

## Step 3: Wait for Chain to Auto-Fire

After scrape completes, sensors auto-trigger the rest:

```
scrape_and_load_job ✅
  → [post_scrape_transform_sensor] transform_job
      → [post_transform_deploy_sensor] deploy_job
```

`transform_job` runs dbt (→ MotherDuck) + embeddings (→ lakehouse.duckdb). ~5-10 min.
`deploy_job` uploads lakehouse.duckdb to HF Dataset + restarts Space. ~10-15 min.

## Step 4: Verify Data Freshness

Check MotherDuck for the latest match date:

```bash
uv run python -c "
import duckdb, os
token = open('.env').read()
token = [l for l in token.split('\n') if 'MOTHERDUCK_TOKEN' in l][0].split('=')[1].strip()
os.environ['motherduck_token'] = token
db = duckdb.connect('md:')
rows = db.execute('''
    SELECT match_date, home_team, away_team
    FROM football_rag.main_main.gold_match_summaries
    ORDER BY match_date DESC LIMIT 5
''').fetchall()
for r in rows: print(r)
"
```

Latest match date should reflect the most recent Eredivisie matchday.

## If Sensors Don't Auto-Fire

Run manually (sensors need the daemon to be running and sensors enabled):

```bash
uv run dagster job execute -m orchestration.defs -j transform_job
uv run dagster job execute -m orchestration.defs -j deploy_job
```

## Verify HF Space

After deploy_job completes, confirm the app serves fresh data:
https://rheredia8-football-rag-intelligence.hf.space/

## Expected Durations

| Job | Duration |
|---|---|
| `scrape_and_load_job` (incremental) | 15-30 min |
| `transform_job` (dbt + embeddings) | 5-10 min |
| `deploy_job` (536MB upload + restart) | 10-15 min |
| **Total** | **~30-55 min** |
