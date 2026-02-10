---
name: quick-test
description: Fast pytest execution with minimal output for rapid TDD cycles. Use when user says "run tests", "quick test", "test this", or during development iteration. Optimized for speed over completeness.
version: 1.0.0
metadata:
  author: Ricardo Heredia
  category: testing
  tags: [testing, tdd, pytest, productivity]
---

# Quick Test

Fast pytest runner optimized for TDD cycles and rapid feedback.

## When to Use

Trigger this skill when the user:
- Says "run tests", "test this", "quick test"
- Is iterating on code changes
- Wants fast feedback on test status
- Mentions pytest or testing

## Instructions

Execute pytest with these flags for optimal speed:

```bash
uv run pytest -x --tb=short -v --no-header {args}
```

**Flags explained:**
- `-x`: Stop at first failure (fast feedback)
- `--tb=short`: Concise traceback
- `-v`: Verbose test names
- `--no-header`: Skip pytest header
- `{args}`: User-provided (file path, -k pattern, etc.)

## Execution Rules

1. **If user provides specific args**: Pass them through
   - Example: `uv run pytest -x --tb=short -v --no-header tests/test_foo.py`

2. **If no args**: Run all tests
   - Example: `uv run pytest -x --tb=short -v --no-header`

3. **After execution**: Show concise summary
   - If passing: "✅ All tests passed (X tests in Y.YYs)"
   - If failing: Show ONLY the failed test name and short traceback

4. **Post-failure**: If error is obvious (e.g., import error, assertion), suggest fix

## Important

- This is for SPEED, not full coverage
- For pre-commit verification, user should run full `uv run pytest`
- Don't ask "what should I do?" - just run and report results
