# Data Architecture Explained: Medallion & Vector Search

## 1. The Medallion Architecture (Bronze -> Silver -> Gold)

We have organized our DuckDB lakehouse into three distinct layers. This is a standard pattern in modern data engineering (popularized by Databricks) that ensures reliability, quality, and performance.

### 🥉 Bronze Layer: The "Raw" Landing Zone
*   **Table:** `raw_matches_bronze`
*   **What is it?** A direct copy of the source JSON files (WhoScored, Fotmob) loaded into the database without modification.
*   **Columns:** `match_id`, `source` (e.g., 'whoscored'), `data` (Raw JSON blob).
*   **Why do we need it?**
    *   **Immutability:** If our logic in Silver/Gold is wrong, we never have to re-scrape. We just re-run the transformation from Bronze.
    *   **Auditability:** We can always verify exactly what the scraper returned.
    *   **Schema Evolution:** If WhoScored adds a new field, the ingestion doesn't break because we store the whole JSON blob.

### 🥈 Silver Layer: The "Cleansed" Zone
*   **Tables:** `silver_events`, `silver_fotmob`
*   **What is it?** Data that is flattened, typed, and normalized.
*   **Transformation:**
    *   Unpacking nested JSON arrays (e.g., extracting `events` list).
    *   Casting strings to integers/floats (e.g., `x`, `y` coordinates).
    *   Handling nulls and standardize naming (`eventType` -> `event_type`).
*   **Why do we need it?**
    *   **Queryable:** You can now write standard SQL (`SELECT * FROM silver_events WHERE is_goal = TRUE`).
    *   **Analyst-Ready:** A data analyst (or you) can understand this schema without knowing the complex JSON nesting of the web scraper.

### 🥇 Gold Layer: The "Aggregated" Business Zone
*   **Table:** `gold_shooting_stats`
*   **What is it?** Highly customized aggregations ready for specific use cases (like RAG or Dashboards).
*   **Transformation:**
    *   Aggregating event logs into player-level stats (Sum of goals, average shot distance).
    *   Joining multiple sources (e.g., combining WhoScored positional data with Fotmob xG).
*   **Why do we need it?**
    *   **RAG Optimization:** LLMs are terrible at calculating "sum of goals" from 1000 event rows. They need the final number. Gold tables provide the precise context chunks the LLM needs.
    *   **Performance:** Reading 1 pre-calculated row is faster than scanning 1 million events.

---

## 2. DuckDB VSS (Vector Similarity Search)

### What is it?
DuckDB VSS is an extension that allows the database to store and search "Vectors" (lists of numbers representing meaning) alongside normal data.

### How does it work here?
In `gold_shooting_stats`, we added a column for embeddings.
`CREATE INDEX shots_vss_idx ON gold_shooting_stats USING HNSW (embedding)`

### Why VSS inside DuckDB?
Traditionally, you would extract data from your DB, embed it, and move it to a vector DB like Pinecone or Chroma. Using DuckDB VSS offers a **Hybrid Search** advantage:

**Scenario:** "Find me strikers similar to Haaland (Vector) who played > 1000 minutes (SQL)."

*   **Standard RAG:**
    1.  Query Pinecone for "similar to Haaland" -> Get 100 results.
    2.  Filter those 100 in Python for "> 1000 mins".
    3.  Problem: You might end up with 0 results if the top 100 were all bench players.
*   **DuckDB VSS:**
    1.  Single Query: `SELECT * FROM gold_players WHERE minutes > 1000 ORDER BY array_distance(embedding, [haaland_vector]) LIMIT 5`.
    2.  Result: The database handles the filtering *before* or *during* the vector sort, guaranteeing you get the best matches that actually fit the criteria.

### Impact on your RAG Pipeline
1.  **Lower Latency:** No network calls to external vector DBs.
2.  **Simpler Stack:** Your "Database" and your "Vector Store" are the same single file (`lakehouse.duckdb`).
3.  **Better context:** You can return the *actual* stats columns (goals, xG) along with the vector match immediately.
