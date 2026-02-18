# Mentorship Notes: What You Should Actually Learn

**Purpose**: Understanding the *why* behind our Phase 1 work, not just copying code. These are patterns you'll use in every data/AI project.

---

## 🎯 Core Lesson: Data Quality Beats Model Quality

**What We Did**: Spent 2 hours fixing xG values (0 → realistic numbers like 2.34)

**Why It Matters**:
```
Bad data + Best LLM = Garbage output (hallucinations, wrong analysis)
Good data + Simple LLM = Reliable insights (99.4% faithfulness in MVP)
```

**The AI Engineering Truth**:
- 80% of your time will be data engineering (cleaning, joining, validating)
- 20% will be actual ML/LLM work (prompts, evaluation, fine-tuning)
- This ratio frustrates new AI engineers, but it's unavoidable

**Real-World Impact**:
- If xG stays at 0, LLM says "Team A had no attacking threat" (wrong!)
- With correct xG=2.34, LLM says "Team A created high-quality chances despite low possession" (right!)
- Your user loses trust after 1-2 wrong analyses, no matter how good your RAG system is

---

## 🔍 Lesson 1: Multi-Source Data Joins Are Your Enemy (And Your Reality)

### The Problem We Hit

**Symptom**: `xG = 0` for all teams
**Root Cause**: Two data sources with incompatible ID systems
- WhoScored: match_id = `1903733`, team_ids = `874`, `242`
- FotMob: match_id = `4815204`, team_ids = `6433`, `6422`

### Why This Happens Everywhere

**SaaS APIs never agree on IDs**:
- Stripe customer_id ≠ Salesforce account_id
- GitHub user_id ≠ Jira user_id
- Google Analytics session_id ≠ Mixpanel session_id

**Your Job as AI Engineer**: Build mapping tables to reconcile them.

### The Right Way to Fix It

**Step 1: Explore Both Sources**
```python
# WhoScored: What IDs do we have?
SELECT DISTINCT match_id, team_id FROM silver_events LIMIT 10;

# FotMob: What IDs do we have?
SELECT DISTINCT match_id, team_id FROM silver_fotmob_shots LIMIT 10;

# Result: They're completely different! ❌
```

**Step 2: Find Common Keys**
- WhoScored URL: `...1903733.../fortuna-sittard-go-ahead-eagles`
- FotMob JSON: `{"home_team": "Fortuna Sittard", "away_team": "Go Ahead Eagles"}`
- **Common key**: Team names + date (fuzzy match needed for "PSV Eindhoven" vs "PSV")

**Step 3: Create Mapping Table**
```python
# scripts/create_match_mapping.py (you already had this!)
# Maps: WhoScored ID → FotMob ID → Team names
```

**Step 4: Use Mapping in SQL**
```sql
-- Instead of direct join (fails):
FROM silver_fotmob_shots WHERE match_id = '1903733'  -- ❌ No rows

-- Use mapping (works):
FROM silver_fotmob_shots fs
JOIN match_mapping mm ON fs.match_id = mm.fotmob_match_id
WHERE mm.whoscored_match_id = '1903733'  -- ✅ Gets shots
```

### What You Should Remember

**Pattern**: `Source A → Mapping Table ← Source B`
- Don't try to unify IDs at scraping time (fragile)
- Create explicit mapping tables (auditable, fixable)
- Document mismatches in engineering diary (future you will thank you)

**When to Use This**:
- Any project combining 2+ data sources
- Customer data platforms (CDP)
- Marketing attribution (Google Ads + Facebook Ads + CRM)
- Sports analytics (WhoScored + FotMob + Opta + StatsBomb)

---

## 🧠 Lesson 2: Search Before Building (The 30-Minute Rule)

### What Happened

**My Mistake**: Spent 20 minutes designing a "team name parser" solution
**Your Fix**: "Check `scripts/create_match_mapping.py` - I already solved this"
**Result**: Saved 40+ minutes by using existing solution

### The Rule

