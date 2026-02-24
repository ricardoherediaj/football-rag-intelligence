# Engineering Diary: Phase 3b — Streamlit UI + Stateless Viz Migration
**Date:** 2026-02-23
**Tags:** `streamlit, viz, motherduck, stateless, hf-spaces, deploy, phase3b`

## 1. Problem Statement

Two blockers prevented a public deployment:

1. **`_load_all_match_data()` read local JSON files** — the viz pipeline required raw match data at `/data/raw/matches/<id>.json` and `/data/raw/fotmob/<id>.json`. This is impossible on any cloud host. The app couldn't run stateless.
2. **No app layer** — `src/football_rag/app/main.py` didn't exist. The `app/__init__.py` imported a Gradio `demo` object that was never built. The Gradio approach was abandoned mid-phase (binary incompatibility between Gradio versions), leaving the app layer completely broken.

Additionally, `hf-deployment` and `space/hf-spaces-minimal` branches existed from a previous ChromaDB-era deploy attempt. These were stale dead code — completely wrong architecture (ChromaDB replaced by DuckDB VSS in Phase 2).

## 2. Approach

**MotherDuck migration** for `_load_all_match_data()`: replace all local JSON reads with three targeted MotherDuck queries:
- `silver_events WHERE match_id = ?` (whoscored ID)
- `silver_fotmob_shots JOIN match_mapping ON fotmob_match_id WHERE whoscored_match_id = ?`
- `match_mapping` for real team names

**Streamlit over Gradio**: Streamlit is HF Spaces' first-class framework. No binary compatibility issues. Single-page app: query textbox → `orchestrator.query()` → commentary or chart.

**Deploy architecture decided** (not yet implemented):
- `lakehouse.duckdb` (536MB, HNSW index) → HF Dataset repo via git-lfs
- MotherDuck → silver/gold tables (already stateless)
- `xT_grid.csv` (1KB) → stays in repo
- HF Spaces free tier hosts Streamlit, downloads lakehouse.duckdb on cold start

## 3. Key Technical Discoveries

### `silver_fotmob_shots.match_id` = fotmob_match_id (NOT whoscored)

This was non-obvious. The join must go through `match_mapping`:
```sql
SELECT s.*
FROM silver_fotmob_shots s
JOIN match_mapping m ON s.match_id = m.fotmob_match_id
WHERE m.whoscored_match_id = ?
```
Discovered by sampling: `SELECT DISTINCT match_id, home_team, away_team FROM silver_fotmob_shots LIMIT 3` returned fotmob IDs (e.g. `4815204`), not whoscored IDs (e.g. `1903733`).

### Column name mismatch: DB snake_case vs visualizers.py camelCase

`visualizers.py` was written against raw FotMob JSON which uses camelCase. The DB stores snake_case. Required explicit rename on load:
```python
shots_df = shots_df.rename(columns={
    "event_type": "eventType",
    "player_name": "playerName",
    "shot_type": "shotType",
    "is_on_target": "isOnTarget",
})
```
This must not be reverted. The rename lives in `viz_tools._load_all_match_data()` as the adapter layer between DB schema and visualizer API.

### `event_row_id AS id` alias required

`visualizers.calculate_player_defensive_positions()` runs `groupby().agg({'id': 'count'})`. The DB column is `event_row_id`. Without the alias in the SELECT, the defensive heatmap raises `KeyError: "Column(s) ['id'] do not exist"`. Fix: `SELECT *, event_row_id AS id FROM silver_events`.

### Dynamic fotmob team IDs

The shot map renderer needs `home_fotmob_id` and `away_fotmob_id`. These were previously hardcoded to `9791` and `6413` (one specific match). Fixed by extracting dynamically from the shots data:
```python
fotmob_ids = shots_df_tmp['team_id'].unique().tolist()
home_fotmob_id = fotmob_ids[0] if len(fotmob_ids) > 0 else None
away_fotmob_id = fotmob_ids[1] if len(fotmob_ids) > 1 else None
```

### Streamlit module cache

