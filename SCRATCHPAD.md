# Session Scratchpad

**Purpose**: Persistent session state that survives context clears. Update this file throughout your work session. When context gets bloated, `/clear` and reload only this file + CLAUDE.md.

**Session Started**: 2026-02-14 (Evening)
**Current Branch**: `feat/scraping-strategies`

---

## 📋 Current Task

**Working On**: Phase 1 Data Pipeline Completion - MVP to V2 Migration

**Goal**: Fix the disconnect between MVP (Gradio + ChromaDB) and V2 (Dagster + dbt + DuckDB) to enable automated post-match reports with production-grade data quality.

**Completed Today (2026-02-14)**:
- ✅ Diagnosed Phase 1 data pipeline status (NOT complete as thought)
- ✅ Identified root cause: TWO parallel pipelines (Dagster simplified schema vs dbt full schema)
- ✅ Mapped MVP architecture (ChromaDB, 38 pre-calc metrics, Gradio visualizers)
- ✅ Confirmed V2 infrastructure works (Dagster: 379 matches, 279K events in DuckDB)
- ✅ Identified schema mismatch: Gradio expects `qualifiers`, `prog_pass`, `x_sb`, `y_sb` (missing in Dagster)
- ✅ Identified dbt disconnected: No profiles.yml, models can't read DuckDB
- ✅ Documented comprehensive analysis in SCRATCHPAD.md + engineering diary
- ✅ Decided on Option C (Hybrid): Dagster orchestrates, dbt transforms, DuckDB VSS replaces ChromaDB

**Next Steps (When Resuming Tomorrow)**:
1. [ ] **Wire up dbt** (20 min) - Create profiles.yml, fix sources.yml, replace Dagster Silver/Gold with dbt
2. [ ] **Enhance dbt models** (60 min) - Add missing 6 columns, add 38 tactical metrics to Gold layer
3. [ ] **Migrate to DuckDB VSS** (45 min) - Set up vector extension, create embedding pipeline, update rag_pipeline.py
4. [ ] **Reconnect Gradio** (30 min) - Update visualizers.py to read DuckDB, test all 6 viz types
5. [ ] **End-to-end verification** - Test "Show dashboard" + "What was pressing strategy" queries

---

## 🎯 Active Tasks (Phase 1 Completion)

### **CRITICAL: Fix Data Pipeline Before Phase 2 (RAG Engine)**

**Context**: You have TWO disconnected systems:
1. MVP (Working): Gradio + ChromaDB + 38 pre-calc metrics → Automated reports
2. V2 (Broken): Dagster + dbt (disconnected) + DuckDB → Missing columns, can't serve Gradio

**Goal**: Make V2 work like MVP (but better data quality + scalability)

### High Priority (Complete Phase 1)
- [ ] **Wire up dbt to DuckDB** - Create ~/.dbt/profiles.yml pointing to data/lakehouse.duckdb
- [ ] **Fix schema mismatch** - Add 6 missing columns to silver_events (qualifiers, prog_pass, x_sb, y_sb, type_display_name, outcome_type_display_name)
- [ ] **Add 38 tactical metrics** - Create Gold layer with PPDA, field tilt, progressive passes, xG aggregations
- [ ] **Migrate ChromaDB → DuckDB VSS** - Set up vector extension, create embeddings, update rag_pipeline.py
- [ ] **Reconnect Gradio visualizers** - Update visualizers.py to read from DuckDB instead of raw JSON

### Medium Priority (Post Phase 1)
- [ ] Add MCP server configuration (DuckDB, GitHub)
- [ ] Create data validation subagent (read-only DuckDB queries)
- [ ] Create `/materialize` skill for Dagster assets
- [ ] Set up SessionStart hook for automatic SCRATCHPAD.md loading

### Low Priority / Future (Phase 2+)
- [ ] Start Phase 2: RAG Engine (SQL retrieval + Vector retrieval + Router)
- [ ] Explore Opik MCP server for LLM observability
- [ ] Multi-league expansion (Championship, Jupiler Pro, Brasileirão)
- [ ] MotherDuck migration for cloud serving

---

## 💡 Decisions Made This Session

