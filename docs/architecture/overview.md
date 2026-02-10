# Football RAG Intelligence - Complete Project Summary

## Project Vision

**Original Goal:** Build an automated system for generating in-depth post-game analytics reports that synthesize complex statistical data, player tracking information, and tactical observations into comprehensive, easy-to-understand reports for coaches, scouts, and players.

**The Problem:** Coaches and analysts waste valuable time browsing multiple apps (WhoScored, Fotmob, StatsBomb) to understand tactical patterns. Traditional LLMs hallucinate match statistics instead of retrieving real data, producing unreliable analysis.

**The Solution:** A Retrieval-Augmented Generation (RAG) system that grounds LLM responses in actual match data, eliminating hallucinations while providing instant tactical insights and visualizations.

---

## Why RAG + LLM?

### The Core Challenge
Transform structured football data (passing networks, shot maps, momentum graphs) into insightful tactical narratives like: *"Real Madrid's right flank overloads created progressive passing lanes leading to higher xT output."*

This requires **reasoned interpretation**, not just data transformation.

### What LLM Adds Beyond Rule-Based Systems

| Capability | Rule-Based | LLM | RAG + LLM |
|------------|-----------|-----|-----------|
| Grammatically correct reports | ✅ | ✅ | ✅ |
| Tactical terminology | ⚠️ (static) | ✅ | ✅ |
| Multi-stat tactical synthesis | ❌ | ✅ | ✅ |
| Historical context & patterns | ❌ | ❌ | ✅ |
| Hallucination prevention | ⚠️ | ❌ | ✅ |
| Cross-match learning | ❌ | ❌ | ✅ |

**Key Benefits:**
- **Abstract Reasoning:** Infers meaning from complex attribute combinations (e.g., high verticality + tight compactness = direct transition play)
- **Semantic Aggregation:** Connects spatial, numerical, and role-based data naturally
- **Context Retrieval:** Grounds analysis in historical team patterns and similar matches
- **Anti-Hallucination:** RAG injects exact source facts, preventing invented statistics

---

## Technical Architecture

### Data Pipeline: Scraping to Intelligence

```
WhoScored + Fotmob (Raw Sources)
    ↓
Python Scrapers (BeautifulSoup/Requests)
    ↓
Raw JSON Files (MinIO Storage + Local)
    ↓
ETL Pipeline (Pydantic Validation)
    ↓
matches_gold.json (Golden Dataset)
    ↓
ChromaDB Indexing (2 chunks per match)
    ↓
RAG Pipeline (LlamaIndex)
    ↓
User Interface (Gradio)
```

### Data Sources

**WhoScored:**
- Event-level granularity (~1355 events per match)
- 108 Eredivisie 2025-26 matches scraped
- Detailed player positions, passes, shots, defensive actions

**Fotmob:**
- xG values and shot quality data
- Cross-referenced via `match_mapping.json`

**Data Characteristics:**
- **Volume:** 108 matches (as of December 2025)
- **Coverage:** Eredivisie 2025-26 season matchdays
- **Storage:** MinIO object store + local JSON files
- **Format:** Structured JSON validated with Pydantic schemas

---

## Core Technical Decisions

### 1. Precalculated Metrics Architecture

**Why Precalculate?**
- **Performance:** Simple RAG pipeline, faster queries
- **Consistency:** Stable prompt requirements (Prompt V3.5)
- **Rebuild Speed:** 18 seconds to rebuild entire ChromaDB (108 matches)

**Trade-off:** Must rebuild if metric logic changes (acceptable for MVP)

**38 Tactical Metrics Per Team:**
- Possession, pass accuracy, verticality
- Progressive passes, PPDA, high press events
- xG, shots, shots on target
- Median position, defense line, compactness
- Field tilt

### 2. Golden Dataset ETL (Contract-Factory-Delivery)

**Architecture:**

| Layer | Script | Purpose |
|-------|--------|---------|
| **Contract** | `src/football_rag/data/models.py` | Pydantic schemas enforce data validity |
| **Factory** | `scripts/process_raw_data.py` | Transform raw data, calculate metrics, validate |
| **Delivery** | `scripts/rebuild_chromadb.py` | Ingest validated data into ChromaDB |

