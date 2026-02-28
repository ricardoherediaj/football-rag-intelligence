---
name: prompt-workshop
description: Side-by-side comparison of prompt versions on a real match to iterate on output quality. Use when user says "workshop the prompt", "test prompt versions", "compare prompt output", "prompt brainstorm", or wants to improve commentary quality.
version: 1.0.0
metadata:
  author: Ricardo Heredia
  category: llm-engineering
  tags: [prompt, evaluation, wordalisation, iteration, commentary]
---

# Prompt Workshop

Iterates on prompt quality by running the pipeline on a real match and comparing outputs.
Designed for rapid evaluation cycles without running the full EDD suite.

## When to Use

Trigger when user:
- Says "workshop the prompt", "test the prompt", "compare prompt versions"
- Wants to improve commentary quality (language, tone, depth)
- Says "the output sounds wrong" or "it's still reciting numbers"
- Wants to test a new few-shot example or system prompt change

## Instructions

### Step 1: Read Current Active Version

```bash
grep -A 3 "v4.0_tactical:" prompts/prompt_versions.yaml | head -5
```

Show the current version name and its score (null = not yet evaluated).

### Step 2: Run Baseline Output

Run the pipeline on the canonical test match (Heracles vs PEC Zwolle — blowout case,
best for spotting language quality issues):

```bash
uv run python -c "
from football_rag.orchestrator import query
r = query('Analyze the Heracles vs PEC Zwolle match')
print(r.get('commentary', r.get('error')))
"
```

Show the output to the user under `## Current Output`.

### Step 3: Diagnose Weaknesses

Evaluate the output against these criteria:
1. **Football language** — Does it sound like a scouting report or a data dashboard?
2. **WHY vs WHAT** — Does it explain why things happened, not just what happened?
3. **Raw numbers** — Are there any leaked numbers (xG=x.xx, PPDA=x.xx, "12 shots")?
4. **Tactical connections** — Does it link patterns together (e.g., high line → exposed on counter)?
5. **Both teams** — Are both sides covered with balanced perspective?
6. **Non-obvious conclusion** — Does it end with something a casual fan wouldn't think of?

List 2-3 specific weaknesses found.

### Step 4: Propose a Change

Either:
- Ask the user: "What do you want to change?" (if they have an idea)
- Or propose the most impactful fix based on the diagnosis

Focus on ONE change at a time:
- System prompt wording tweak
- Adding/replacing a few-shot example
- Changing the format of tactical_labels in the user_prompt
- Adjusting the instructions block

### Step 5: Apply and Re-run

Apply the proposed change IN MEMORY (do NOT write to yaml yet). Re-run the pipeline
with the candidate prompt using a direct API call:

```python
from football_rag.models.generate import generate_with_llm
from football_rag.prompts_loader import load_prompt
from football_rag.analytics.metrics import classify_metrics

# Load current metrics for Heracles vs PEC Zwolle (match_id 1904034)
# Then format with candidate system + user prompt and call generate_with_llm
```

Show output under `## Candidate Output`.

### Step 6: Side-by-Side Assessment

Present:

```
## Current Output
{current_commentary}

## Candidate Output
{candidate_commentary}

## Assessment
| Criterion | Current | Candidate |
|---|---|---|
| Football language | ✅/⚠️/❌ | ✅/⚠️/❌ |
| WHY reasoning | ✅/⚠️/❌ | ✅/⚠️/❌ |
| No raw numbers | ✅/⚠️/❌ | ✅/⚠️/❌ |
| Tactical connections | ✅/⚠️/❌ | ✅/⚠️/❌ |
| Both teams covered | ✅/⚠️/❌ | ✅/⚠️/❌ |
| Non-obvious conclusion | ✅/⚠️/❌ | ✅/⚠️/❌ |

Verdict: {Improved / Regressed / Mixed}
```

### Step 7: Commit or Discard

Ask: "Save this as the new active version?"

- **Yes**: Write new version to `prompts/prompt_versions.yaml` with a version bump
  (e.g., `v4.1_tactical`), update `rag_pipeline.py` default if needed, and note
  that the EDD golden dataset name should be bumped before running full eval.
- **No**: Discard and return to Step 3 with a different hypothesis.

## Rules

- Never run full EDD during a workshop session — that's expensive and slow
- Always test on Heracles vs PEC Zwolle first (extreme case, easiest to spot issues)
- ONE change per iteration — don't stack multiple changes before evaluating
- If the candidate is worse, note WHY before trying something else
- Don't touch the few-shot examples unless language quality is the specific issue

## Post-Workshop

After a successful improvement:
1. Remind user to bump `GOLDEN_DATASET_NAME` in `test_edd.py` before next EDD run
2. Suggest running `/quick-test` to check nothing else broke
