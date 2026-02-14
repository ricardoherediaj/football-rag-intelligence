# Engineering Diary: Phase 1 Data Pipeline Diagnosis

**Date**: 2026-02-14 (Evening Session)
**Author**: Ricardo Heredia + Claude Sonnet 4.5
**Branch**: `feat/scraping-strategies`
**Session Duration**: ~2 hours (analysis + documentation)

---

## 🎯 Session Objective

**Original Question**: "Where did I leave off? What did I accomplish in recent phases?"

**Discovery**: Phase 1 (Data Foundation) is **NOT complete** as initially thought. Found critical gap between MVP (working Gradio app) and V2 (broken data pipeline).

---

## 🔍 What We Discovered

### The Confusion
User thought Phase 1 was done because:
- ✅ Scraping works (188/190 matches, 98.9% parity)
- ✅ Dagster orchestration works (379 matches in DuckDB)
- ✅ DuckDB Medallion pipeline works (Bronze/Silver/Gold tables created)
- ✅ dbt models exist (silver_events.sql, schema.yml with 18 tests)

But when asked: *"There are errors in the silver layer. The current data isn't processed ready as it was with the Gradio MVP."*

### The Root Cause: Two Parallel Pipelines

We have **TWO disconnected systems** that don't talk to each other:

#### **System 1: MVP (HuggingFace Spaces) - WORKING** ✅
```
Raw JSON → Pydantic validation → matches_gold.json → ChromaDB (2 chunks × 108 matches)
    ↓
RAG Pipeline (LlamaIndex) → Gradio UI
    ↓
6 Visualization Types + LLM Text Analysis
```

**Key Features**:
- 38 pre-calculated tactical metrics (PPDA, field tilt, progressive passes, xG, etc.)
- Schema optimized for visualizers (has `qualifiers`, `prog_pass`, `x_sb`, `y_sb`)
- Evaluation: 100% retrieval, 99.4% faithfulness, 95% tactical insight
- Cost: <$0.01 per 100 queries

#### **System 2: V2 (Local Dev) - BROKEN** ❌
```
Playwright Scrapers → MinIO → Dagster Bronze → Dagster Silver/Gold
    ↓
DuckDB lakehouse.duckdb (485 MB, 279K events)
    ↓
dbt models (created but NOT connected)
    ↓
Gradio (can't read data - still expects ChromaDB)
```

**Problems**:
1. **Schema Mismatch**: Dagster creates 17 columns, Gradio needs 23 columns
2. **dbt Disconnected**: No `~/.dbt/profiles.yml`, models can't read `lakehouse.duckdb`
3. **Missing Metrics**: No 38 pre-calculated metrics (needed for LLM grounding)
4. **ChromaDB vs DuckDB**: `rag_pipeline.py` still queries ChromaDB, but data is in DuckDB

---

## 📊 Detailed Analysis

### Schema Comparison: Dagster vs dbt vs Gradio

| Column | Dagster (v2) | dbt Model | Gradio Needs | Missing? |
|--------|--------------|-----------|--------------|----------|
| `event_type` | ✅ | ❌ (uses `type_display_name`) | ❌ | Rename |
| `outcome` | ✅ | ❌ (uses `outcome_type_display_name`) | ❌ | Rename |
| `type_display_name` | ❌ | ✅ | ✅ | **YES** |
| `outcome_type_display_name` | ❌ | ✅ | ✅ | **YES** |
| `qualifiers` | ❌ | ✅ | ✅ | **YES** |
| `prog_pass` | ❌ | ✅ | ✅ | **YES** |
| `x_sb` | ❌ | ✅ | ✅ | **YES** |
| `y_sb` | ❌ | ✅ | ✅ | **YES** |

**Impact**: Gradio's `visualizers.py` line 892 expects:
```python
(~df_events['qualifiers'].astype(str).str.contains('CornerTaken|Freekick', na=False)) &
(df_events['prog_pass'] >= 9.11)  # Progressive pass threshold
```

These columns don't exist in Dagster's `silver_events` → **Visualizations will crash**.

