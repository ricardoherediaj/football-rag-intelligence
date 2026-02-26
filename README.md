# Football RAG Intelligence

[![Hugging Face Spaces](https://img.shields.io/badge/🤗%20Hugging%20Face-Spaces-blue)](https://huggingface.co/spaces/rheredia8/football-rag-intelligence)

**An active sports analytics engineering project.** Natural language queries over real Eredivisie match data — grounded answers backed by a production data pipeline.

🚀 **[Try the Live Demo](https://rheredia8-football-rag-intelligence.hf.space/)**

> **Status:** 🟢 **Phase 1–4a COMPLETE — Live on HF Spaces, auto-refreshing**
> - Phase 1: Data pipeline (412 matches, 279k events, dbt + MotherDuck + CI)
> - Phase 2: RAG engine (DuckDB VSS retrieval, Opik tracing, multi-path routing)
> - Phase 3a: Evaluation locked (retrieval_accuracy=1.0, tactical_insight=0.91, answer_relevance=0.84)
> - Phase 3b: **Streamlit UI deployed** — text analysis + 7 viz types live at public URL
> - Phase 4a: **Hybrid pipeline automation** — scrape → dbt → embed → HF deploy, fully chained via Dagster sensors. dagster-daemon auto-starts at macOS login via launchd.

---

## Results

| Metric | Value | Meaning |
|--------|-------|---------|
| **Retrieval Accuracy** | 1.0000 (10/10) | Every query returns the correct match (Recall@1) |
| **Tactical Insight** | 0.9142 | Domain judge validates grounding + specificity + terminology |
| **Answer Relevance** | 0.8380 | LLM output remains on-topic to user query |
| **Pipeline Coverage** | 205/205 (100%) | All Eredivisie 2025-26 matches in schema |
| **Latency** (local) | ~1.5s | Query embed + VSS + LLM response |
| **Data Freshness** | Mon/Thu 7am UTC | GitHub Actions dbt run (CI integrated) |
| **Tests** | 57 passing, 0 failing | End-to-end pipeline + RAG + observability |

**Baseline:** 10 tactical analysis test cases evaluated via opik.evaluate(), all metrics locked in production.

---

## Demo

### Shot Map
![Shot Map — Fortuna Sittard vs Go Ahead Eagles](docs/assets/newapp1.png)

### Tactical Analysis
![Text Analysis — Ajax vs Feyenoord](docs/assets/newapp2.png)

---

## The Problem

Coaches, scouts, and analysts spend time bouncing between WhoScored, FotMob, and other tools to reconstruct what happened in a match. Traditional LLMs can't help because they can fabricate stats instead of retrieving them:

- ❌ "PSV dominated possession" (actual: 45%)
- ❌ "Heracles created few chances" (actual: 24 shots)
- ❌ Generic tactical commentary with no grounding

The solution presented here is a RAG system built on real match data.

---

## Quick Start (3 Examples)

Run locally (Phase 2 engine working today):

```python
from football_rag.orchestrator import query

# 1️⃣ Tactical analysis (semantic RAG)
result = query("Why did PSV Eindhoven edge Excelsior 2-1 despite their high press?")
print(result["text"])  # → grounded commentary with xG, position, PPDA stats

# 2️⃣ Statistical query (exact metric retrieval)
result = query("Which team had the highest PPDA in their last match?")
print(result["viz_metrics"])  # → {"team": "...", "ppda": 8.2, ...}

# 3️⃣ Visualization request (routing to chart engine)
result = query("Show me the shot map from the Ajax vs Feyenoord match")
print(result["chart_path"])  # → PNG with both teams' shots by xG
```

**Each query is grounded:** Retrieved match data → Claude generates → metrics validated against DuckDB (no hallucination).

---

## Architecture

```
 ┌─────────────────────────────────────────────────────────────────┐
 │  DATA COLLECTION  (local — residential IP required)             │
 │                                                                 │
 │  WhoScored ──► Playwright scraper                               │
 │  FotMob    ──► SSR extractor (__NEXT_DATA__)                    │
 │                      │                                          │
 │                 Dagster Assets                                  │
 │         (Mon/Thu schedule + manual trigger)                     │
 └────────────────────┬────────────────────────────────────────────┘
                      │
                      ▼
 ┌─────────────────────────────────────────────────────────────────┐
 │  STORAGE LAYER                                                  │
 │                                                                 │
 │  MinIO (object store)          DuckDB — lakehouse.duckdb        │
 │  └─ raw JSON                   └─ bronze_matches (412)          │
 │                                └─ match_mapping  (205)          │
 │                                └─ silver_events  (279k)         │
 │              MotherDuck (cloud DuckDB)                          │
 │              └─ same schema, auto-synced on scrape              │
 │              └─ silver_team_metrics, gold_match_summaries       │
 └────────────────────┬────────────────────────────────────────────┘
                      │
                      ▼
 ┌─────────────────────────────────────────────────────────────────┐
 │  TRANSFORMATION  (dbt Core + GitHub Actions)                    │
 │                                                                 │
 │  bronze_matches ──► silver_events      (279,104 events)         │
 │                 └─► silver_team_metrics (378 team performances) │
 │                 └─► gold_match_summaries (205 match summaries)  │
 │                                                                 │
 │  CI: GitHub Actions runs dbt --target prod on Mon/Thu 7am UTC  │
 │  Tests: PASS=69 WARN=0 ERROR=0 FAIL=0                          │
 └────────────────────┬────────────────────────────────────────────┘
                      │
                      ▼
 ┌─────────────────────────────────────────────────────────────────┐
 │  EMBEDDINGS (local DuckDB — VSS not supported in MotherDuck)    │
 │                                                                 │
 │  gold_match_summaries ──► sentence-transformers/all-mpnet-base-v2
 │                       └─► gold_match_embeddings (205 × 768-dim) │
 │                           HNSW index, array_distance() queries  │
 └────────────────────┬────────────────────────────────────────────┘
                      │
                      ▼
 ┌─────────────────────────────────────────────────────────────────┐
 │  RAG ENGINE  [Phase 2 — COMPLETE ✅]                            │
 │                                                                 │
 │  User query ──► orchestrator.query() (router)                   │
 │                 │                                               │
 │         ┌───────┴────────┐                                      │
 │         ▼                ▼                                      │
 │   semantic query    viz request                                 │
 │   DuckDB VSS        fetch df_events from DuckDB                 │
 │   (array_distance)  visualizers.py → PNG                        │
 │   @opik.track       @opik.track                                 │
 │   → LLM (Claude)    → generate_with_llm()                       │
 │         │                │                                      │
 │         └───────┬────────┘                                      │
 │                 ▼                                               │
 │         {"text": ..., "viz_metrics": ...}                       │
 └─────────────────────────────────────────────────────────────────┘
                      │
                      ▼
 ┌─────────────────────────────────────────────────────────────────┐
 │  OBSERVABILITY  [Phase 3a — COMPLETE ✅]                        │
 │                                                                 │
 │  Opik (@opik.track on orchestrator + rag_pipeline + generate)   │
 │  EDD (3 metrics: retrieval_accuracy=1.0, tactical_insight=0.91, │
 │       answer_relevance=0.84) via opik.evaluate()                │
 │  21 pytest tests gated by --run-edd flag                        │
 │  Baseline: 10 test cases, all passing, metrics locked in Opik  │
 └─────────────────────────────────────────────────────────────────┘
                      │
                      ▼
 ┌─────────────────────────────────────────────────────────────────┐
 │  UI  [Phase 3b — next]                                          │
 │                                                                 │
 │  Streamlit single-page app                                      │
 │  Query input → orchestrator.query() → commentary + chart        │
 │  MotherDuck read-only for match selection (optional)            │
 └─────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Tool | Why |
|---|---|---|
| Language | Python 3.10+ via `uv` | |
| Orchestration | Dagster (Software-Defined Assets) | Asset lineage, sensor-chained jobs, daemon as macOS LaunchAgent |
| Object storage | MinIO | S3-compatible, single Docker container (Bronze JSON only) |
| Analytics DB | DuckDB + MotherDuck | Same SQL dialect local and cloud |
| Transformation | dbt Core (`dbt-duckdb`) | SQL version control, tested models |
| Embeddings | `sentence-transformers/all-mpnet-base-v2` | 768-dim, semantic match retrieval |
| Vector search | DuckDB VSS (`array_distance`) | No external vector DB needed |
| LLM | Anthropic Claude (primary) | Multi-provider via `generate.py` |
| CI/CD | GitHub Actions | `dbt run --target prod` Mon/Thu |
| Observability | Opik (Phase 3a DONE) | `@opik.track` end-to-end, EDD harness with 3 metrics |
| Evaluation | opik.evaluate() + custom scorers | retrieval_accuracy (1.0), tactical_insight (0.91), answer_relevance (0.84) |
| Cloud inference | Modal (Phase 4 planned) | Serverless GPU for open-source models |

---

## Data Coverage

- **League:** Eredivisie 2025-26
- **Matches:** 205 (100% coverage, auto-updated)
- **Events:** 279,104 tactical events (passes, shots, tackles, aerials...)
- **Metrics per match:** 24 pre-calculated tactical metrics per team (PPDA, progressive passes, xG, field tilt, compactness...)
- **Embeddings:** 205 match summary vectors, HNSW index

Sources: WhoScored (event-level) + FotMob (xG + shot data), cross-linked via `match_mapping`.

---

## Visualizations

6 tactical visualization types — rendered from raw event data, $0 LLM cost:

| Type | What it shows |
|---|---|
| **Dashboard** | Full 3×3 match report |
| **Passing Network** | Player positions + connection strength |
| **Defensive Heatmap** | KDE of defensive actions, block compactness |
| **Progressive Passes** | Forward pass zones with comet lines |
| **Shot Map** | Both teams' shots by type and xG |
| **xT Momentum** | Match flow over time (weighted Expected Threat) |

---

## LLM Providers

No vendor lock-in — swap via `provider` parameter:

| Provider | Model |
|---|---|
| Anthropic (default) | `claude-haiku-4-5` |
| OpenAI | `gpt-4o-mini` |
| Google | `gemini-1.5-flash` |
| Ollama (local) | `llama3.2:1b` |

---

## Why This Project Matters

Every component answers a production question:

- **Data pipeline (Dagster → dbt → DuckDB/MotherDuck):** Scales from Eredivisie → Championship → Brasileirão with zero code changes. Parameterized by league. Multi-source deduplication via match_mapping.
- **Vector search without vendor lock-in (DuckDB HNSW):** No Pinecone, Weaviate, or Milvus. `array_distance()` on FLOAT[768]. Embedding updates are SQL transactions, not API calls.
- **Observability as infrastructure (Opik @opik.track + EDD):** Not a dashboard bolt-on. LLM calls traced from orchestrator → rag_pipeline → generate. 3 domain-specific scorers with custom CoT reasoning.
- **Metrics locked, not tuned (retrieval=1.0, insight=0.91):** Each metric answers "is this production ready?" Not vibes. Baseline committed, thresholds in code.
- **Multi-provider LLM routing (Claude/OpenAI/Gemini/Ollama):** One `provider` parameter. No vendor dependency. Cost optimization and model experiments are one-line changes.
- **CI/CD on data quality (GitHub Actions + dbt testing):** Data tests automated. Pipeline broken? Workflow fails before MotherDuck updates. Same rigor as app code.

---

## Project Structure

```
football-rag-intelligence/
├── orchestration/              # Dagster assets, schedules, sensors
│   ├── assets/                 # bronze, silver, gold, embeddings
│   └── definitions.py
├── dbt_project/                # dbt models
│   ├── models/
│   │   ├── sources.yml
│   │   ├── silver/             # silver_events, silver_team_metrics
│   │   └── gold/               # gold_match_summaries
│   └── profiles.yml            # dev (local DuckDB) + prod (MotherDuck)
├── src/football_rag/
│   ├── models/
│   │   ├── rag_pipeline.py     # RAG orchestration [Phase 2]
│   │   └── generate.py         # LLM provider abstraction
│   ├── router.py               # Intent classification
│   ├── visualizers.py          # Matplotlib plot functions
│   ├── viz_tools.py            # Viz API (dashboard/team/match)
│   ├── data/schemas.py         # Pydantic models
│   └── prompts_loader.py
├── scripts/
│   ├── materialize_embeddings.py   # Regenerate HNSW index
│   └── test_vector_search.py       # Verify VSS queries
├── tests/
├── docs/
│   ├── engineering_diary/      # Session-by-session build log
│   └── motherduck-setup.md     # Cloud DB operational reference
├── ARCHITECTURE.md
├── SCRATCHPAD.md               # Active session state
└── CLAUDE.md                   # AI assistant instructions
```

---

## Quick Start

```bash
git clone https://github.com/ricardoherediaj/football-rag-intelligence
cd football-rag-intelligence
uv sync

# Run dbt transformations (local)
cd dbt_project && uv run dbt run

# Run dbt against MotherDuck (cloud)
MOTHERDUCK_TOKEN=<token> uv run dbt run --target prod

# Start Dagster UI
uv run dagster dev

# Verify vector search
uv run python scripts/test_vector_search.py

# Run tests
uv run pytest
```

---

## Pipeline Status

| Layer | Status | Details |
|---|---|---|
| **Data Collection** | ✅ Live | WhoScored + FotMob scrapers, 412 raw matches in MinIO |
| **Match Mapping** | ✅ Live | 205/205 (100% coverage) cross-linked via fotmob_id |
| **dbt Silver** | ✅ Live | 279,104 events, 378 team performances, GitHub Actions CI=PASS |
| **dbt Gold** | ✅ Live | 205 match summaries in MotherDuck (24 metrics per match) |
| **Embeddings (Phase 1)** | ✅ Live | 205 × 768-dim sentences, HNSW index in DuckDB |
| **RAG Engine (Phase 2)** | ✅ DONE | DuckDB VSS retrieval, multi-path routing (semantic + viz), @opik.track |
| **EDD Eval (Phase 3a)** | ✅ DONE | 3 scorers (retrieval=1.0, tactical_insight=0.91, answer_relevance=0.84), 21 pytest tests locked |
| **Streamlit UI (Phase 3b)** | ✅ DONE | Wide layout, BYOK API key, 5 free demo queries, deployed on HF Spaces |
| **Pipeline Automation (Phase 4a)** | ✅ DONE | scrape → dbt → embed → HF deploy chained via Dagster sensors. dagster-daemon as macOS LaunchAgent (auto-starts at login). Mon/Thu 7am UTC schedule. |
| **Modal Inference (Phase 4b)** | 📋 Planned | Serverless wrapper for generate_with_llm(), open-source model inference |

---

## Roadmap

**Phase 1 — Data Pipeline** ✅ COMPLETE
- Bronze/Silver/Gold medallion (dbt + Dagster)
- 205 matches with 24 tactical metrics each
- Auto-sync to MotherDuck, CI/CD on Mon/Thu

**Phase 2 — RAG Engine** ✅ COMPLETE
- DuckDB VSS retrieval (no external vector DB)
- Intent router: semantic text → LLM, viz requests → charts
- `orchestrator.query()` as single entry point
- Multi-provider LLM support (Claude/OpenAI/Gemini/Ollama)

**Phase 3a — Observability** ✅ COMPLETE
- `@opik.track` end-to-end (orchestrator → rag_pipeline → generate)
- EDD harness: 3 scorers, 21 pytest tests, 10 golden eval cases
- Metrics locked in Opik (baseline: retrieval=1.0, tactical_insight=0.91, answer_relevance=0.84)
- Maintenance: Version dataset names (v3 → v4) when eval queries change

**Phase 3b — Streamlit UI + Deploy** ✅ COMPLETE
- Wide-layout Streamlit app on HF Spaces
- BYOK (Bring Your Own Key) with rate-limited demo mode (5 free queries/session)
- Shot maps, passing networks, dashboards + text analysis — all live at public URL
- Cold start: downloads 536MB lakehouse.duckdb from private HF Dataset

**Phase 4a — Hybrid Pipeline Automation** ✅ COMPLETE
- Dagster sensor chain: `scrape_and_load_job` → `transform_job` → `deploy_job` (fully automatic)
- `deploy_job`: uploads lakehouse.duckdb (536MB) to HF Dataset + restarts Space
- `dagster-daemon` as macOS LaunchAgent — auto-starts at login, survives laptop sleep
- SQLite-backed local Dagster home (no Docker dependency for orchestration)
- Mon/Thu 7am UTC schedule via `eredivisie_post_matchday`

**Phase 4b — Prompt Tuning + Inference** *(planned)*
- Prompt v4.0: tactical interpretation over metric recitation
- EDD evaluation in CI (GitHub Actions)
- Open-source model inference via Modal (Llama 3 / vLLM, optional)

---

## Engineering Log

Build decisions and session notes documented in [`docs/engineering_diary/`](docs/engineering_diary/).

---

## License

MIT
