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