### Why Two Pipelines?

**Historical Context**:
1. **MVP Development** (Sep-Dec 2025):
   - Built Gradio app with ChromaDB
   - Created `matches_gold.json` with 38 pre-calc metrics
   - Optimized schema for visualizers
   - Deployed to HuggingFace Spaces
   - **Status**: Production, working perfectly

2. **V2 Migration** (Jan-Feb 2026):
   - Goal: Scale to 2000+ matches with production data quality
   - Built Playwright scrapers (replaced Selenium)
   - Set up Dagster orchestration
   - Created DuckDB Medallion pipeline
   - Created dbt models (but never wired them up)
   - **Status**: Infrastructure ready, data pipeline broken

3. **The Gap**:
   - Dagster assets (`duckdb_assets.py`) implement **simplified schema** (17 columns)
   - dbt models (`silver_events.sql`) implement **full schema** (23 columns)
   - dbt models **never run** (no profiles.yml, no connection to DuckDB)
   - Result: Dagster creates tables, but Gradio can't use them

---

## 🏗️ The Solution: Option C (Hybrid Architecture)

After evaluating 3 options (Dagster-only, dbt-only, Hybrid), we chose **Hybrid**:

### Architecture Decision
```
┌─────────────────────────────────────────┐
│            DAGSTER                      │
│  (Orchestration + Scraping)             │
│                                         │
│  ┌─────────────────┐                   │
│  │ Playwright      │ ─────────┐        │
│  │ Scrapers        │          │        │
│  └─────────────────┘          ▼        │
│                          raw_matches    │
│                          _bronze        │
│                          (MinIO→DuckDB) │
│                                │        │
│                                ▼        │
│  ┌─────────────────┐     ┌─────────┐   │
│  │ dbt run         │ ◀── │ Trigger │   │
│  │ (Silver/Gold)   │     └─────────┘   │
│  └─────────────────┘                   │
│         │                              │
│         ▼                              │
│  DuckDB VSS (Vector Search)            │
│    ↓                                   │
│  Gradio UI                             │
└─────────────────────────────────────────┘
```

### Why Hybrid?

**Why NOT Dagster-only?**
- User already invested 134 lines of dbt documentation + 18 tests
- dbt gives column-level tests, documentation generation, incremental models (future)
- dbt SQL is cleaner than Python SQL strings in Dagster assets

**Why NOT dbt-only?**
- Scrapers live in Dagster naturally (Playwright, not SQL)
- Dagster provides scheduling, sensors, asset metadata tracking
- dbt can't orchestrate end-to-end pipeline (just transformations)

**Why Hybrid?**
- Clean separation: Dagster = scraping + orchestration, dbt = transformations + testing
- Leverage both tools' strengths
- Future-proof for Phase 2 (RAG engine) and multi-league scaling

### ChromaDB → DuckDB VSS Migration

**Decision**: Replace ChromaDB with **DuckDB VSS** (Vector Similarity Search extension)

**Why?**
- **Simpler Stack**: One database for SQL + vectors (no separate ChromaDB container)
- **Hybrid Queries**: `SELECT * FROM matches WHERE league='Eredivisie' ORDER BY vector_distance(...)`
- **Aligns with Vision**: ARCHITECTURE.md mentions DuckDB VSS as future direction
- **Performance**: Native DuckDB performance, no network calls to external vector DB

**Migration Path**:
1. Install DuckDB VSS extension
2. Generate embeddings for match summaries (use `sentence-transformers/all-mpnet-base-v2` like MVP)
3. Store embeddings in Gold layer with HNSW index
4. Update `rag_pipeline.py` to query DuckDB instead of ChromaDB

---

## 📋 Phase 1 Completion Roadmap

### Total Estimated Time: ~3 hours

#### Step 1: Wire up dbt (20 minutes)
**Tasks**:
- Create `~/.dbt/profiles.yml`:
  ```yaml
  football_analytics:
    target: dev
    outputs:
      dev:
        type: duckdb
        path: data/lakehouse.duckdb
        threads: 4
  ```
