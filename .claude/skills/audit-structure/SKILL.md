---
name: audit-structure
description: Review project directory structure for minimalism and optimization. Use when user asks "audit structure", "check files", "clean up project", "too many files", or wants to ensure essentialist organization.
version: 1.0.0
metadata:
  author: Ricardo Heredia
  category: project-management
  tags: [organization, minimalism, cleanup, structure]
---

# Project Structure Audit

Reviews project for file bloat, unnecessary artifacts, and optimization opportunities following essentialist principles.

## When to Use

Trigger when user:
- Says "audit structure", "review files", "clean up"
- Mentions "too many files" or "project bloat"
- Asks about project organization
- Wants to ensure minimalism before PR/commit

## Instructions

### Step 1: Scan Project Structure

Run comprehensive scan:
```bash
tree -L 3 -I '__pycache__|*.pyc|.git|node_modules' .
```

Capture key metrics:
- Total directories
- Total files
- Size of data/ directory
- Number of notebooks
- Number of scripts

### Step 2: Analyze Against Essentialist Criteria

Check for violations:

**❌ Red Flags (Must Fix):**
- Duplicate files (same content, different names)
- Abandoned notebooks in project root
- Multiple README files
- Orphaned scripts (no imports/usage)
- Test files in non-test directories
- Data files committed to git (should be in .gitignore)
- Temporary/debug files (test.py, debug.py, scratch.ipynb)

**⚠️ Yellow Flags (Review):**
- More than 5 files in project root
- Scripts and notebooks mixed in same directory
- Multiple configuration files for same tool
- Archive directories that should be deleted
- Documentation scattered across multiple locations

**✅ Green Patterns (Good):**
- Clear separation: src/, tests/, docs/, scripts/
- Single source of truth for configs
- Data isolated in gitignored directory
- Notebooks organized by purpose
- No duplicate functionality

### Step 3: Generate Recommendations

Format as actionable checklist:

```markdown
## 🔍 Structure Audit Results

### Critical Issues (Fix Now)
- [ ] **Delete**: `test.py` in root (orphaned debug file)
- [ ] **Move**: notebooks/*.ipynb → archive/notebooks/
- [ ] **Consolidate**: 3 separate README files → single README.md

### Optimization Opportunities
- [ ] **Consider**: Merge scripts/ and src/ (both have similar utilities)
- [ ] **Review**: docs/archive/ - can this be deleted?
- [ ] **Simplify**: Remove data/ from tracking (.gitignore already excludes)

### Structure Score: 7/10
✅ Clear test separation
✅ Good docs organization
⚠️ Root directory cluttered (8 files, should be ≤5)
❌ Orphaned files detected
```

### Step 4: Priority Ranking

Rank fixes by impact:

**High Priority** (Do First):
1. Delete abandoned/orphaned files
2. Move data files to proper locations
3. Consolidate duplicate configs

**Medium Priority** (Do Soon):
1. Reorganize scattered documentation
2. Archive old notebooks
3. Simplify directory structure

**Low Priority** (Nice to Have):
1. Rename for consistency
2. Further consolidation opportunities

## Evaluation Rubric

Score project 1-10:

| Score | Criteria |
|-------|----------|
| 10 | Perfect essentialist structure, zero bloat |
| 8-9 | Minor issues, mostly clean |
| 6-7 | Some bloat, needs cleanup |
| 4-5 | Significant issues, must address |
| 1-3 | Major bloat, hard to navigate |

## Common Patterns to Flag

**Pattern 1: Test Pollution**
```
❌ Bad:
/
├── test_foo.py
├── src/
│   └── test_bar.py

✅ Good:
tests/
├── test_foo.py
└── test_bar.py
```

**Pattern 2: Notebook Sprawl**
```
❌ Bad:
/
├── experiment1.ipynb
├── debug.ipynb
├── scratch.ipynb

✅ Good:
archive/notebooks/  # Or delete if not needed
```

**Pattern 3: Config Clutter**
```
❌ Bad:
/
├── .env
├── .env.local
├── .env.example
├── config.py
├── settings.py

✅ Good:
/
├── .env.example  # Committed template
.env (gitignored)  # Local only
```

## Action Items Format

Always provide:
1. **Immediate deletions**: Files/dirs to remove now
2. **Consolidations**: What to merge
3. **Moves**: What goes where
4. **Preventions**: How to avoid future bloat

## Post-Audit

After user applies fixes:
- Re-run scan
- Confirm improvements
- Update score
- Suggest .gitignore additions to prevent recurrence