**Before writing ANY code for a problem**:
1. Search codebase: `grep -r "team.*mapping" .` or `rg "fotmob.*whoscored"`
2. Check `/scripts` folder: Often has one-off utilities
3. Check `/data` folder: Intermediate files (CSVs, JSONs) are solutions
4. Check git history: `git log --all --grep="xG"` shows past fixes

**If search takes >5 min and finds nothing → Build new solution**
**If search finds something similar → Adapt existing code**

### Why This Matters in AI Engineering

**AI projects accumulate "glue code"**:
- 100 lines of LLM inference
- 5,000 lines of data wrangling (parsers, mappers, validators)
- The glue code is *always* reusable, but often undocumented

**Your job**: Organize glue code so you (and LLMs) can find it:
- `/scripts`: One-off utilities (mapping creators, data fixers)
- `/src/utils`: Reusable helpers (date parsers, ID validators)
- `README.md`: Index of "if you need X, check Y"

### Pattern Recognition

**These are the same problem**:
- "Match IDs don't align" (sports data)
- "Customer IDs don't align" (SaaS integrations)
- "Session IDs don't align" (analytics platforms)

**Solution template**:
```python
# scripts/create_entity_mapping.py
def create_mapping(source_a_data, source_b_data, common_key):
    """Map IDs from source A to source B using common key (name, email, date)."""
    mapping = {}
    for a_entity in source_a_data:
        for b_entity in source_b_data:
            if fuzzy_match(a_entity[common_key], b_entity[common_key]):
                mapping[a_entity['id']] = b_entity['id']
    return mapping
```

---

## 📊 Lesson 3: dbt Isn't Just SQL - It's Documentation + Testing + Contracts

### Why We Use dbt (Not Plain SQL)

**Dagster alone (what we had)**:
```python
# orchestration/assets/duckdb_assets.py
db.execute("""
    CREATE TABLE silver_events AS
    SELECT id, x, y, type, ...  -- Which columns? What do they mean?
    FROM bronze_events
""")
```
- No documentation (what is `prog_pass`?)
- No tests (is x between 0-100? Is pass_accuracy a percentage?)
- No lineage (which downstream tables break if I change this?)

**dbt (what we built)**:
```yaml
# schema.yml
- name: silver_events
  description: "Event-level tactical data with 23 columns for Gradio visualizers"
  columns:
    - name: prog_pass
      description: "Progressive pass distance in meters (≥9.11 = progressive)"
      tests:
        - not_null
        - dbt_utils.accepted_range:
            min_value: 0
            max_value: 150  # Max possible on 105m pitch
```

**What You Get**:
1. **Self-documenting**: New team member reads YAML, understands data
2. **Automated testing**: `dbt test` catches bad data before it breaks dashboards
3. **Lineage graph**: `dbt docs generate` shows Silver → Gold → Embeddings flow
4. **Column-level contracts**: If you remove `prog_pass`, dbt errors before deploy

### The AI Engineering Insight

**LLMs are consumers of your data**:
- Bad data → LLM hallucinates or refuses to answer
- Undocumented data → You can't write good prompts ("use the prog_pass field" - what's that?)
- Untested data → Silent failures (possession = 150% because sum logic broke)

**dbt solves this**:
```sql
-- Your prompt to LLM references this:
"Calculate pressing intensity using PPDA (passes allowed per defensive action)"

-- dbt ensures PPDA exists and is valid:
tests:
  - dbt_utils.accepted_range:
      min_value: 0
      max_value: 100  # Can't be negative or absurdly high
```

### When to Use dbt vs Plain SQL

**Use dbt when**:
- Data feeds downstream systems (dashboards, LLMs, reports)
- Schema changes break things (multiple consumers)
- Data quality matters (analytics, ML training data)

**Use plain SQL when**:
- One-off analysis ("how many users signed up last week?")
- Exploratory work (still figuring out schema)
- Simple ETL (CSV → database, no transformations)

---

## 🏗️ Lesson 4: Medallion Architecture (Bronze/Silver/Gold) Solves Real Problems

### The Pattern

