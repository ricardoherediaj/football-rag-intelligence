---
name: session-brief
description: Summarize recent project work and next steps to get up to speed fast at session start. Reads git log, SCRATCHPAD, CHANGELOG, and latest diary. Token-efficient — no full file loads. Use when user says "brief me", "catch me up", "session brief", "what did we do", "where did we leave off", or starts a new session.
version: 1.0.0
metadata:
  author: Ricardo Heredia
  category: project-management
  tags: [session, onboarding, context, summary, next-steps]
---

# Session Brief

Gets the developer up to speed in < 30 seconds. Token-efficient by design — read only what's needed, never load full files.

## When to Use

Trigger when user:
- Starts a new session ("catch me up", "brief me", "session brief")
- Says "where did we leave off" or "what did we do last time"
- Opens a new conversation and wants context
- Asks "what's next" without a specific task in mind

## Instructions

Execute steps in order. Each step is a single targeted read — no full file dumps.

### Step 1: Recent Commits (last 5)

```bash
git -C . log --oneline -5
```

Extract: what areas were touched (scope tokens like `feat/`, `fix/`, `chore/`), last commit date.

### Step 2: SCRATCHPAD — Current State + Next Session only

Read `.claude/SCRATCHPAD.md` but extract ONLY:
- `## Current State` section → branch, status, Pipeline Status table
- `## Next Session` section → prioritized TODO list

Do NOT load Historical Reference or Gotchas sections.

### Step 3: CHANGELOG — Latest Entry

```bash
grep -m 1 "^## \[" CHANGELOG.md
```

Then read only the block between that heading and the next `## [` heading (typically 10–20 lines).

### Step 4: Latest Engineering Diary — First 30 Lines

```bash
ls -t docs/engineering_diary/*.md | head -1
```

Then read lines 1–30 of that file (title, goal, what was completed). Skip implementation details.

### Step 5: Compose Brief

Format as a tight markdown brief — NO preamble, NO "here is your brief":

````markdown
# Session Brief — {today's date}

## Last Work
**{N} commits since {date}** — {one-line summary of themes}
> {commit 1}
> {commit 2}
> ...

## Pipeline Status
| Layer | Status | Count |
|---|---|---|
{rows from SCRATCHPAD — only ✅/❌ rows, omit ⏳ pending layers}

## Latest Release / Milestone
**{CHANGELOG entry heading}** — {2-sentence summary of what landed}

## Next Steps (priority order)
1. **{Task 1}** — {one-line why + first action}
2. **{Task 2}** — {one-line why + first action}
3. **{Task 3}** — {one-line why}

## Jump In
**Immediate action:** `{first command or file to open}`
````

## Rules

- **Never** load full CHANGELOG, full diary files, or full git log
- **Never** explain what you're doing — output the brief directly
- If SCRATCHPAD is missing, fall back to git log + CHANGELOG only and note it
- Keep the entire brief under 40 lines
- If a Next Step requires a specific skill, mention it: e.g., "Use `/release` to tag v0.4.0"

## Post-Brief

After showing the brief, ask ONE question:
> "Ready to start on **{top next step}**, or anything else first?"

Do not propose a todo list — let the user direct.