After editing `viz_tools.py`, the running Streamlit server cached the old module. Error appeared to persist despite the fix. Resolution: `Ctrl+C` and restart. Lesson: always restart Streamlit after editing backend modules, not just the UI file.

## 4. All 7 Viz Types Verified

Smoke-tested against `Fortuna Sittard vs Go Ahead Eagles` (match_id `1903733`):

| Viz Type | Status | Notes |
|---|---|---|
| `dashboard` | ✅ | 3x3 tactical report, all panels rendered |
| `passing_network` | ✅ | Home and away networks |
| `defensive_heatmap` | ✅ | Requires `event_row_id AS id` alias |
| `progressive_passes` | ✅ | xT-weighted passes |
| `shot_map` | ✅ | Requires dynamic fotmob team IDs |
| `xt_momentum` | ✅ | Match momentum over time |
| `match_stats` | ✅ | Summary stats bar chart |

## 5. Deploy Decision: HF Spaces over Modal

Modal is designed for serverless functions and GPU inference — not for persistent Streamlit web apps. Running Streamlit on Modal requires undocumented web endpoint hacks. HF Spaces has native Streamlit support (first-class template), 5GB file limit via git-lfs, and free tier that serves portfolio demos adequately (sleeps after 48h inactivity, wakes on request).

**The right split**: HF Spaces hosts the UI + data files. Modal gets added only when swapping to local Llama 3 inference (Phase 4).

## 6. Branch Cleanup

Deleted stale branches:
- `hf-deployment` — ChromaDB-era deploy attempts, 5 fixup commits trying to work around Mac/Linux binary incompatibility for ChromaDB. Superseded entirely by DuckDB VSS architecture.
- `feat/phase3b-streamlit-ui` — merged to `main` via PR #8.

Remote `space/hf-spaces-minimal` remains but points to dead ChromaDB code. Will be overwritten by `feat/hf-spaces-deploy` push.

## 7. v1.0 "Properly Done" Checklist

What "shipped" actually means for this project:

```
[ ] Public URL live (HF Spaces)
[ ] Cold start < 90s (lakehouse.duckdb downloads on wake)
[ ] Secrets configured (MOTHERDUCK_TOKEN, ANTHROPIC_API_KEY, HF_TOKEN)
[ ] README has live URL + screenshot
[ ] EDD runs in CI (not just locally)
```

When all five are true: "I built and shipped a production RAG system with a live public URL, evaluated with domain-specific metrics, backed by a real data pipeline." Interview-grade sentence.

## 8. Lessons Learned

- **Test column names at the adapter layer**: The DB schema and the library API don't have to match. The adapter function (`_load_all_match_data`) is the right place to reconcile them explicitly — not in `visualizers.py`.
- **Smoke test every viz type before shipping**: Found 3 bugs (camelCase columns, `id` alias, hardcoded fotmob IDs) that unit tests didn't catch because they hit different code paths. End-to-end smoke is irreplaceable.
- **Stale branches are noise**: `hf-deployment` had 5 commits all named `fix: ...` trying to patch a fundamentally broken architecture. Delete dead experiments when the approach is superseded — don't let them accumulate.
- **Deploy platform matters for DX**: Gradio binary compat issues → abandoned. ChromaDB Mac/Linux binary issues → 5 fixup commits. Streamlit + HF Spaces + MotherDuck avoids all of these — each component is stateless and platform-agnostic.
- **"Is it done?" = "Can a stranger use it?"**: Working locally is not done. The v1.0 checklist above is the bar.

## 9. Next Steps

1. **`feat/hf-spaces-deploy`** — wire `requirements.txt`, `app.py` HF entrypoint, startup download of `lakehouse.duckdb` from HF Dataset repo
2. **Upload `lakehouse.duckdb` to HF Dataset repo** via git-lfs
3. **Set HF Spaces secrets**: `MOTHERDUCK_TOKEN`, `ANTHROPIC_API_KEY`, `HF_TOKEN`
4. **EDD in CI** — add `pytest tests/test_edd.py --run-edd` step to GitHub Actions (after deploy confirmed working)
5. **Prompt `v4.0_tactical`** — post-deploy, tune LLM to interpret metrics tactically instead of reciting them