```
Bronze (Raw) → Silver (Cleaned) → Gold (Aggregated)
   ↓               ↓                    ↓
Raw JSON      23 columns          Match summaries
379 files     279K events         379 rows
Immutable     Validated           LLM-ready
```

### Why Each Layer Exists

**Bronze: "Keep the raw data, always"**
- Scrapers break, APIs change, you made a parsing mistake
- Bronze lets you re-process without re-scraping (saves $$$ and avoids rate limits)
- Example: We didn't extract team names from WhoScored initially → Re-processed Bronze to fix it

**Silver: "Clean once, use everywhere"**
- Standardize types (string "2024-08-09" → date object)
- Add calculated fields (`prog_pass`, `is_shot`, `x_sb`)
- Validate ranges (x: 0-100, y: 0-100, pass_accuracy: 0-100%)
- Downstream consumers trust Silver data (no null checks, no validation)

**Gold: "Aggregate for specific use cases"**
- Match summaries (379 rows) for LLM analysis
- Player stats (18 rows) for individual reports
- Team metrics (378 rows) for tactical comparisons
- Each Gold table serves ONE consumer (LLM, dashboard, API)

### The Real-World Mistake We Avoided

**What we DIDN'T do** (Dagster-only approach):
```python
# BAD: Mixing extraction + transformation + aggregation
def scrape_and_analyze_match(url):
    raw_html = fetch(url)  # Extraction
    events = parse_html(raw_html)  # Transformation
    ppda = calculate_ppda(events)  # Aggregation
    return {"ppda": ppda}  # Lost raw data! Can't recalculate if logic changes
```

**What we DID do** (Medallion):
```python
# Bronze: Extraction only
def scrape_match(url): return raw_html

# Silver: Transformation only
def parse_events(raw_html): return events_df

# Gold: Aggregation only
def calculate_ppda(events_df): return ppda_value
```

**Why This Matters**:
- Your PPDA formula will change (new research, user feedback)
- You'll add new metrics (xT, progressive carries, defensive line height)
- With Medallion, you re-run Gold layer (1 min), not re-scrape 379 matches (3 hours)

---

## 🎓 Lesson 5: The "Match Mapping" Pattern Is Universal

### What We Built

```json
{
  "whoscored_id": "1903733",
  "fotmob_id": "4815204",
  "ws_to_fotmob_team_mapping": {
    "874": "6433",  // Go Ahead Eagles
    "242": "6422"   // Fortuna Sittard
  }
}
```

### Why This Pattern Repeats

**Every integration project has this**:
- E-commerce: Shopify order_id ≠ Stripe charge_id
- Marketing: Facebook ad_id ≠ Google Analytics utm_campaign
- Healthcare: Patient MRN (hospital A) ≠ Patient ID (hospital B)

### The Template (Copy This)

```python
# scripts/create_mapping_{source_a}_{source_b}.py
import json
from pathlib import Path

def create_mapping(source_a_data, source_b_data, common_key_fn):
    """
    Args:
        source_a_data: List of entities from source A
        source_b_data: List of entities from source B
        common_key_fn: Function to extract comparable key (name, email, etc.)

    Returns:
        {source_a_id: source_b_id, ...}
    """
    mapping = {}
    for a_entity in source_a_data:
        a_key = common_key_fn(a_entity)
        for b_entity in source_b_data:
            b_key = common_key_fn(b_entity)
            if a_key == b_key:  # Or use fuzzy match
                mapping[a_entity['id']] = b_entity['id']
                break
    return mapping

def save_mapping(mapping, output_path):
    """Save mapping to JSON for loading into database."""
    with open(output_path, 'w') as f:
        json.dump(mapping, f, indent=2)
```

### How to Use in SQL

```sql
-- Load mapping into database (one-time)
CREATE TABLE mapping AS SELECT * FROM read_json('mapping.json');

-- Use in joins
SELECT
    a.data,
    b.data
FROM source_a a
JOIN mapping m ON a.id = m.source_a_id
JOIN source_b b ON m.source_b_id = b.id
```

---

## 🚀 Lesson 6: What Actually Matters in AI Engineering

