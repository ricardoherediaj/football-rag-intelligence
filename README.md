# ⚽ Football RAG Intelligence

[![Hugging Face Spaces](https://img.shields.io/badge/🤗%20Hugging%20Face-Spaces-blue)](https://huggingface.co/spaces/rheredia8/football-rag-intelligence)

**Post-match tactical analysis for Eredivisie 2025-26 season. Ask questions, get grounded answers backed by real match data.**

🚀 **[Try the Live Demo](https://huggingface.co/spaces/rheredia8/football-rag-intelligence)**

---

## 📸 Demo

### Text Analysis
![Text Analysis](docs/assets/app_sc.png)

### Visualizations
![Dashboard Visualization](docs/assets/app_sc2.png)

---

## 🎯 The Problem

**For coaches, scouts, and analysts:** Browsing post-match data across multiple apps (WhoScored, Fotmob, StatsBomb) wastes valuable time. You need quick, centralized access to tactical insights from past games.

**Traditional LLMs can't help** because they hallucinate when asked about specific matches:
- ❌ "PSV dominated possession" (actually 45%)
- ❌ "Heracles created few chances" (actually 24 shots)
- ❌ Generic analysis without tactical depth

**Why this happens:** LLMs lack access to your match data and fabricate plausible-sounding stats instead of retrieving real numbers.

## 💡 The Solution

A **centralized RAG system** that ingests and processes your own match data, enabling natural language queries for instant visual and text reports:

**What it does:**
1. **Centralizes** your data: Ingest from WhoScored, Fotmob (108 Eredivisie matches indexed)
2. **Retrieves** actual match data from a vector database (ChromaDB)
3. **Generates** tactical insights using LLMs grounded in real metrics (xG, PPDA, progressive passes)
4. **Validates** faithfulness (100% retrieval, 99.4% faithfulness, 95% tactical insight)
5. **Visualizes** tactical patterns instantly (6 visualization types, $0 cost)

**Ask in natural language, get instant answers:**
- "What was PSV's pressing strategy against Ajax?" → Text analysis
- "Show dashboard for Heracles vs PEC Zwolle" → Visual report
- No more browsing multiple apps. No hallucinations. Just grounded insights from your data.

---

## ✨ Key Features

### 🎨 Dual-Mode Interface
- **Text Analysis:** LLM-generated tactical commentary using engineered prompts
- **Visualizations:** Instant, $0-cost rendering (passing networks, shot maps, dashboards)

### 🔄 Multi-Provider Support
Choose your LLM provider - no vendor lock-in:
- **Anthropic Claude** (Haiku 3.5 - recommended)
- **OpenAI GPT** (GPT-4o mini)
- **Google Gemini** (Gemini 1.5 Flash)

### 🎯 Smart Routing
- **Questions** (What/How/Why) → LLM text analysis
- **Explicit commands** (Show/Display) → Keyword-based visualization routing
- **Zero hallucinations:** Every stat traced to source data

### 📊 Production-Quality Evaluation
- **Retrieval Accuracy:** 100% (metadata filtering)
- **Faithfulness:** 99.4% (Pydantic validation)
- **Tactical Insight:** 95.0% (LLM-as-a-Judge)

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- `uv` package manager (or `pip`)
- API key for your chosen LLM provider

### Installation

```bash
# Clone repository
git clone https://github.com/yourusername/football-rag-intelligence
cd football-rag-intelligence

# Install dependencies
uv pip install -e .

# Run the app
uv run python -m football_rag.app
```

Visit `http://localhost:7860` in your browser.

### Example Queries

**Text Analysis:**
```
"What was PSV's pressing strategy against Ajax?"
"How did Heracles build up play against PEC Zwolle?"
"Explain the tactics in Feyenoord vs Ajax"
```

**Visualizations:**
```
"Show dashboard for Heracles vs PEC Zwolle"
"Show passing network for Feyenoord"
"Show shot map for AZ vs Utrecht"
```

---

## 💰 Cost Estimation

**Testing all features costs < $0.50:**

| Provider | Cost per Query | 100 Queries |
|----------|----------------|-------------|
| **Claude Haiku 3.5** | ~$0.0001 | ~$0.01 |
| **GPT-4o mini** | ~$0.00015 | ~$0.015 |
| **Gemini Flash 1.5** | ~$0.00005 | ~$0.005 |

**Why so cheap?**
- Prompt engineering reduced tokens by 80% (V1.0 → V3.5)
- Keyword routing for visualizations ($0 cost)
- Average response: ~360 tokens

---

## 🏗️ Architecture

### The Flow
```
User Query → Router (classify_intent)
             ↓
    ┌────────┴─────────┐
    ↓                  ↓
LLM Analysis      Visualization
(Prompt V3.5)     (Keyword-based)
    ↓                  ↓
pipeline.run()    viz_tools.*
    ↓                  ↓
Commentary        Image Output
```

### Key Design Decisions

**1. Prompt-First RAG (Why?)**
- Designed Prompt V3.5 BEFORE building ChromaDB
- Result: Zero retrieval-generation mismatch
- ChromaDB metadata perfectly aligned with prompt requirements

**2. Pre-Calculated Metrics (Why?)**
- 38 tactical metrics computed during ingestion
- Trade-off: Must rebuild if metric logic changes (18 sec rebuild)
- Benefit: Simpler RAG pipeline, faster queries, stable V3.5 prompt

**3. 2-Chunk Architecture (Why?)**
- Each match → 2 ChromaDB documents:
  1. **Summary** (filtering by team/date)
  2. **Tactical Metrics** (LLM generation)
- Enables selective retrieval: "Get only tactical metrics"
- Visualizations bypass ChromaDB entirely (load raw JSON files directly)

**4. Keyword-Based Routing (Why?)**
- $0 cost, instant, works with any provider
- Priority: Questions → LLM, Commands → Viz
- Prevents routing collisions (e.g., "pressing strategy" ≠ "pressing heatmap")

**5. Golden Dataset ETL (Why?)**
- Decoupled pipeline: Extract → Transform → Load
- Catches data bugs BEFORE indexing (fail-fast)
- Pydantic "airlock" prevents corrupt data from reaching LLM

---

## 📊 Data Pipeline

### Sources
- **WhoScored:** Event-level granularity (108 matches)
- **Fotmob:** xG values + shot data
- **Match Mapping:** `match_mapping.json` for cross-source linking

### ETL Architecture
```
scripts/process_raw_data.py (Factory)
    ↓
matches_gold.json (Golden Dataset)
    ↓
scripts/rebuild_chromadb.py (Delivery)
    ↓
ChromaDB (216 documents = 108 matches × 2 chunks)
```

**Why this matters:** Fixed "Home/Away swap bug" that caused hallucinations (e.g., Heracles showing 7 shots instead of 24).

---

## 🧪 Evaluation

### The Strategy
Quantitative harness using "LLM-as-a-Judge" methodology across 3 dimensions:

| Metric | Target | Achieved | How |
|--------|--------|----------|-----|
| **Retrieval Accuracy** | >90% | **100%** | Metadata filtering ("Sniper" approach) |
| **Faithfulness** | >90% | **99.4%** | Pydantic validation + ground truth check |
| **Tactical Insight** | >80% | **95.0%** | Reference-based LLM judging (strict rubric) |

**Test Dataset:** 10 diverse matches (blowouts, close games, tactical variations)

**Key Fixes:**
- False Failure #1: Aligned test to match-specific queries (not broad search)
- False Failure #2: Expanded ground truth to full `matches_gold.json`
- False Failure #3: Fixed API key loading + structured JSON output

### Evaluation Dataset Details

**Location:** [data/eval_datasets/tactical_analysis_eval.json](data/eval_datasets/tactical_analysis_eval.json)

**Test Cases (10 matches):**
1. **Blowout Game** - Heracles vs PEC Zwolle (2-8): Testing xG paradox detection
2. **High-Scoring** - NEC Nijmegen vs PSV (5-3): Testing aggressive tactical analysis
3. **Stalemate** - Twente vs Telstar (0-0): Testing dominance without goals
4. **Narrow Win** - PEC Zwolle vs Twente (1-0): Testing tight margin analysis
5. **Upset** - Feyenoord vs FC Volendam (1-3): Testing counter-attack recognition
6. **Efficiency Study** - Heracles vs AZ Alkmaar (2-1): Testing conversion rate insights
7. **Defensive Struggle** - NAC Breda vs Go Ahead Eagles (0-1): Testing low xG analysis
8. **Counter-Attack** - NEC Nijmegen vs Twente (4-2): Testing transition patterns
9. **Defensive Dominance** - Excelsior vs Sparta Rotterdam (0-1): Testing clean sheet analysis
10. **Tight Margins** - Excelsior vs PSV (1-2): Testing competitive balance

**Ground Truth Source:** [data/processed/matches_gold.json](data/processed/matches_gold.json) (108 matches, Pydantic-validated)

**Run Evaluation:**
```bash
uv run python tests/evaluate_pipeline.py
```

**Results File:** [data/eval_datasets/eval_results.json](data/eval_datasets/eval_results.json)

---

## 🎨 Visualizations

6 tactical visualization types (generated via matplotlib):

1. **Dashboard** - 3x3 grid with all metrics
2. **Passing Network** - Player positions + connections
3. **Defensive Heatmap** - Defensive actions KDE
4. **Progressive Passes** - Forward pass zones
5. **Shot Map** - Both teams' shots with xG
6. **xT Momentum** - Match flow over time
7. **Match Stats** - Stats comparison bars

**Access:** Use "Show [viz_type] for [match]" queries

---

## 🔑 API Keys

Paste your API key in the UI (keys never stored):

- **Anthropic:** [console.anthropic.com/account/keys](https://console.anthropic.com/account/keys)
- **OpenAI:** [platform.openai.com/account/api-keys](https://platform.openai.com/account/api-keys)
- **Gemini:** [makersuite.google.com/app/apikey](https://makersuite.google.com/app/apikey)

**Security:**
- ✅ Never stored in files or database
- ✅ Only used in-memory for current session
- ✅ Not logged or tracked

---

## 📁 Project Structure

```
football-rag-intelligence/
├── src/football_rag/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── __main__.py        # Entry point: python -m football_rag.app
│   │   └── main.py            # Gradio UI
│   ├── models/
│   │   └── rag_pipeline.py    # RAG orchestration
│   ├── data/
│   │   ├── models.py          # Pydantic schemas
│   │   ├── schemas.py         # Match context models
│   │   └── scrapers.py        # Web scrapers
│   ├── router.py              # Intent classification
│   ├── visualizers.py         # Matplotlib visualizations
│   ├── viz_tools.py           # Viz wrapper API
│   ├── prompts_loader.py      # Load prompts from YAML
│   └── custom_logging.py      # JSON logging
├── scripts/
│   ├── process_raw_data.py    # ETL: Raw → Golden Dataset
│   └── rebuild_chromadb.py    # ETL: Golden → ChromaDB
├── tests/
│   └── evaluate_pipeline.py  # Evaluation harness
├── prompts/
│   └── v3.5_balanced.yml      # Production prompt (4.9/5 score)
├── data/
│   ├── chroma/                # Vector database (git-ignored)
│   └── matches_gold.json      # Validated dataset
└── pyproject.toml
```

---

## 🛠️ Development

### Run Tests
```bash
uv run pytest
```

### Rebuild ChromaDB
```bash
# Process raw data → Golden Dataset
uv run python scripts/process_raw_data.py

# Ingest Golden Dataset → ChromaDB
uv run python scripts/rebuild_chromadb.py
```

### Run Evaluation
```bash
uv run python tests/evaluate_pipeline.py
```

---

## 🚀 Deployment

### Hugging Face Spaces

1. Create Space: [huggingface.co/new-space](https://huggingface.co/new-space) (Gradio SDK)
2. Connect GitHub repo
3. Add API key secrets (optional, users can provide their own)
4. Auto-deploy from main branch

### Local Docker (Optional)
```bash
docker compose up -d  # If using ChromaDB service
```

---

## 📚 Technical Learnings

### What Worked
1. **Prompt-first design** → ChromaDB aligned with project goal
2. **Simple code** → Functions over classes
3. **Pre-calculated metrics** → quick rebuild
4. **Golden Dataset ETL** → Caught data bugs before indexing

### What We Avoided
- ❌ Over-engineering (no abstract classes, factories)
- ❌ Premature optimization (no caching, retry logic)
- ❌ On-demand calculation (slow, complex)
- ❌ Pure semantic search (added metadata filtering)

### Design Principles Applied
- **KISS:** Simplest solution that works
- **DRY:** Reused visualizers.py logic
- **SOLID:** Single responsibility per module
- **Rule of Three:** Only abstract after third repetition

---

## 🏆 Acknowledgments

Built for the [Full Stack AI Engineering](https://www.towardsai.net/) course capstone project.

**Course Requirements Met:**
- ✅ RAG system with retrieval + generation
- ✅ Multi-provider LLM support (Anthropic, OpenAI, Gemini)
- ✅ Hugging Face Spaces deployment
- ✅ Cost < $0.50 for full demo
- ✅ API key security (no hardcoding)
- ✅ Comprehensive README with cost estimation
- ✅ **7/5 optional features** (see section above)

**Inspired by:**
- [LLMOps Python Package](https://github.com/callmesora/llmops-python-package)
- [Stop Launching AI Apps Without This - Decoding AI](https://www.decodingai.com/p/stop-launching-ai-apps-without-this)
- [AI Tutor Skeleton - Towards AI](https://github.com/towardsai/ai-tutor-skeleton/tree/main)

---

## 📋 Course Optional Features Implemented

**Required: 5 features minimum | Implemented: 7 features ✅**

1. ✅ **RAG Evaluation Code & Results** - Complete evaluation harness with 3-metric system:
   - Retrieval Accuracy: 100%
   - Faithfulness: 99.4%
   - Tactical Insight: 95.0%
   - Evaluation script: [tests/evaluate_pipeline.py](tests/evaluate_pipeline.py)
   - Test dataset: [data/eval_datasets/tactical_analysis_eval.json](data/eval_datasets/tactical_analysis_eval.json)
   - Results: [data/eval_datasets/eval_results.json](data/eval_datasets/eval_results.json)

2. ✅ **Domain-Specific Application** - Football tactical analysis system (not an AI tutor)
   - Specialized for coaches, scouts, and analysts
   - 38 pre-calculated tactical metrics
   - Eredivisie 2025-26 season focus

3. ✅ **2+ Data Sources Collection** - Multi-source data ingestion with cross-linking:
   - WhoScored: Event-level data (108 matches, ~1355 events/match)
   - Fotmob: xG values and shot data
   - ID mapping system: [match_mapping.json](data/match_mapping.json) for reliable cross-source linking
   - Data collection scripts: [src/football_rag/data/scrapers.py](src/football_rag/data/scrapers.py)

4. ✅ **Structured JSON Outputs** - Pydantic-validated data pipeline:
   - Golden dataset: [data/processed/matches_gold.json](data/processed/matches_gold.json)
   - Pydantic schemas: [src/football_rag/data/models.py](src/football_rag/data/models.py)
   - Contract → Factory → Delivery ETL architecture
   - Prevents corrupt data via "airlock" pattern

5. ✅ **Metadata Filtering** - "Sniper" approach for 100% retrieval accuracy:
   - Team-based filtering (home_team/away_team metadata)
   - Entity extraction from queries
   - 100% retrieval accuracy vs 70% with semantic-only search

6. ✅ **Query Routing** - Intent classification system:
   - Router module: [src/football_rag/router.py](src/football_rag/router.py)
   - Routes queries to text analysis (LLM) or visualization (keyword-based)
   - Priority logic prevents routing collisions
   - Example: "What was PSV's pressing?" → Text | "Show pressing heatmap" → Viz

7. ✅ **Function Calling** - Dynamic visualization generation:
   - 6 visualization types (dashboard, passing network, heatmaps, shot maps, etc.)
   - Keyword-based routing to viz functions
   - $0 cost (no LLM calls for visualizations)
   - Viz tools: [src/football_rag/viz_tools.py](src/football_rag/viz_tools.py)

---

## 🚀 Next Steps: Production Scaling

**Vision:** Scale from 108 Eredivisie matches → 2000+ matches across Championship, Jupiler Pro League, and Brasileirão with automated daily updates.

### Core Stack (TODO)

- **Orchestration:** Apache Airflow - Schedule scraping, ETL, ChromaDB rebuilds
- **Data Quality:** dbt + Great Expectations - Transform & validate data
- **Cloud Inference:** Modal - Serverless embedding generation
- **Storage:** AWS S3 Free Tier - Raw data storage
- **Monitoring:** Opik - LLM observability & prompt tracking

### Learning Path
- [Data Engineering Academy](https://iansaura.com)
- [dbt Fundamentals](https://courses.getdbt.com/collections)
- [Modal Examples](https://modal.com/docs/examples)

---

## 📝 License

MIT License - See LICENSE file

---

## 📧 Contact

Questions or issues? Open a GitHub issue.