- Update `dbt_project/models/sources.yml`: Change `database: memory` → `database: lakehouse`
- Delete Dagster's `events_silver`, `silver_fotmob`, `gold_*` assets
- Create single Dagster asset: `dbt_build` that runs `dbt run && dbt test`

**Verification**:
```bash
cd dbt_project
uv run dbt run --select silver_events
# Should succeed and create silver_events table
```

#### Step 2: Enhance dbt Models (60 minutes)
**Tasks**:
- Add missing 6 columns to `silver_events.sql`:
  - `type_display_name` (already exists in model, just verify)
  - `outcome_type_display_name` (already exists)
  - `qualifiers` (already exists)
  - `prog_pass` (already exists)
  - `x_sb` (already exists)
  - `y_sb` (already exists)
- Create `gold_team_metrics.sql` with 38 pre-calculated metrics:
  - PPDA (passes allowed per defensive action)
  - Field tilt (attack vs defense positioning)
  - Progressive passes (distance toward goal)
  - xG aggregations
  - Median position, compactness, etc.
- Add tests to `schema.yml`

**Verification**:
```bash
uv run dbt test
# All 18+ tests should pass
```

#### Step 3: Migrate to DuckDB VSS (45 minutes)
**Tasks**:
- Install DuckDB VSS extension:
  ```sql
  INSTALL vss;
  LOAD vss;
  ```
- Create embedding generation script:
  - Use `sentence-transformers/all-mpnet-base-v2`
  - Embed match summaries (tactical metrics + team names + score)
  - Store in `gold_match_embeddings` table
- Create HNSW index:
  ```sql
  CREATE INDEX match_vss_idx ON gold_match_embeddings
  USING HNSW (embedding);
  ```
- Update `src/football_rag/models/rag_pipeline.py`:
  - Replace `chromadb.PersistentClient` with DuckDB connection
  - Update retrieval logic to query DuckDB VSS

**Verification**:
```python
# Test vector search
db = duckdb.connect('data/lakehouse.duckdb')
result = db.execute("""
  SELECT match_id, home_team, away_team,
         array_distance(embedding, [test_vector]) as distance
  FROM gold_match_embeddings
  ORDER BY distance LIMIT 5
""").fetchall()
```

#### Step 4: Reconnect Gradio (30 minutes)
**Tasks**:
- Update `src/football_rag/visualizers.py`:
  - Replace raw JSON file loading with DuckDB queries
  - Ensure it reads from `silver_events` table (now has full schema)
- Update `src/football_rag/viz_tools.py`:
  - Point to DuckDB instead of data/raw/ directory
- Test all 6 visualization types:
  - Dashboard, Passing Network, Defensive Heatmap, Progressive Passes, Shot Map, xT Momentum

**Verification**:
```bash
# Run Gradio app
uv run python -m football_rag.app

# Test queries:
# 1. "Show dashboard for PSV vs Ajax"
# 2. "Show passing network for Feyenoord"
# 3. "What was Heracles' pressing strategy against AZ?"
```

#### Step 5: End-to-End Verification (30 minutes)
**Tasks**:
- Full pipeline test: Scrape → MinIO → Bronze → dbt Silver/Gold → DuckDB VSS → Gradio
- Run evaluation harness from MVP:
  ```bash
  uv run python tests/evaluate_pipeline.py
  ```
- Verify metrics meet MVP benchmarks:
  - Retrieval Accuracy: 100%
  - Faithfulness: 99.4%
  - Tactical Insight: 95%

---

## 🎯 Success Criteria

Phase 1 is **complete** when:

1. ✅ dbt connected to DuckDB (`dbt run` succeeds)
2. ✅ `silver_events` has 23 columns (not 17)
3. ✅ Gold layer has 38 tactical metrics
4. ✅ DuckDB VSS enabled with match embeddings
5. ✅ `rag_pipeline.py` queries DuckDB (not ChromaDB)
6. ✅ `visualizers.py` reads from DuckDB (not raw JSON)
7. ✅ Gradio query "Show dashboard for PSV vs Ajax" works
8. ✅ Gradio query "What was Feyenoord's pressing?" works
9. ✅ Evaluation metrics match MVP (99.4% faithfulness)