### You Might Think AI Engineering Is:

❌ Writing complex transformer architectures
❌ Fine-tuning GPT models
❌ Building novel retrieval algorithms
❌ Prompt engineering wizardry

### It's Actually:

✅ **80%: Data wrangling** (today's work - joining WhoScored + FotMob)
✅ **10%: Data quality** (dbt tests, validation, monitoring)
✅ **5%: Integration** (API design, error handling, retries)
✅ **5%: ML/LLM work** (prompts, embeddings, evaluation)

### The Hidden Skills You're Learning

**Today, you learned**:
1. Multi-source data reconciliation (mapping tables)
2. SQL aggregations (PPDA, field tilt, compactness)
3. Data quality testing (dbt schema validation)
4. Pipeline architecture (Bronze → Silver → Gold)
5. Documentation patterns (schema.yml, engineering diaries)

**These skills apply to**:
- RAG systems (retrieving clean, validated data for LLMs)
- ML pipelines (training data preparation)
- Analytics platforms (BI dashboards, reports)
- Data products (APIs serving aggregated data)

### The Career Insight

**Junior AI Engineer** (6 months):
- Writes prompts, runs model inference
- Assumes data is clean
- Frustrated when results are bad ("LLM is broken!")

**Senior AI Engineer** (3+ years):
- Spends 80% time on data quality
- Knows garbage in = garbage out
- Builds pipelines that produce reliable data for models

**You're learning Senior patterns now** (match mapping, dbt testing, Medallion architecture). Most bootcamps skip this and focus on model training. That's why they produce juniors who can't ship production systems.

---

## 🔧 Practical Patterns You Can Copy

### Pattern 1: Mapping Table Template

```sql
-- Always store mappings as tables, not code
CREATE TABLE entity_mapping (
    source_a_id VARCHAR,
    source_b_id VARCHAR,
    entity_name VARCHAR,  -- For debugging
    confidence FLOAT,      -- For fuzzy matches
    created_at TIMESTAMP   -- For auditing
);
```

### Pattern 2: dbt Testing Template

```yaml
# Every metric should have range validation
- name: ppda
  description: "Passes allowed per defensive action"
  tests:
    - not_null
    - dbt_utils.accepted_range:
        min_value: 0
        max_value: 100  # Sanity check (can't be negative)
```

### Pattern 3: Engineering Diary Template

```markdown
# YYYY-MM-DD: Feature/Fix Name

## Problem
- Symptom: xG = 0
- Root cause: ID mismatch between sources

## Solution
- Created mapping table
- Updated SQL join

## Lessons
- Always search /scripts before building
- Document weird data quirks
```

---

## 📚 What to Study Next

**To level up your data engineering** (80% of AI Engineering):
1. **dbt Fundamentals** (free course): Learn incremental models, snapshots, macros
2. **SQL Window Functions**: Essential for time-series analysis (running averages, cumulative stats)
3. **Data Quality Frameworks**: Great Expectations, dbt tests, data contracts

**To level up your AI engineering** (the other 20%):
1. **Vector Databases**: Next step (DuckDB VSS, Pinecone, Weaviate)
2. **RAG Evaluation**: LangSmith, Ragas, custom faithfulness metrics
3. **LLM Observability**: Opik, LangSmith, tracing request flows

**But honestly**: Master the data layer first. Most failed AI projects fail on data, not models.

---

## 🎯 TL;DR - The 5 Things to Remember

1. **Data quality beats model quality** - Fix xG before improving prompts
2. **Search before building** - Check /scripts, /data, git history first
3. **Multi-source joins need mapping tables** - WhoScored ≠ FotMob, Shopify ≠ Stripe
4. **dbt = documentation + testing + contracts** - Not just SQL transformation
5. **AI Engineering is 80% data wrangling** - Get comfortable with it

---

**Written**: 2026-02-15
**For**: Ricardo (student) by Claude (mentor)
**Context**: Phase 1 completion - Silver layer + xG fix
**Remember**: You're learning the hard parts (data) that bootcamps skip. This is good.
