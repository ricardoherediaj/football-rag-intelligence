# Phase 2: Prompt Engineering & Testing

## Quick Start Guide

### Files Created
1. **[tactical_analysis_v1_baseline.txt](tactical_analysis_v1_baseline.txt)** - Baseline prompt template
2. **[sample_match_heracles_vs_pec.txt](sample_match_heracles_vs_pec.txt)** - Pre-formatted match data for testing
3. **[../docs/PHASE2_PROMPT_TESTING.md](../docs/PHASE2_PROMPT_TESTING.md)** - Test results documentation template

### Testing Workflow

#### Step 1: Open Anthropic Console
- Go to https://console.anthropic.com
- Select Claude 3.5 Sonnet (or latest model)

#### Step 2: Set Up System Prompt
1. Open `tactical_analysis_v1_baseline.txt`
2. Copy the **SYSTEM PROMPT** section
3. Paste into the "System" field in Console

#### Step 3: Test With Match Data
1. Open `sample_match_heracles_vs_pec.txt`
2. Copy the match data (from "**Match Details:**" onwards)
3. Paste as user message in Console
4. Generate analysis

#### Step 4: Score the Output
Use the rubric from `PHASE2_PROMPT_TESTING.md`:

- **Tactical Insight Quality (1-5)**: Does it explain *why* things happened?
- **Data Grounding (1-5)**: Are claims backed by specific numbers?
- **Actionable Recommendations (1-5)**: Can coaches use this?
- **Coherence & Structure (1-5)**: Is it well-organized?

**Target**: Average score ≥ 4.0

#### Step 5: Document Results
1. Open `../docs/PHASE2_PROMPT_TESTING.md`
2. Fill in the test results for Match 1
3. Note strengths and weaknesses

#### Step 6: Iterate
If score < 4.0, modify the prompt:
- Add more specific instructions
- Add constraints (e.g., "MUST reference xG data")
- Add few-shot examples
- Refine the required analysis structure

Repeat Steps 2-5 with the new prompt version.

### Why This Match is a Good Test

The Heracles vs PEC Zwolle match (2-8) is an excellent test case because:

1. **Statistical Anomaly**: PEC scored 8 goals from only 1.14 xG (7x overperformance)
2. **Paradox**: Heracles had more shots (24 vs 7) and higher xG (4.51 vs 1.14) but lost badly
3. **Clear Tactical Story**: PEC dominated with pressing (16 vs 2 events) and progressive passes (101 vs 55)
4. **Rich Metrics**: Multiple dimensions to analyze (xG, positioning, pressing, passing)

A good prompt should:
- ✓ Identify the xG overperformance as the key insight
- ✓ Explain the paradox (how PEC won despite lower xG)
- ✓ Reference multiple tactical dimensions
- ✓ Provide actionable insights for coaches

### Next Steps After Finding Winning Prompt

1. Test with remaining 9 evaluation matches (use `tactical_analysis_eval.json`)
2. Ensure consistent quality across all matches
3. Document the winning prompt version
4. Save insights for Phase 3 (RAG implementation):
   - What context format works best?
   - Which metrics are critical?
   - What output structure is most useful?

### Tips for Iteration

**If outputs are too generic:**
- Add constraints: "Must reference at least 4 specific metrics"
- Add examples of good vs bad analysis

**If outputs ignore xG data:**
- Make xG analysis mandatory: "xG Analysis section is REQUIRED"
- Add specific xG-related questions

**If recommendations are vague:**
- Ask for "specific, actionable recommendations tied to data"
- Provide example: "Focus on finishing training: 4.51 xG converted to only 2 goals"

**If structure is poor:**
- Make section headings mandatory
- Specify order: Overview → Insights → xG → Pressing → Progression → Recommendations

### Questions?

See [CLAUDE.md](../CLAUDE.md) for project guidelines or [EVALUATION_DATASET_PLAN.md](../docs/EVALUATION_DATASET_PLAN.md) for context on the evaluation dataset.
