---
name: row-counts
description: Check DuckDB table row counts for data pipeline verification. Use when user asks "check row counts", "verify data", "table sizes", "how many rows", or during pipeline debugging.
version: 1.0.0
metadata:
  author: Ricardo Heredia
  category: data-validation
  tags: [duckdb, data-quality, pipeline, verification]
---

# Row Counts Verification

Quick DuckDB table row count checker for Medallion pipeline validation.

## When to Use

Trigger when user:
- Says "check row counts", "table sizes", "how many rows"
- Wants to verify pipeline ran correctly
- Is debugging data issues
- Mentions specific table names (bronze_matches, silver_events, gold_match_summary, etc.)

## Instructions

### Step 1: Identify Tables to Check

**If user specifies tables**: Check only those
**If no specification**: Check ALL tables in standard pipeline:
- `bronze_matches`
- `silver_events`
- `silver_fotmob_shots`
- `gold_match_summary`
- `gold_player_stats`

### Step 2: Execute DuckDB Query

```bash
duckdb data/lakehouse.duckdb "
SELECT
  table_name,
  COUNT(*) as row_count
FROM {table_name}
GROUP BY table_name
ORDER BY table_name;
"
```

**For multiple tables** (run single query):
```sql
SELECT 'bronze_matches' as table, COUNT(*) as rows FROM bronze_matches
UNION ALL
SELECT 'silver_events', COUNT(*) FROM silver_events
UNION ALL
SELECT 'silver_fotmob_shots', COUNT(*) FROM silver_fotmob_shots
UNION ALL
SELECT 'gold_match_summary', COUNT(*) FROM gold_match_summary
UNION ALL
SELECT 'gold_player_stats', COUNT(*) FROM gold_player_stats;
```

### Step 3: Report Results

Format output as table:

```
📊 DuckDB Table Row Counts
==========================
bronze_matches      : 379
silver_events       : 279,104
silver_fotmob_shots : 5,345
gold_match_summary  : 378
gold_player_stats   : 499
```

### Step 4: Validation Checks

After showing counts, flag anomalies:
- ❌ **0 rows**: Table exists but empty (pipeline failure?)
- ⚠️ **Unexpected drop**: If count decreased from known baseline
- ✅ **Expected ranges**: Confirm counts match known good state

## Common Scenarios

**Scenario 1: Post-pipeline run**
User: "Did the pipeline work?"
→ Check all tables, compare to baseline

**Scenario 2: Debugging**
User: "Why is gold_match_summary showing 0?"
→ Check upstream dependencies (silver tables)

**Scenario 3: Before migration**
User: "Save baseline counts"
→ Run query, format as baseline reference

## Error Handling

If table doesn't exist:
```
❌ Table '{table_name}' not found in data/lakehouse.duckdb
Available tables: [list from `SHOW TABLES`]
```

If DuckDB file missing:
```
❌ DuckDB file not found: data/lakehouse.duckdb
Has the pipeline been run? Check with: ls -lh data/
```