**Decision 1** (CRITICAL): Option C - Hybrid Architecture
- **Rationale**: Best of both worlds - Dagster orchestrates, dbt transforms, single DuckDB for SQL + vectors
- **Implementation**:
  - Dagster: Scraping (Playwright) + Bronze loading (MinIO → DuckDB)
  - dbt: Silver/Gold transformations (SQL logic, tests, docs)
  - DuckDB VSS: Replace ChromaDB for vector search (hybrid SQL+semantic queries)
- **Impact**: Clean separation of concerns, leverage both tools' strengths, future-proof for multi-league scaling
- **Why NOT Dagster-only?** You already invested 134 lines dbt docs + 18 tests. dbt gives column-level tests, documentation as code, incremental models (future)
- **Why NOT ChromaDB?** DuckDB VSS enables hybrid queries ("Find similar matches WHERE league = 'Eredivisie'"), one less system to maintain

**Decision 2**: Migrate ChromaDB → DuckDB VSS
- **Rationale**: Simplifies stack (one database for SQL + vectors), enables hybrid search, aligns with ARCHITECTURE.md vision
- **Implementation**:
  - Install DuckDB VSS extension
  - Generate embeddings for match summaries (sentence-transformers/all-mpnet-base-v2)
  - Store in Gold layer with HNSW index
  - Update rag_pipeline.py to query DuckDB instead of ChromaDB
- **Impact**: Future-proof for Phase 2 RAG engine, enables "Find matches with high pressing AND similar to Feyenoord" queries

**Decision 3**: Keep 38 Pre-Calculated Metrics from MVP
- **Rationale**: LLMs are bad at calculating aggregates from 279K event rows. Need pre-calc metrics for fast, accurate analysis
- **Implementation**:
  - Gold layer dbt models calculate: PPDA, field tilt, progressive passes, xG, median position, compactness, etc.
  - Store in gold_team_metrics table
  - Embed summaries for semantic search
- **Impact**: Maintains MVP quality (99.4% faithfulness) while adding dbt testing framework

**Decision 4**: Fix Schema Mismatch in dbt (Not Dagster)
- **Rationale**: Gradio visualizers expect full schema. dbt already has the right schema defined, just not running
- **Implementation**: Wire up dbt, add missing 6 columns (qualifiers, prog_pass, x_sb, y_sb, type_display_name, outcome_type_display_name)
- **Impact**: Visualizers work immediately after dbt runs, no need to update visualizers.py code

---

## 🚧 Blockers / Questions

**Blocker 1**: Phase 1 NOT complete (discovered tonight)
- **Issue**: Data pipeline has schema mismatch between Dagster (simplified) and Gradio (expects full MVP schema)
- **Root Cause**: TWO parallel pipelines that don't talk to each other (Dagster Python SQL vs dbt SQL models)
- **Resolution**: Implement Option C (Hybrid) - wire up dbt, replace Dagster Silver/Gold, add missing columns
- **Status**: Documented, ready to implement tomorrow

**Blocker 2**: dbt not connected to DuckDB
- **Issue**: No profiles.yml, sources.yml points to wrong database (memory vs lakehouse)
- **Resolution**: Create ~/.dbt/profiles.yml, fix sources.yml, replace Dagster assets with dbt_build
- **Status**: Clear steps defined, ~20 min fix

**Question 1 (ANSWERED)**: dbt vs Dagster-only?
- **Answer**: Hybrid (Option C) - dbt for transformations, Dagster for orchestration
- **Why**: You already invested 134 lines dbt docs + 18 tests. dbt adds column-level testing, docs generation, incremental models

**Question 2 (ANSWERED)**: ChromaDB vs DuckDB VSS?
- **Answer**: Migrate to DuckDB VSS
- **Why**: Hybrid search, simpler stack, aligns with architecture vision, enables "Find X WHERE Y" queries

---

## 📝 Notes / Discoveries

**Note 1**: MVP Architecture (What Worked)
- **Gradio + ChromaDB**: 108 matches, 2 chunks per match (summary + tactical metrics)
- **38 Pre-Calc Metrics**: PPDA, field tilt, progressive passes, xG, median position, compactness, etc.
- **Golden Dataset ETL**: Raw JSON → Pydantic validation → matches_gold.json → ChromaDB
- **Evaluation**: 100% retrieval accuracy, 99.4% faithfulness, 95% tactical insight
- **Cost**: <$0.01 per 100 queries (Claude Haiku), visualizations $0 (matplotlib)

