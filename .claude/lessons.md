# Lessons Learned: Football RAG Intelligence

This file tracks patterns, mistakes, and rules discovered during development to prevent repetition.

---

## Lesson: Docker Bind Mounts on macOS
**Date:** 2026-02-08
**Context:** MinIO crashed with D state (disk sleep) after uploading ~35 files

**Pattern:** Assumed bind mount `./data_lake:/data` would work like Linux production
**Why:** Didn't account for macOS Docker Desktop VirtioFS latency triggering MinIO's strict disk health monitor
**Rule:** For I/O-heavy workloads (MinIO, Postgres, Redis), ALWAYS use Docker named volumes on macOS
**Project Impact:**
- Applies to any future Docker services requiring high I/O throughput
- Named volumes use Linux VM's native ext4, bypassing macOS filesystem translation
- Use `MINIO_CI_CD=1` for development to relax health checks

**References:**
- Engineering Diary: `docs/engineering_diary/2026-02-08-minio-stability-fix.md`
- Docker Compose: Named volume `minio_data:/data`

---

---

## Lesson: CLAUDE.md Instruction Limit & Context Engineering
**Date:** 2026-02-13
**Context:** CLAUDE.md was 424 lines with ~200+ instructions; expert playbook revealed Claude only follows ~150 instructions max

**Pattern:** Treated CLAUDE.md as comprehensive documentation covering everything (architecture, patterns, git workflow, development commands)
**Why:** Didn't understand Claude's instruction-following limit (~150-200 total, system prompt uses ~50, leaving ~100-150 for CLAUDE.md). More instructions = attention competition = degraded output quality
**Rule:** Keep CLAUDE.md to ~150 instructions. Move stable architectural decisions to ARCHITECTURE.md, coding patterns to PATTERNS.md, session state to SCRATCHPAD.md. Only behavioral guidelines belong in CLAUDE.md
**Project Impact:**
- CLAUDE.md: 424 lines → 396 lines (behavioral focus only)
- Created external memory: ARCHITECTURE.md (stable system design), PATTERNS.md (coding reference), SCRATCHPAD.md (session persistence)
- Enables context degradation management: `/compact` → `/clear` → reload only SCRATCHPAD.md + CLAUDE.md
- Follows expert playbook: "Good CLAUDE.md = amnesia notes to yourself, not new hire documentation"

**References:**
- Expert playbook tweet thread on context management
- GSD methodology (external state files for multi-session work)
- New files: ARCHITECTURE.md, PATTERNS.md, SCRATCHPAD.md

---

## Template for New Lessons

## Lesson: [Brief Description]
**Date:** YYYY-MM-DD
**Context:** [What was happening when the issue occurred]

**Pattern:** [What mistake/assumption was made]
**Why:** [Root cause analysis]
**Rule:** [Specific rule to prevent recurrence]
**Project Impact:** [How this applies to Football RAG specifically]

**References:** [Links to files, commits, or docs]

---
