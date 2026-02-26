---
name: release
description: Create a versioned release with git tag, GitHub Release, and CHANGELOG update. Use when completing a Phase or significant milestone. Examples: "create release", "tag this version", "release v0.5.0".
version: 1.0.0
metadata:
  author: Ricardo Heredia
  category: devops
  tags: [git, release, versioning, changelog]
---

# Release Manager

Creates a formal versioned release at phase boundaries or significant milestones.

## When to Use

Trigger when user:
- Says "create release", "tag this version", "cut a release"
- Just completed a Phase (4a, 4b, 5...)
- Wants to mark a stable checkpoint in the project history

## Versioning Convention

This project uses **CalVer + Phase** hybrid:

```
v{PHASE}.{MINOR}.{PATCH}
```

Examples:
- `v0.4.0` — Phase 4a complete (pipeline automation)
- `v0.4.1` — hotfix within Phase 4
- `v0.5.0` — Phase 4b complete (Modal inference)

Minor = 0 at phase start, increments for significant features within a phase.

## Process

### Step 1 — Determine version

Ask user or infer from context:
- What phase just completed? → determines major.minor
- Any hotfixes since last release? → patch

Check the latest tag:
```bash
git tag --sort=-version:refname | head -5
```

### Step 2 — Update CHANGELOG.md

Add a dated section under `[Unreleased]` following Keep a Changelog format:

```markdown
## [v0.4.0] — 2026-02-26

### Added
- ...

### Changed
- ...

### Fixed
- ...
```

Read existing CHANGELOG.md first to match style.

### Step 3 — Commit the CHANGELOG

```bash
git add CHANGELOG.md
git commit -m "chore(release): bump CHANGELOG for v0.4.0"
```

### Step 4 — Create annotated tag

```bash
git tag -a v0.4.0 -m "Phase 4a: hybrid pipeline automation complete

- Dagster daemon + launchd auto-start at login
- Sensor chain: scrape → transform → deploy
- workspace.yaml fix for daemon gRPC
- GitHub Actions CI: lint + unit-tests jobs
- 214 matches, 100% mapping, HF Space live"
```

### Step 5 — Push tag

```bash
git push origin v0.4.0
```

### Step 6 — Create GitHub Release

```bash
gh release create v0.4.0 \
  --title "Phase 4a: Pipeline Automation" \
  --notes "$(git log $(git describe --tags --abbrev=0 HEAD^)..HEAD --oneline)" \
  --latest
```

### Step 7 — Report

Show the user:
- Tag created: `v0.4.0`
- GitHub Release URL
- CHANGELOG section added
- Commit SHA

## Rules

- Always use annotated tags (`-a`), never lightweight
- Tag message must reference the Phase and list top 3-5 changes
- Never tag a commit that has failing CI
- Check `gh run list --limit 1` before tagging — CI must be green
- CHANGELOG must be updated before tagging, never after