**Note 2**: V2 Current State (What's Built)
- **Scraping**: Playwright scrapers (188/190 matches, 98.9% parity), stored in MinIO
- **Dagster**: 379 matches loaded, 279K events in DuckDB, orchestration working
- **DuckDB**: lakehouse.duckdb (485 MB), Bronze/Silver/Gold tables created
- **dbt**: Models created (63 lines SQL, 134 lines docs, 18 tests) but NOT connected

**Note 3**: The Gap (What's Broken)
- **Schema Mismatch**: Dagster creates 17 columns, Gradio needs 23 columns (missing qualifiers, prog_pass, x_sb, y_sb, etc.)
- **dbt Disconnected**: No profiles.yml, can't read lakehouse.duckdb, models never run
- **ChromaDB vs DuckDB**: rag_pipeline.py still queries ChromaDB, but data is in DuckDB
- **Visualizers Broken**: visualizers.py expects MVP schema (qualifiers, prog_pass) that doesn't exist in Dagster's silver_events

**Note 4**: Phase 1 Completion Roadmap
1. Wire up dbt (20 min): profiles.yml, sources.yml, replace Dagster Silver/Gold
2. Enhance dbt models (60 min): Add 6 missing columns, add 38 tactical metrics
3. Migrate to DuckDB VSS (45 min): Vector extension, embeddings, update rag_pipeline.py
4. Reconnect Gradio (30 min): Update visualizers.py, test end-to-end
**Total: ~3 hours to complete Phase 1 properly**

**Note 5**: Why This Matters for Phase 2 (RAG Engine)
- Can't build RAG engine without clean, tested data pipeline
- Need 38 pre-calc metrics for LLM grounding (prevents hallucinations)
- Need proper schema for visualizations (6 types: dashboard, passing network, heatmaps, shot maps, etc.)
- DuckDB VSS enables hybrid RAG (SQL retrieval for stats + vector search for semantic queries)

---

## 🔗 Related Work

**PRs**:
- None in progress (working on local optimization)

**Issues**:
- None currently blocking

**Documentation**:
- Expert playbook: https://x.com/thread (summarized in CLAUDE.md refactor)
- GSD methodology: Atomic git commits, XML task structure, multi-agent orchestration

---

## 📊 Metrics / Verification

**Data Pipeline Status**:
- Scrapers: ✅ 188/190 matches (98.9% parity), 379 files in MinIO
- DuckDB: ✅ 485 MB lakehouse.duckdb, 279,104 events in silver_events
- dbt: ✅ Wired to DuckDB (profiles.yml created)
- Schema: ✅ 23 columns in silver_events (MVP parity)
- Team Metrics: ⚠️ 24/24 metrics created, xG=0 (needs match_mapping.json integration)
- Match Mapping: ✅ `data/match_mapping.json` exists (108 matches mapped WhoScored ↔ FotMob)
- ChromaDB: ❌ rag_pipeline.py still queries ChromaDB (data is in DuckDB)
- Gradio: ❌ Can't generate reports (data source disconnected)

**Critical Discovery (2026-02-15)** - xG Values Fix:
- **Problem**: WhoScored match_id (1903733) ≠ FotMob match_id (4815204), team IDs also different
- **Root Cause**: Assumed failure too early, didn't search codebase for existing solutions
- **Solution Found**: MVP already solved this with `scripts/create_match_mapping.py` + `data/match_mapping.json`
- **Implementation**: Loaded mapping into DuckDB, updated `silver_team_metrics.sql` xG join
- **Result**: ✅ xG values now working (57.1% teams have xG > 0, realistic values like 2.34, 1.17)
- **Lesson**: ALWAYS search `/scripts` and `/data` for existing solutions before implementing new ones

**MVP Quality Benchmarks (Target for V2)**:
- Retrieval Accuracy: 100% (metadata filtering)
- Faithfulness: 99.4% (Pydantic validation + ground truth)
- Tactical Insight: 95.0% (LLM-as-a-Judge)
- Cost: <$0.01 per 100 queries (Claude Haiku)
- Rebuild Speed: 18 seconds for 108 matches

**Phase 1 Completion Checklist**:
- [ ] dbt wired to DuckDB (profiles.yml created)
- [ ] dbt models run successfully (dbt run passes)
- [ ] Schema complete (23 columns in silver_events, not 17)
- [ ] 38 tactical metrics in Gold layer
- [ ] DuckDB VSS set up (vector extension + embeddings)
- [ ] rag_pipeline.py queries DuckDB (not ChromaDB)
- [ ] visualizers.py reads DuckDB (not raw JSON)
- [ ] End-to-end test: "Show dashboard for PSV vs Ajax" works
- [ ] End-to-end test: "What was Feyenoord's pressing?" works

---

## 🗓️ Next Session Handoff (Tomorrow Morning)

**Quick Summary Request from User**:
> "Im going to sleep and come back tomorrow to tackle everything. Keep in mind I'll ask you to summarize it again just to see where we left off and go forward from there"

**What to Say When User Returns**:
1. "Phase 1 NOT complete - discovered gap between MVP (working) and V2 (broken)"
2. "Root cause: TWO parallel pipelines (Dagster simplified schema vs dbt full schema)"
3. "Solution: Option C (Hybrid) - wire up dbt, add missing columns, migrate ChromaDB → DuckDB VSS"
4. "Estimated 3 hours to fix: dbt setup (20 min) + schema fix (60 min) + VSS migration (45 min) + Gradio reconnect (30 min)"
5. "Goal: Make V2 work like MVP (99.4% faithfulness, automated reports) but with better data quality"

**Context to Preserve**:
- MVP Architecture: Gradio + ChromaDB + 38 pre-calc metrics → 100% retrieval, 99.4% faithfulness
- V2 Infrastructure: Dagster (379 matches loaded) + DuckDB (279K events) + dbt (disconnected)
- The Gap: Schema mismatch (missing 6 columns), dbt not wired up, ChromaDB vs DuckDB disconnect
- The Plan: Hybrid architecture (Dagster orchestrates, dbt transforms, DuckDB VSS for vectors)
- Branch: feat/scraping-strategies (misleading name - Phase 1 completion, not new scraping)

**Files Created/Updated**:
- SCRATCHPAD.md: Full session state documented
- Engineering diary: To be created tomorrow (2026-02-14-phase1-diagnosis.md)

**Don't Reload Tomorrow** (unless needed):
- ARCHITECTURE.md (already aligned with DuckDB VSS vision)
- PATTERNS.md (coding patterns stable)
- README.md (MVP docs, context established)
- Full git history (recent commits known)

**Priority Tomorrow**:
1. **Enter Plan Mode** for Phase 1 completion (Shift+Tab twice)
2. Create detailed plan for dbt setup + schema fix + VSS migration
3. Get user approval before starting implementation
4. Execute in order: dbt → schema → VSS → Gradio → verify

---

## 🎯 Key Files Referenced This Session

**Documentation Read**:
- README.md: MVP architecture (Gradio + ChromaDB + 38 metrics)
- docs/architecture/overview.md: MVP design decisions
- docs/architecture/DATA_ARCHITECTURE_EXPLAINED.md: Medallion + VSS rationale
- docs/architecture/V2_MIGRATION_STATUS.md: V2 progress (scrapers + Dagster done)

**Code Analyzed**:
- dbt_project/models/silver/silver_events.sql: Full schema (63 lines, has qualifiers/prog_pass)
- dbt_project/models/silver/schema.yml: 134 lines docs, 18 tests
- orchestration/assets/duckdb_assets.py: Dagster simplified schema (17 columns)
- src/football_rag/visualizers.py: Expects qualifiers, prog_pass, x_sb, y_sb
- src/football_rag/models/rag_pipeline.py: Still queries ChromaDB (needs DuckDB update)

**Database Verified**:
- data/lakehouse.duckdb: 485 MB, 5 tables (bronze_matches, silver_events, silver_fotmob_shots, gold_match_summary, gold_player_stats)
- silver_events: 279,104 rows, but only 17 columns (missing 6 from MVP schema)

---

**Last Updated**: 2026-02-14 23:45 CET (Evening session, comprehensive Phase 1 diagnosis completed)
