# Phase 1 Completion Plan - Quick Reference

**Created**: 2026-02-14 Evening
**Status**: Ready to Execute Tomorrow
**Estimated Time**: ~3 hours total

---

## 🎯 The Problem (In 30 Seconds)

Your MVP (Gradio + ChromaDB) works perfectly with 99.4% faithfulness.

Your V2 (Dagster + dbt + DuckDB) has the infrastructure but **broken data pipeline**:
- ❌ Dagster creates simplified schema (17 columns)
- ❌ Gradio expects full schema (23 columns with `qualifiers`, `prog_pass`, etc.)
- ❌ dbt models have correct schema but never run (no profiles.yml)
- ❌ rag_pipeline.py queries ChromaDB (data is in DuckDB)

**Result**: Visualizations crash, LLM can't generate reports.

---

## ✅ The Solution: Hybrid Architecture (Option C)

**Dagster**: Orchestration + Scraping (Playwright)
**dbt**: Transformations (SQL logic, tests, docs)
**DuckDB VSS**: Storage (SQL tables + vector search)
**Gradio**: UI (unchanged, just point to DuckDB)

---

## 📋 5-Step Execution Plan

### Step 1: Wire up dbt (20 min)
```yaml
# Create ~/.dbt/profiles.yml
football_analytics:
  target: dev
  outputs:
    dev:
      type: duckdb
      path: data/lakehouse.duckdb
      threads: 4
```

**Tasks**:
1. Create profiles.yml (above)
2. Fix `dbt_project/models/sources.yml`: `database: memory` → `database: lakehouse`
3. Delete Dagster Silver/Gold assets (lines 70-228 in `orchestration/assets/duckdb_assets.py`)
4. Create new Dagster asset: `dbt_build` (runs `dbt run && dbt test`)

**Verify**: `uv run dbt run --select silver_events` succeeds

---

### Step 2: Enhance dbt Models (60 min)

**Verify `silver_events.sql` has all 23 columns**:
- ✅ `type_display_name` (already in model)
- ✅ `outcome_type_display_name` (already in model)
- ✅ `qualifiers` (already in model)
- ✅ `prog_pass` (already in model)
- ✅ `x_sb`, `y_sb` (already in model)

**Create `dbt_project/models/gold/gold_team_metrics.sql`**:
```sql
-- 38 Pre-Calculated Tactical Metrics (from MVP)
WITH match_stats AS (
    SELECT
        match_id,
        team_id,
        -- PPDA (Passes Allowed Per Defensive Action)
        ROUND(SUM(CASE WHEN event_type = 'Pass' THEN 1 ELSE 0 END)::DOUBLE /
              NULLIF(SUM(CASE WHEN event_type IN ('Tackle', 'Interception') THEN 1 ELSE 0 END), 0), 2) as ppda,

        -- Field Tilt (% of events in opponent half)
        ROUND(100.0 * SUM(CASE WHEN x > 50 THEN 1 ELSE 0 END) / COUNT(*), 1) as field_tilt,

        -- Progressive Passes (>= 9.11m threshold)
        SUM(CASE WHEN prog_pass >= 9.11 THEN 1 ELSE 0 END) as progressive_passes,

        -- xG, shots, goals (join with fotmob)
        -- Median position, compactness, etc.
        -- ... (all 38 metrics)
    FROM {{ ref('silver_events') }}
    GROUP BY match_id, team_id
)
SELECT * FROM match_stats
```

**Verify**: `uv run dbt test` passes

---

### Step 3: Migrate to DuckDB VSS (45 min)

**Create `scripts/generate_embeddings.py`**:
```python
import duckdb
from sentence_transformers import SentenceTransformer

# Load model (same as MVP)
model = SentenceTransformer('sentence-transformers/all-mpnet-base-v2')

# Connect to DuckDB
db = duckdb.connect('data/lakehouse.duckdb')

# Get match summaries
matches = db.execute("""
    SELECT match_id, home_team, away_team,
           -- Concatenate tactical metrics for embedding
           'Match: ' || home_team || ' vs ' || away_team ||
           ' | PPDA: ' || CAST(ppda AS VARCHAR) ||
           ' | Field Tilt: ' || CAST(field_tilt AS VARCHAR) || ...
           AS summary_text
    FROM gold_team_metrics
""").fetchall()

# Generate embeddings
embeddings = model.encode([m[3] for m in matches])

# Store in DuckDB
db.execute("INSTALL vss; LOAD vss;")
db.execute("""
    CREATE TABLE gold_match_embeddings (
        match_id VARCHAR,
        embedding FLOAT[768],
        summary_text TEXT
    )
""")

for (match_id, _, _, text), emb in zip(matches, embeddings):
    db.execute(
        "INSERT INTO gold_match_embeddings VALUES (?, ?, ?)",
        [match_id, emb.tolist(), text]
    )

# Create HNSW index
db.execute("""
    CREATE INDEX match_vss_idx ON gold_match_embeddings
    USING HNSW (embedding)
""")
```