---

## 📂 Files to Modify Tomorrow

### Create:
- `~/.dbt/profiles.yml` (dbt connection config)
- `dbt_project/models/gold/gold_team_metrics.sql` (38 pre-calc metrics)
- `scripts/generate_embeddings.py` (DuckDB VSS embedding pipeline)
- `orchestration/assets/dbt_asset.py` (Dagster calls dbt run)

### Modify:
- `dbt_project/models/sources.yml` (fix database path)
- `dbt_project/models/silver/silver_events.sql` (verify all 23 columns)
- `src/football_rag/models/rag_pipeline.py` (ChromaDB → DuckDB VSS)
- `src/football_rag/visualizers.py` (raw JSON → DuckDB queries)
- `src/football_rag/viz_tools.py` (data source update)

### Delete:
- `orchestration/assets/duckdb_assets.py` lines 70-228 (replace with dbt_build asset)

---

## 💡 Key Insights

### What Went Right
- **Infrastructure Solid**: Playwright scrapers, Dagster orchestration, DuckDB storage all work
- **dbt Groundwork Done**: Models already exist with correct schema (just not connected)
- **MVP Proven**: 99.4% faithfulness benchmark proves the architecture works

### What Went Wrong
- **Lost in Translation**: MVP schema → V2 simplified schema lost critical columns
- **Two Pipelines**: Dagster Python SQL vs dbt SQL models created parallel implementations
- **Assumption Error**: Thought Phase 1 was done because infrastructure worked (but data quality wasn't there)

### Lessons Learned
- **Always verify end-to-end**: Infrastructure working ≠ pipeline complete
- **Schema compatibility critical**: Downstream consumers (Gradio) dictate schema requirements
- **dbt investment pays off**: 134 lines of docs + 18 tests caught this issue early

---

## 🚀 Next Steps (Tomorrow Session)

1. **Enter Plan Mode** (Shift+Tab twice)
   - User will ask for summary when returning
   - Present clear 5-step roadmap
   - Get approval before starting

2. **Execute Phase 1 Completion** (~3 hours)
   - Wire up dbt → Enhance models → Migrate VSS → Reconnect Gradio → Verify

3. **Merge to Main**
   - Create PR documenting Phase 1 completion
   - Update CHANGELOG.md with full migration story
   - Close `feat/scraping-strategies` branch

4. **Start Phase 2 Planning**
   - RAG Engine: SQL retrieval + Vector retrieval + Router
   - Modal inference setup
   - Opik observability integration

---

## 📚 References

**Documents Read**:
- README.md (MVP architecture)
- docs/architecture/overview.md (design decisions)
- docs/architecture/DATA_ARCHITECTURE_EXPLAINED.md (Medallion + VSS)
- docs/architecture/V2_MIGRATION_STATUS.md (V2 progress)

**Code Analyzed**:
- dbt_project/models/silver/silver_events.sql (full schema)
- orchestration/assets/duckdb_assets.py (simplified schema)
- src/football_rag/visualizers.py (schema requirements)
- src/football_rag/models/rag_pipeline.py (ChromaDB queries)

**Database Verified**:
- data/lakehouse.duckdb (485 MB, 5 tables, 279K events)

---

## 🎬 Closing Notes

This session transformed confusion into clarity. What seemed like "Phase 1 complete" was actually "Phase 1 infrastructure built, data pipeline broken." Now we have:

1. **Clear diagnosis**: Two parallel pipelines, schema mismatch
2. **Concrete plan**: Option C (Hybrid), 3-hour roadmap
3. **Success criteria**: 9 checkpoints to verify completion
4. **Full documentation**: SCRATCHPAD.md + this diary for tomorrow's session

Tomorrow: **Execute and close Phase 1 properly.** Then we can confidently move to Phase 2 (RAG Engine) knowing our data foundation is rock solid.

---

**Session End**: 2026-02-14 23:50 CET
**Status**: Documented, ready to execute tomorrow