**Why This Matters:**
- Catches data bugs BEFORE indexing (fail-fast)
- Fixed critical "Home/Away swap bug" that caused hallucinations
- Pydantic "airlock" prevents corrupt data from reaching LLM

**Example Bug Fixed:** Heracles showing 7 shots instead of 24 due to incorrect team ID mapping

### 3. 2-Chunk ChromaDB Architecture

Each match → 2 documents in ChromaDB:

1. **Summary Chunk:** Team names, score, date, possession, xG (for filtering)
2. **Tactical Metrics Chunk:** All 38 precalculated metrics (for LLM generation)

**Why Not 4 Chunks?**
- Simpler retrieval logic
- Faster queries
- Sufficient context for Prompt V3.5

**Visualizations:** Bypass ChromaDB entirely, load raw JSON files directly for matplotlib rendering

### 4. Vector Embeddings Strategy

**Model:** `sentence-transformers/all-mpnet-base-v2`

**Why This Model?**
- **Balance:** 768-dimensional embeddings (performance vs quality)
- **Domain Agnostic:** Pretrained on diverse text, works for tactical language
- **Open Source:** No API costs, runs locally
- **Proven:** Widely used in RAG systems, strong baseline

**Embedding Process:**
1. Combine summary + tactical metrics into natural language text
2. Generate embeddings via sentence-transformers
3. Store in ChromaDB with metadata for filtering

### 5. Prompt-First Design Philosophy

**Critical Decision:** Designed Prompt V3.5 BEFORE building ChromaDB schema

**Result:**
- Zero retrieval-generation mismatch
- ChromaDB metadata perfectly aligned with prompt requirements
- 80% token reduction from V1.0 → V3.5 (~360 tokens average)

**Evaluation-Driven Development:**
- Tested prompts in Anthropic Console before coding
- Iterated based on 10-match evaluation dataset
- Monitored token spend throughout development
- Achieved 4.9/5 quality score

---

## Evaluation Framework

### The Strategy: LLM-as-a-Judge + Ground Truth

**Test Dataset:** 10 diverse matches from `tactical_analysis_eval.json`
- Blowouts, close games, defensive struggles, high-scoring matches
- Ground truth: `matches_gold.json` (108 Pydantic-validated matches)

### Three-Dimensional Evaluation

| Metric | Target | Achieved | Methodology |
|--------|--------|----------|-------------|
| **Retrieval Accuracy** | >90% | **100%** | Metadata filtering ("Sniper" approach) |
| **Faithfulness** | >90% | **99.4%** | Regex + ground truth verification |
| **Tactical Insight** | >80% | **95.0%** | LLM-as-a-Judge (reference-based) |

**Why These Metrics?**

1. **Retrieval Accuracy:** Ensures correct match data is found (metadata filtering vs semantic-only search)
2. **Faithfulness:** Prevents hallucinations by verifying every cited statistic exists in golden dataset
3. **Tactical Insight:** Measures analytical value beyond raw data reporting

**Key Fixes During Evaluation:**
- **False Failure #1:** Aligned test to match-specific queries (not broad search)
- **False Failure #2:** Expanded ground truth to full `matches_gold.json`
- **False Failure #3:** Implemented structured JSON output for Judge LLM

---

## Dual-Mode Interface: Text + Visualizations

### Query Routing Architecture

```
User Query
    ↓
Match Identification (ChromaDB)
    ↓
Intent Classification (Keyword Matching)
    ↓
┌─────────────┴──────────────┐
↓                            ↓
LLM Text Analysis      Visualizations
(Prompt V3.5)         (matplotlib/mplsoccer)
~360 tokens           $0 cost
    ↓                            ↓
Commentary            6 viz types
    └──────────┬─────────────┘
               ↓
       Final Output
```

**Why Keyword Routing?**
- **$0 Cost:** No LLM calls for visualization routing
- **Instant:** No API latency
- **Flexible:** Works with any LLM provider
- **95% Coverage:** Handles most visualization requests

### 6 Prebuilt Visualizations (matplotlib + mplsoccer)

Built by hand to ensure quality and control:

1. **Dashboard** - 3x3 grid with all tactical metrics
2. **Passing Network** - Player positions with connection strength
3. **Defensive Heatmap** - KDE of defensive actions
4. **Progressive Passes** - Forward pass zones
5. **Shot Map** - Both teams' shots with xG markers
6. **xT Momentum** - Match flow over time

