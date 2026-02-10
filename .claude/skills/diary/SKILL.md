---
name: diary
description: Auto-generate engineering diary drafts from session work. Use when user finishes major work, says "create diary", "document what we did", after merging PR, or wants to log session accomplishments.
version: 1.0.0
metadata:
  author: Ricardo Heredia
  category: documentation
  tags: [engineering-diary, documentation, productivity]
---

# Engineering Diary Generator

Automatically generates structured engineering diary entries from session work.

## When to Use

Trigger when user:
- Says "create diary", "document this session", "write diary entry"
- Just finished major work (feature, bug fix, infrastructure change)
- Merged a PR and wants to document it
- Mentions "engineering diary" or "session log"

## Instructions

### Step 1: Gather Context

Collect information from:

1. **Recent commits**:
```bash
git log --oneline --since="2 days ago" --no-merges
```

2. **Git status**:
```bash
git status --short
git diff --stat
```

3. **Completed TODOs**:
Review TodoWrite items marked completed in this session

4. **CHANGELOG**:
```bash
grep -A 20 "## \[Unreleased\]" CHANGELOG.md
```

### Step 2: Identify Topic

Determine diary topic from:
- Most frequent words in commit messages
- Primary files changed (e.g., "MinIO", "dbt", "scraping")
- User's description if provided

Format: `YYYY-MM-DD-<topic>-<action>.md`
Example: `2026-02-10-claude-workflow-improvements.md`

### Step 3: Generate Draft

Use this template:

````markdown
# Engineering Diary: {Topic}
**Date:** YYYY-MM-DD
**Tags:** `{comma-separated-tags}`

## 1. Problem Statement
[What needed fixing/building? Why does it matter?]

[Analyze commits and changes to extract the PROBLEM, not just the solution]

## 2. Approach
[How was it solved? What was the strategy?]

[List key decisions made, technologies used, patterns applied]

**Key Changes:**
- {file_path}: {what changed}
- {file_path}: {what changed}

## 3. Verification
[How was it tested? What proves it works?]

**Tests Run:**
- {test command}: {result}
- {verification step}: {outcome}

**Metrics:**
- {quantifiable result}

## 4. Lessons Learned
[What would we do differently? What insights emerged?]

[Check `.claude/lessons.md` for new lessons from this session]

## 5. Next Steps
[Follow-up work identified]

[Reference plan file if applicable: `~/.claude/plans/{plan}.md`]
````

### Step 4: Draft Review

Before finalizing:

1. **Verify accuracy**: All claims backed by commits/diffs
2. **Check completeness**: All major changes covered
3. **Add context**: WHY decisions were made, not just WHAT
4. **Link artifacts**: Reference specific files/commits
5. **Quantify impact**: Row counts, test coverage, performance

### Step 5: Save and Confirm

1. **Save draft**:
```bash
# Preview first
cat > docs/engineering_diary/YYYY-MM-DD-{topic}.md
```

2. **Ask user**: "Review this draft. Should I save it?"

3. **If approved**: Write file

4. **Update lessons.md**: If new patterns discovered

## Quality Checklist

Before presenting draft, verify:

- [ ] Problem statement is clear (not just "we did X")
- [ ] Approach explains WHY, not just WHAT
- [ ] Verification includes concrete evidence (test results, metrics)
- [ ] Lessons learned are actionable (not generic)
- [ ] Next steps are specific (file paths, commands)
- [ ] All file references use correct paths
- [ ] Tags are relevant and specific

## Common Scenarios

**Scenario 1: Bug Fix**
```markdown
## 1. Problem Statement
MinIO crashed with D state after 35 files due to VirtioFS latency

[Not: "Fixed MinIO"]
```

**Scenario 2: Feature Addition**
```markdown
## 1. Problem Statement
Pipeline lacked configurable scraping modes. Users couldn't choose between
recent, n_matches, or full-season scraping based on use case.

[Not: "Added scraping modes"]
```

**Scenario 3: Refactoring**
```markdown
## 1. Problem Statement
SQL transformations lived in Python strings, making version control and
testing difficult. Needed to migrate to dbt for better DX.

[Not: "Migrated to dbt"]
```

## Error Handling

If insufficient context:
```
⚠️ Insufficient information to generate complete diary.

Missing:
- Recent commits (run: git log)
- File changes (run: git diff --stat)

Please provide more context or run commands above.
```

If no major work detected:
```
ℹ️ No significant changes detected in last 2 days.

Consider:
- Expanding time window (--since="7 days ago")
- Manually specifying topic and changes
- Skipping diary entry (trivial changes don't need documentation)
```

## Post-Generation

After creating diary:
1. Suggest updating CHANGELOG if not already done
2. Check if `.claude/lessons.md` needs updating
3. Confirm file was saved: `ls -lh docs/engineering_diary/`
