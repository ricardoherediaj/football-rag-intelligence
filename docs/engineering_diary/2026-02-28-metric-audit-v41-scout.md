# Engineering Diary — 2026-02-28 — Metric Audit, Migration & v4.1 Scout Prompt

## Session Goal

Fix two metric calculation bugs found during audit, migrate silver_team_metrics from dbt to Python Dagster asset, recalibrate Wordalisation labels with real Eredivisie distributions, and improve LLM output quality from editorial to scout-style prose.

## Bugs Found

### Bug A: Progressive Passes Coordinate System
- **Root cause**: `count_progressive_passes()` used goal coordinates `(105, 34)` (UEFA pitch dimensions) but WhoScored uses normalized `0-100 x 0-100` coordinate system where goal is at `(100, 50)`
- **Fix**: Changed goal to `(100, 50)`, threshold from `9.11` (UEFA meters) to `8.68` (WhoScored units, scaled by 100/105)
- **Impact**: Minimal — p50 progressive passes barely changed (154→149) because the coordinate shift mostly cancels the threshold change for typical forward passes

### Bug B: Compactness Divisor
- **Root cause**: `calculate_compactness()` used divisor `120` (StatsBomb field length) but our data uses WhoScored's `0-100` normalized coordinates
- **Fix**: Changed divisor from `120` to `100`
- **Impact**: Significant — p50 compactness dropped from 54.55 to 35.8 (the field is "shorter" in WhoScored units, so the same inter-line distance represents a larger proportion)

### Bug C: Goals NULL in Gold Layer
- **Root cause**: `calculate_all_metrics()` never returned `home_goals`/`away_goals` keys, but `_COL_MAP` in metrics_assets.py mapped them → gold layer had NULL goals → `MatchContext` validation failed
- **Fix**: Added goals counting (events with type "Goal") to the return dict

## Migration: dbt → Python Dagster Asset

**Why**: The dbt SQL model couldn't call Python metric functions (progressive passes, PPDA zone filtering, compactness). Having metrics in two places (Python for classify, SQL for storage) created drift risk.

**Architecture**:
```
dbt_silver_models (silver_events)
    → silver_team_metrics (Python asset, calls calculate_all_metrics())
        → dbt_gold_models (gold_match_summaries, reads via source())
            → gold_match_embeddings
```

**Key decisions**:
- Write to `main` schema (not `main_main`) because `sources.yml` resolves `source('football_rag', 'silver_team_metrics')` to `lakehouse.main.silver_team_metrics`
- Long format output: one row per (match_id, team_id) with unprefixed columns to match the gold JOIN pattern
- `_COL_MAP` renames prefixed keys (e.g. `home_tackles → successful_tackles`) for dbt compatibility

## Wordalisation Recalibration

### Data-driven thresholds (Eredivisie 2024-25 real distributions)
```
ppda:        p25=6.0,  p50=7.4,  p75=9.2
high_press:  p25=5,    p50=6,    p75=8
def_line:    p25=9.4,  p50=11.1, p75=13.5
position:    p25=43.6, p50=47.4, p75=54.0
compactness: p25=33.0, p50=35.8, p75=38.0
field_tilt:  p25=46.5, p50=57.7, p75=67.9
shots:       p25=12,   p50=16,   p75=20
```

### PMDS-informed labels
Inspired by 360 Scouting framework (Position-Moment-Direction-Speed):
- Replace catch-all terms ("high_press_intensity") with action descriptions ("pressed_aggressively_allowing_few_passes")
- Each label describes what the team DID, not a statistical bucket

### New dimensions added
- `compactness`: stretched_shape / compact_block / very_narrow
- `territorial_dominance`: dominated_final_third / shared / penned_back
- `possession_style`: controlled_extensively / shared / conceded_the_ball

## Prompt v4.1_scout

### Problem with v4.0_tactical
The system prompt + few-shot examples actively pushed the model toward editorial writing:
- "Prioritise WHY over WHAT" → philosophical tangents
- "End with a non-obvious tactical conclusion" → rhetorical pirouettes
- Few-shot examples used literary language ("paradoxically", "at the heart of")

### Fix
- System prompt: "scout's internal report, not newspaper column"
- Hard rules: 3 paragraphs, 2-3 sentences each, each sentence = one finding
- Banned cliches list: "paradox", "non-obvious", "at the heart of", "remains", "ultimately"
- Single reference_style example in scout tone instead of two novelistic examples
- Final sentence rule: "the sharpest observation, not a conclusion"

### Result
Before: "The non-obvious conclusion here is that Heracles' compactness, which should theoretically limit space, was rendered irrelevant..."
After: "Heracles's defensive block did not break catastrophically in shape, but the absence of any ball-near pressing trigger meant Zwolle could recycle possession at will..."

## Verification

- 20/20 unit tests pass
- Pipeline: 428 rows in silver_team_metrics, 214 matches in gold, 214 embeddings
- LLM smoke test with Anthropic API: v4.1_scout output is dense, informative, no filler
- Pre-commit hooks: all pass (ruff, format, detect-secrets)

## PR

https://github.com/ricardoherediaj/football-rag-intelligence/pull/10

## Next Steps

- Merge PR after CI passes
- Run full EDD with v4.1_scout to get a score
- First formal release v0.4.0 (tags Phase 4a + MLOps + Wordalisation + Metric Audit)
- Fix xG data (fotmob match_mapping has gaps — all xG is 0 for some matches)