**Coordinate Transformation Fix:** WhoScored (0-100) → StatsBomb (0-120 x 0-80) scale

**Future Expansion:**
- Additional tactical visualizations (pressure maps, build-up patterns)
- Player-specific metrics and comparisons
- Multi-match trend analysis

---

## API Key Strategy: Flexible MVP Approach

### Why User-Provided API Keys?

**MVP Rationale:**
- **Flexibility:** Users choose their preferred provider (Anthropic, OpenAI, Gemini)
- **Cost Control:** No infrastructure costs during validation phase
- **Security:** Keys never stored, in-memory only
- **Demonstration:** Proves RAG concept works across providers

**Supported Providers:**
- **Anthropic Claude** Haiku 3.5 (recommended, ~$0.0001/query)
- **OpenAI GPT-4o mini** (~$0.00015/query)
- **Google Gemini 1.5 Flash** (~$0.00005/query)

**Future Evolution:**
- **Modal Integration:** Self-hosted LLMs for cost reduction at scale
- **Embedding API:** Cloud-hosted embedding generation
- **Caching Layer:** Reduce redundant API calls

---

## Deployment: HuggingFace Spaces

### Mac/Linux Binary Incompatibility Challenge

**Problem:** ChromaDB's HNSW index `.bin` files created on macOS x86_64 crash on Linux containers

**Symptom:** Rust panic errors on HF Spaces despite working locally

**Root Cause:** Platform-specific binary format incompatibility

**Solution:** Build ChromaDB fresh on Linux from `matches_gold.json`

### Deployment Architecture

**HF Spaces Entry Point (`app.py`):**
1. Download `matches_gold.json` from HF Dataset
2. Build ChromaDB fresh on Linux (creates native binaries)
3. Download raw match data for visualizations
4. Launch Gradio interface

**Benefits:**
- Clean Linux-native binaries (no crashes)
- Reproducible builds
- No git binary file issues (orphan branch strategy)

---

## Project Modularity & Design Principles

### Code Philosophy: KISS, DRY, SOLID

**Functions Over Classes:**
- Default to functions unless shared state required
- Example: `viz_tools.py` - 3 public functions, shared data loading logic

**Complexity Limits:**
- Functions: Max 20 lines
- Files: Max 300 lines
- Nesting: Max 3 levels
- Arguments: Max 4 parameters

**Self-Review Checklist:**
- Can I remove abstraction layers?
- Are all type hints necessary?
- Can I reduce nesting with early returns?
- Would I maintain this in 6 months?

### Module Structure

```
src/football_rag/
├── app/main.py           # Gradio interface
├── models/rag_pipeline.py # RAG orchestration
├── data/
│   ├── models.py         # Pydantic schemas
│   ├── schemas.py        # Match context models
│   └── scrapers.py       # Web scrapers
├── router.py             # Intent classification
├── visualizers.py        # Matplotlib plots
├── viz_tools.py          # Visualization API
└── prompts_loader.py     # YAML prompt management
```

**Clear Separation of Concerns:**
- Data layer: Scraping, validation, schemas
- Storage layer: ChromaDB, MinIO
- Model layer: RAG pipeline, embeddings
- Presentation layer: Gradio UI, visualizations

---

## Gradio as MVP Frontend

### Why Gradio?

**Rapid Prototyping:**
- Python-native (no frontend framework needed)
- Built-in components (textbox, dropdown, image, markdown)
- Auto-generates shareable demo UI

**HF Spaces Integration:**
- Native deployment platform
- Automatic public URL
- Version control via Git

**User Experience:**
- 2-column layout (controls + output)
- Dynamic rendering (text OR image based on query)
- Provider selection dropdown
- Real-time API key input (secure, in-memory)

**Limitations for Production:**
- Limited customization vs React/Vue
- Performance at scale
- Advanced state management

**Future Migration:** FastAPI backend + React frontend for production scalability

---

## Cost Analysis & Token Optimization

### Token Reduction Journey

**Prompt V1.0 → V3.5:**
- **80% token reduction** (1800 → 360 avg tokens)
- **Method:** Removed redundant instructions, optimized structure
- **Result:** Sub-$0.01 per 100 queries with Claude Haiku

### Cost Breakdown (100 Queries)

