# Engineering Diary: Wordalisation v4.0 — Football Language Pipeline
**Date:** 2026-02-28
**Tags:** `wordalisation`, `prompt-engineering`, `edd`, `llm`, `classify-metrics`, `football-language`, `context-engineering`

## 1. Problem Statement

The existing pipeline (`v3.5_balanced`) explicitly instructed the LLM to "state only what metrics
directly prove" and use "technical terminology, neutral tone". This produced data recitation —
the LLM echoed raw numbers from the user prompt instead of interpreting them tactically. Output
looked like a data dashboard, not a scouting report:

> "Home xG was 1.2 and they scored 3 goals. Away PPDA was 4.8..."

The root cause was architectural: we were passing raw numeric values to a model that knows football
language perfectly well, then constraining it to not use that language. The LLM's football
knowledge was locked behind a statistical straightjacket.

Additionally, the evaluation suite lacked a `football_language` criterion — we were measuring
*specificity* and *visual grounding* but not whether the prose actually sounded like human
analysis.

## 2. Approach

Applied the **Wordalisation principle** (Sumpter / arXiv 2504.00767): a two-stage pipeline where
raw metrics are classified into qualitative English labels *before* the LLM call. The LLM never
sees numbers — only football-language descriptions of what those numbers mean.

Combined with **Context Engineering** best practices from the Towards AI Academy course:
- XML tags to isolate context blocks (`<match_context>`, `<tactical_labels>`, `<few_shot_examples>`)
- YAML format for structured data (more token-efficient than JSON)
- Static content (few-shot examples) before dynamic content (match labels) — enables prompt caching
- Instructions at both START (system prompt) and END (`<instructions>`) to prevent lost-in-the-middle

**Key architectural decision**: Model upgraded from `claude-haiku-4-5-20251001` → `claude-sonnet-4-6`.
Haiku could produce labels correctly but lacked the narrative range needed for scouting-report
prose. Sonnet produces continuous editorial flow naturally.

**Key Changes:**
- `src/football_rag/analytics/metrics.py`: Added `classify_metrics(metrics: dict) -> dict` — 17
  English labels covering press style, shot quality, field position, defensive line, result
  fairness, progression advantage, press dominance. Handles dual key formats (`home_progressive_passes`
  AND `home_pp` via `.get()` fallbacks) because `to_prompt_variables()` uses short keys.
- `src/football_rag/models/generate.py`: Model `claude-haiku-4-5-20251001` → `claude-sonnet-4-6`
- `prompts/prompt_versions.yaml`: Added `v4.0_tactical` — continuous prose system prompt, XML-tagged
  YAML user prompt, two post-match few-shot examples (scouting-report style, no headers, no raw numbers)
- `src/football_rag/models/rag_pipeline.py`: Wired `classify_metrics()` into `run()`, default
  `prompt_version` changed to `v4.0_tactical`, `**labels` merged into `formatted_prompt`
- `tests/test_edd.py`: `GOLDEN_DATASET_NAME` → `"football-rag-golden-v4"`, `tactical_insight`
  scorer extended to 4 equal-weight components (0.25 each) including new `football_language`
  criterion; 13 parametrized test cases (was 10)
- `data/eval_datasets/tactical_analysis_eval.json`: 3 new cases targeting language quality:
  `match_11_language_quality_press`, `match_12_language_quality_xg`, `match_13_language_quality_narrative`
- `.claude/skills/prompt-workshop/SKILL.md`: New skill for rapid prompt iteration without full EDD
- `.claude/skills/session-brief/SKILL.md`: New skill for token-efficient session onboarding

## 3. Verification

**Smoke test** — "Analyze the Heracles vs PEC Zwolle match" (the blowout match, most extreme case):

Output excerpt:
> "Heracles set up to frustrate, sitting deep and inviting PEC Zwolle to come at them — a coherent
> enough plan in isolation, but one that demanded defensive discipline and clinical use of the rare
> moments they could hurt the visitors on the break... a low block without the finishing to punish
> opponents on the counter is simply a slow surrender."

Criteria check:
- ✅ No raw numbers cited
- ✅ Continuous prose (no headers, no bullet points)
- ✅ Football language throughout (deep block, counter-attacking, high line, transition)
- ✅ Explains WHY, not just WHAT
- ✅ Both teams covered
- ✅ Non-obvious conclusion ("slow surrender")

**Tests Run:**
- `uv run pytest` (unit tier): all passing

**Metrics:**
- 7 files changed, 284 insertions, 23 deletions
- `classify_metrics()` outputs 17 string labels (zero floats passed to LLM)
- EDD test cases: 10 → 13 (3 new language-quality cases)
- Scorer components: 3 → 4 (added `football_language` at 0.25 weight)

## 4. Lessons Learned

**The constraint was the problem, not the model.** The LLM already knew how to write football
prose. The v3.5 system prompt constrained it to data recitation. Removing the constraint (by
pre-classifying into labels) unlocked the output immediately — no fine-tuning needed.

**Key mapping gotcha**: `to_prompt_variables()` in `schemas.py` returns short keys (`home_pp`,
`home_press`, `home_pos`, `home_def`) while the metrics classifier was written expecting full keys.
Always use dual `.get()` fallbacks when bridging schema layers:
```python
home_high_press = metrics.get("home_high_press", metrics.get("home_press", 0))
```

**Few-shot examples are the unlock**: Two post-match analysis examples in the few-shot block
immediately shaped the prose style to match. The LLM pattern-matched to editorial football writing
without any instruction to "write like this". The examples do more work than explicit instructions.

**YAML over JSON for structured context**: The `<tactical_labels>` block in YAML format is
noticeably more compact than the equivalent JSON and reads more naturally alongside prose examples.

## 5. Next Steps

- **Run full EDD** (`uv run pytest tests/test_edd.py -v -m edd --run-edd`) against v4.0_tactical
  to score all 13 cases. Update `v4.0_tactical: score:` in `prompt_versions.yaml` with actual result.
- **First formal release v0.4.0** — CI must be green, then use `/release` skill
- **EDD in CI** — GitHub Actions `workflow_dispatch`-gated job so evaluation is reproducible
- **HF_TOKEN in GitHub Secrets** — needed for `deploy_job` automation from CI
- **`/prompt-workshop`** — use to iterate on v4.0 if EDD score < 0.75 on any case
