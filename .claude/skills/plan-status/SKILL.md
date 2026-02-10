---
name: plan-status
description: Show current implementation plan progress with checklist status. Use when user asks "plan status", "where are we", "check plan", "show progress", or wants to see remaining work.
version: 1.0.0
metadata:
  author: Ricardo Heredia
  category: project-management
  tags: [planning, progress, checklist, status]
---

# Plan Status Checker

Displays current plan progress from `~/.claude/plans/` with checklist visualization.

## When to Use

Trigger when user:
- Says "plan status", "where are we", "show progress"
- Asks "what's next" or "what's left"
- Wants to review implementation plan
- Mentions "checklist" or "validation"

## Instructions

### Step 1: Find Active Plan

```bash
ls -t ~/.claude/plans/*.md | head -1
```

If multiple plans or user specifies: ask which one

### Step 2: Parse Plan File

Read the plan and extract:
1. **Context**: What's the goal?
2. **Success Criteria**: Checkboxes at bottom
3. **Implementation Steps**: Numbered phases
4. **Current State**: Which phase are we in?

### Step 3: Determine Progress

Analyze to calculate:
- Total checklist items
- Completed items (✅ or [x])
- Pending items ([ ])
- Current phase/step

**Heuristics:**
- Check git log for recent work matching plan steps
- Check file existence for files mentioned in plan
- Review CHANGELOG for completed items

### Step 4: Generate Status Report

Format as:

````markdown
# 📋 Plan Status: {Plan Title}

## 🎯 Goal
{Extract from plan context section}

## 📊 Progress: {X}/{Y} Complete ({Z%})

### ✅ Completed
- [x] {Item 1} - Done: {evidence}
- [x] {Item 2} - Done: {evidence}

### 🔄 In Progress
- [ ] {Current item} - Status: {details}

### ⏳ Pending
- [ ] {Future item 1}
- [ ] {Future item 2}

## 🎯 Next Action
**Immediate:** {Most important next step}
**File:** `{file to work on}`
**Command:** `{command to run}`

## 🚦 Blockers
{Any identified blockers or "None detected"}
````

### Step 5: Evidence Gathering

For completed items, show proof:
- ✅ File exists: `ls {file}`
- ✅ Tests pass: Reference test runs
- ✅ Code committed: `git log --grep="{topic}"`
- ✅ Documented: Reference CHANGELOG or diary

### Step 6: Suggest Next Steps

Based on progress:
1. **If phase complete**: "Ready to move to Phase {N+1}"
2. **If blocked**: "Address blocker: {issue}"
3. **If on track**: "Continue with: {next item}"

## Example Output

````markdown
# 📋 Plan Status: dbt Migration (Phase 1)

## 🎯 Goal
Migrate SQL transformations from Python strings to dbt models for version control and testability.

## 📊 Progress: 3/10 Complete (30%)

### ✅ Completed (Phase 1: Days 1-3)
- [x] Install dbt-duckdb and dagster-dbt - Done: `uv.lock` updated
- [x] Initialize dbt project - Done: `dbt_project/` exists
- [x] Create sources.yml - Done: `dbt_project/models/sources.yml` exists

### 🔄 In Progress
- [ ] Migrate silver_events.sql - Status: File created, needs testing

### ⏳ Pending (Phase 2-5)
- [ ] Migrate gold tables
- [ ] Add dbt tests
- [ ] Dagster integration
- [ ] MotherDuck sync setup
- [ ] Observability implementation

## 🎯 Next Action
**Immediate:** Verify silver_events row counts match Python implementation
**File:** `dbt_project/models/silver/silver_events.sql`
**Command:** `dbt run --select silver_events && dbt test --select silver_events`

## 🚦 Blockers
None detected - on track for Phase 1 completion
````

## Common Scenarios

**Scenario 1: User lost track**
User: "Where are we in the plan?"
→ Show full status report with context

**Scenario 2: Quick check**
User: "What's next?"
→ Show only "Next Action" section

**Scenario 3: Validation**
User: "Did we finish Phase 1?"
→ Check Phase 1 items, report completion percentage

## Special Cases

**No active plan:**
```
ℹ️ No active plan found in ~/.claude/plans/

Available plans:
- {plan1}.md (modified: {date})
- {plan2}.md (modified: {date})

Which plan should I check?
```

**Plan file unreadable:**
```
❌ Cannot read plan file: {path}

Error: {error message}
```

**Ambiguous progress:**
```
⚠️ Cannot automatically determine progress for some items.

Needs manual review:
- [ ] {Item} - Check if this is complete?
```

## Integration

Link with other skills:
- `/row-counts`: Verify data pipeline items
- `/quick-test`: Verify testing items
- `/diary`: Document completed phases

## Post-Status

After showing status:
1. Ask: "Want to continue with next step?"
2. If yes: Proceed directly to implementation
3. If blockers: Help resolve them first