| Component | Cost |
|-----------|------|
| Visualization routing | $0.00 (keyword matching) |
| Visualization generation | $0.00 (matplotlib) |
| Text analysis (Claude Haiku) | ~$0.01 |
| **Total** | **< $0.50** ✅ |

**Course Requirement Met:** Full demo testing under $0.50

---

## Key Technical Achievements

### 1. Data Quality Pipeline
- Fixed Home/Away swap bug causing hallucinations
- Pydantic "airlock" pattern prevents corrupt data
- 18-second ChromaDB rebuild for 108 matches

### 2. Evaluation Excellence
- 100% retrieval accuracy (metadata filtering)
- 99.4% faithfulness (ground truth validation)
- 95% tactical insight (LLM-as-a-Judge)

### 3. Cost Optimization
- $0 visualization routing (keyword matching)
- 80% token reduction through prompt engineering
- Multi-provider flexibility (no vendor lock-in)

### 4. Production Deployment
- Solved Mac/Linux ChromaDB incompatibility
- Orphan branch strategy for HF Spaces
- Automated data download on first launch

### 5. Clean Architecture
- Functions over classes (KISS principle)
- Clear module boundaries (SOLID)
- Comprehensive type annotations

---

## Optional Features Implemented (7/5 Required)

1. ✅ **RAG Evaluation:** Complete harness with 3-metric system
2. ✅ **Domain-Specific:** Football tactical analysis (not generic AI tutor)
3. ✅ **2+ Data Sources:** WhoScored + Fotmob with cross-linking
4. ✅ **Structured JSON:** Pydantic-validated ETL pipeline
5. ✅ **Metadata Filtering:** 100% retrieval accuracy
6. ✅ **Query Routing:** Intent classification (text vs visualization)
7. ✅ **Function Calling:** 6 visualization types via keyword routing

---

## Next Steps: Production Scaling

### Vision
Scale from 108 Eredivisie matches → 2000+ matches across Championship, Jupiler Pro League, and Brasileirão with automated daily updates.

### Proposed Stack

**Orchestration:** Dagster - DAG-based scheduling for scraping, ETL, rebuilds

**Data Quality:** dbt + DuckDB - Transform & validate data before indexing

**Cloud Inference:** Modal - Serverless embedding generation with GPU access

**Storage:** Local Lakehouse DuckDB - Raw data storage, PostgreSQL for metadata queries

**Monitoring:** Opik - LLM observability & prompt tracking

### Future Enhancements

**Visualization Layer:**
- Player-specific metrics and comparisons
- Multi-match trend analysis
- Advanced tactical patterns (pressure maps, build-up zones)

**Data Pipeline:**
- Automated daily scraping via GitHub Actions
- Multi-league support with league-agnostic ETL
- Real-time match data integration

**LLM Infrastructure:**
- Self-hosted LLMs on Modal (cost reduction at scale)
- Context caching for repeated queries
- Fine-tuned embeddings for football domain

---

## Learning Resources

- [Data Engineering Academy](https://iansaura.com)
- [dbt Fundamentals](https://courses.getdbt.com/collections)
- [Modal Examples](https://modal.com/docs/examples)
- [Full Stack AI Engineering Course](https://www.towardsai.net/)

---

## Project Metrics Summary

**Data:**
- 108 Eredivisie 2025-26 matches indexed
- 216 ChromaDB documents (2 chunks × 108 matches)
- 38 tactical metrics per team per match
- ~1355 events per match

**Evaluation:**
- Retrieval Accuracy: 100%
- Faithfulness: 99.4%
- Tactical Insight: 95.0%

**Performance:**
- ChromaDB rebuild: 18 seconds
- Average prompt: 360 tokens (80% reduction from V1.0)
- Cost per 100 queries: < $0.01 (Claude Haiku)

**Deployment:**
- Live HF Space: https://huggingface.co/spaces/rheredia8/football-rag-intelligence
- GitHub: https://github.com/ricardoherediaj/football-rag-intelligence
- License: MIT

---

## Conclusion

This project demonstrates a production-ready RAG system that:
- **Eliminates hallucinations** through ground truth validation
- **Optimizes costs** via prompt engineering and smart routing
- **Delivers value** to coaches and analysts with tactical insights
- **Scales efficiently** with modular, maintainable architecture

From MVP to production scaling, every decision prioritized simplicity, data quality, and user value over premature optimization.