**Update `src/football_rag/models/rag_pipeline.py`**:
```python
# OLD (ChromaDB)
self.client = chromadb.PersistentClient(path=str(db_path))
results = self.client.query(query_embeddings=[query_emb], n_results=5)

# NEW (DuckDB VSS)
self.db = duckdb.connect('data/lakehouse.duckdb')
query_emb = self.model.encode(query)
results = self.db.execute("""
    SELECT match_id, summary_text,
           array_distance(embedding, ?::FLOAT[768]) as distance
    FROM gold_match_embeddings
    ORDER BY distance
    LIMIT 5
""", [query_emb.tolist()]).fetchall()
```

**Verify**: Test vector search works

---

### Step 4: Reconnect Gradio (30 min)

**Update `src/football_rag/visualizers.py`**:
```python
# OLD (raw JSON files)
with open(f'data/raw/whoscored/{match_id}.json') as f:
    data = json.load(f)
df_events = pd.DataFrame(data['events'])

# NEW (DuckDB)
db = duckdb.connect('data/lakehouse.duckdb')
df_events = db.execute("""
    SELECT * FROM silver_events WHERE match_id = ?
""", [match_id]).df()
```

**Test all 6 visualization types**:
1. Dashboard
2. Passing Network
3. Defensive Heatmap
4. Progressive Passes
5. Shot Map
6. xT Momentum

**Verify**: `uv run python -m football_rag.app` works

---

### Step 5: End-to-End Verification (30 min)

**Test Queries**:
1. "Show dashboard for PSV vs Ajax" → Should render matplotlib plot
2. "What was Feyenoord's pressing strategy?" → Should return LLM analysis

**Run Evaluation**:
```bash
uv run python tests/evaluate_pipeline.py
```

**Expected Results** (match MVP benchmarks):
- Retrieval Accuracy: 100%
- Faithfulness: 99.4%
- Tactical Insight: 95%

---

## ✅ Success Criteria (9 Checkpoints)

- [ ] dbt connected to DuckDB (`dbt run` succeeds)
- [ ] `silver_events` has 23 columns (not 17)
- [ ] Gold layer has 38 tactical metrics
- [ ] DuckDB VSS enabled with match embeddings
- [ ] `rag_pipeline.py` queries DuckDB (not ChromaDB)
- [ ] `visualizers.py` reads from DuckDB (not raw JSON)
- [ ] Gradio query "Show dashboard for PSV vs Ajax" works
- [ ] Gradio query "What was Feyenoord's pressing?" works
- [ ] Evaluation metrics match MVP (99.4% faithfulness)

---

## 📂 Files to Create/Modify

### Create:
- `~/.dbt/profiles.yml`
- `dbt_project/models/gold/gold_team_metrics.sql`
- `scripts/generate_embeddings.py`
- `orchestration/assets/dbt_asset.py`

### Modify:
- `dbt_project/models/sources.yml`
- `dbt_project/models/silver/silver_events.sql` (verify)
- `src/football_rag/models/rag_pipeline.py`
- `src/football_rag/visualizers.py`
- `src/football_rag/viz_tools.py`

### Delete:
- `orchestration/assets/duckdb_assets.py` lines 70-228

---

## 🎬 When You Resume Tomorrow

**Say to Claude**:
> "Summarize where we left off with Phase 1"

**Claude will respond**:
1. Phase 1 NOT complete - gap between MVP (working) and V2 (broken)
2. Root cause: Two parallel pipelines (Dagster simplified vs dbt full schema)
3. Solution: Option C (Hybrid) - 5-step plan documented
4. Estimate: ~3 hours to complete
5. Goal: Make V2 work like MVP (99.4% faithfulness)

**Then**:
1. Enter Plan Mode (Shift+Tab twice)
2. Review this plan
3. Get approval
4. Execute steps 1-5 in order

---

## 💡 Key Decisions Made

1. **Hybrid Architecture** - Dagster orchestrates, dbt transforms, DuckDB stores
2. **Migrate ChromaDB → DuckDB VSS** - Simpler stack, hybrid queries
3. **Keep 38 Pre-Calc Metrics** - LLMs need aggregates, not raw events
4. **Fix Schema in dbt** - dbt already has right schema, just wire it up

---

**Ready to Execute**: 2026-02-15 Morning
**Full Details**: See SCRATCHPAD.md + docs/engineering_diary/2026-02-14-phase1-diagnosis.md
