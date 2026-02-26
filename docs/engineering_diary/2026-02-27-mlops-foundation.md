# Engineering Diary: MLOps Foundation — Test Markers, Pre-Commit, CI Split, Skills
**Date:** 2026-02-27
**Tags:** `mlops`, `pytest`, `pre-commit`, `ci-cd`, `github-actions`, `detect-secrets`, `developer-experience`

---

## 1. Problem Statement

After Phase 4a delivered a fully automated end-to-end pipeline (scrape → transform → deploy), the project had a fragile developer experience in three dimensions:

**Testing was binary and opaque.** CI ran all tests with `--ignore` flags to skip known-broken ones. This meant: (a) no contractual distinction between "always safe to run" and "needs local infra", (b) any new test that touched a file or network would silently break CI, and (c) no on-ramp for running heavier test suites locally when you actually want them.

**Nothing stopped bad commits locally.** A developer could commit code with debug prints, private keys, or formatting violations — these would only fail in CI (minutes later, after push). Pre-commit hooks didn't exist.

**There was no standardized release process.** We had tags in `git tag` history but no canonical ceremony: no checklist, no annotated tag convention, no CHANGELOG coupling, no `gh release create`. Similarly, diagnosing system health required remembering 6+ manual commands across daemon, MinIO, CI, HF Space, and MotherDuck.

The user's framing captured it well: *"lo MAS solido debe ser el pipeline ahora mismo y tenerlo bien blindado JUNTO a la observabilidad"* — build the armor now, before technical debt accumulates.

---

## 2. Approach

### 2.1 Pytest Marker System

Introduced four marker tiers in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
markers = [
    "unit: pure logic, no I/O, no browser, no local files — always runs in CI",
    "integration: requires browser (Playwright) or live network — local only",
    "local_data: requires lakehouse.duckdb or MinIO on disk — local only",
    "edd: EDD evaluation suite — requires --run-edd flag and live LLM access",
]
addopts = "-m 'not integration and not local_data and not edd'"
```

The `addopts` line is the key insight: CI runs unit tests **by default**, without any `--ignore` lists or flag-passing ceremony. The inverse opt-in model means new tests are safe by default — they run in CI unless explicitly marked otherwise.

`tests/conftest.py` provides a second layer of protection via `pytest_collection_modifyitems`: even if `addopts` is bypassed (e.g., someone runs `pytest -m ''`), tests marked `integration`/`local_data`/`edd` are skipped unless the corresponding CLI flag is passed (`--run-integration`, `--run-local-data`, `--run-edd`).

**Key Changes:**
- [pyproject.toml](pyproject.toml): added `[tool.pytest.ini_options]` with markers + addopts
- [tests/conftest.py](tests/conftest.py): full rewrite with `pytest_addoption` + `pytest_collection_modifyitems`
- [tests/test_whoscored_scraper.py](tests/test_whoscored_scraper.py): `@pytest.mark.integration` on browser test, unit tests (`test_extract_match_id`, `test_match_event_pydantic`) unmarked → still run in CI
- [tests/test_fotmob_scraper.py](tests/test_fotmob_scraper.py): replaced `@pytest.mark.skip` with `@pytest.mark.integration`
- [tests/test_phase1_pipeline.py](tests/test_phase1_pipeline.py): `pytestmark = pytest.mark.local_data` (whole file)
- [tests/test_duckdb_pipeline.py](tests/test_duckdb_pipeline.py): `pytestmark = pytest.mark.local_data` (whole file)

### 2.2 CI Job Separation

Rewrote [.github/workflows/matchday_pipeline.yml](.github/workflows/matchday_pipeline.yml) from a single `test` job into two gated jobs:

```
lint ──► unit-tests
```

`lint` runs `ruff check .` + `ruff format --check .`. `unit-tests` has `needs: lint`, so format violations block tests from running. This surfaces the cheapest check first and gives developers a faster feedback loop (lint failure in ~30s vs waiting for test setup).

Both jobs use `uv sync` for deterministic dependency resolution from `uv.lock`.

### 2.3 Pre-Commit Hooks

Created [.pre-commit-config.yaml](.pre-commit-config.yaml) with two hook repositories:

**astral-sh/ruff-pre-commit** (v0.9.0):
- `ruff --fix`: auto-fixes lint violations on commit
- `ruff-format`: auto-formats code on commit

**pre-commit/pre-commit-hooks** (v5.0.0):
- `check-merge-conflict`: catches accidental `<<<<<<` markers
- `debug-statements`: blocks `breakpoint()`, `pdb`, `ipdb` in committed code
- `detect-private-key`: regex-scans for RSA/SSH private key headers
- `check-added-large-files` (500KB limit): prevents accidental binary commits
- `trailing-whitespace` (excluding `docs/`): keeps diffs clean

**detect-secrets** (v1.5.0):
- Baseline generated from full repo scan: 489 lines, 11 files with false positives (all in `archive/` notebooks and config files — none in `src/` or `tests/`)
- `.secrets.baseline` committed → hook passes on every subsequent commit

All hooks installed into `.git/hooks/pre-commit` via `pre-commit install`.

### 2.4 Skills: `/release` and `/health-check`

Two reusable Claude skills codify processes that would otherwise require remembering commands:

**[.claude/skills/release/SKILL.md](.claude/skills/release/SKILL.md)** — CalVer + Phase versioning:
- Convention: `v{PHASE}.{MINOR}.{PATCH}` (e.g., `v0.4.0` = Phase 4a complete)
- 7-step process: determine version → update CHANGELOG → commit → annotated tag → push tag → `gh release create` → report
- Hard rules: never tag failing CI, always annotated tags, CHANGELOG before tag

**[.claude/skills/health-check/SKILL.md](.claude/skills/health-check/SKILL.md)** — 6-layer system verification:
1. Dagster daemon PID via `launchctl` + `ps aux`
2. MinIO via Docker + `curl` health endpoint
3. GitHub Actions latest run status via `gh run list`
4. HF Space runtime via `huggingface_hub.HfApi`
5. MotherDuck row counts (bronze ≥420, silver ≥270k, gold ≥210)
6. `lakehouse.duckdb` embeddings (≥210)
- Outputs as a table with ✅/❌ per layer

### 2.5 detect-secrets Baseline (Today — Feb 27)

The baseline file was generated as a background task during the previous session boundary. Today:
- Verified 11 false-positive files, all in `archive/` or config — zero hits in production code
- Re-enabled the `detect-secrets` hook in `.pre-commit-config.yaml`
- Verified `pre-commit run detect-secrets --all-files` → **Passed**
- Committed `1f438ac`

---

## 3. Verification

**Tests (local):**
```
$ uv run pytest -v
17 passed, 62 deselected (by markers) in 3.2s
```
62 tests deselected = integration + local_data tests correctly filtered by `addopts`. Zero failures.

**Pre-commit (all hooks):**
```
ruff.............................................................Passed
ruff-format......................................................Passed
check for merge conflicts........................................Passed
debug statements.................................................Passed
detect private key...............................................Passed
check for added large files......................................Passed
trim trailing whitespace.........................................Passed
Detect secrets...................................................Passed
```

**CI (GitHub Actions):**
- `lint` job: ✅ ruff check + format clean
- `unit-tests` job: ✅ 17 passed, 62 deselected

**Commits shipped:**
| SHA | Description |
|---|---|
| `b8e358c` | fix(scraper): stale-counter bug |
| `ed421a6` | fix(ci): skip test_duckdb_pipeline |
| `24fe72f` | fix(ci): skip test_phase1_pipeline |
| `ccadf14` | fix(ci): skip playwright scraper tests |
| `a93b8cc` | fix(dagster): workspace.yaml for daemon gRPC |
| `a8e8ef5` | chore(dx): markers + pre-commit + CI jobs + skills |
| `1f438ac` | chore(security): detect-secrets baseline committed |

---

## 4. Lessons Learned

**The `addopts` pattern is the right default for data projects.** Using `addopts = "-m 'not integration and not local_data'"` is safer than `--ignore` lists because: (1) it's self-documenting in pyproject.toml, (2) new tests default to running unless marked, (3) you can override with `-m ''` if needed. `--ignore` lists grow quietly and obscure what's actually skipped.

**Double-layer skip protection is worth it.** Having both `addopts` (marker filter) and `conftest.py` `pytest_collection_modifyitems` (skip with reason + flag gate) seems redundant but serves different use cases: `addopts` for CI automation, conftest for explicit local developer choices.

**Skills as structured context, not code.** The `/release` and `/health-check` skills are Markdown files that Claude reads as context — they encode knowledge that would otherwise require remembering multi-step processes. They're most valuable for infrequent but high-stakes operations (releasing a version, diagnosing a production issue) where a consistent checklist prevents mistakes.

**detect-secrets baseline is a one-time cost with ongoing value.** The baseline scan took ~3 minutes on first run against a codebase with notebooks in `archive/`. Every subsequent commit check is ~1 second. Worth the setup friction.

**The `execute` vs `launch` distinction is the most dangerous Dagster footgun.** `dagster job execute` feels correct but runs in-process and is invisible to the daemon — sensors never fire. Always use `dagster job launch` for sensor-coupled pipeline runs. This belongs in any Dagster onboarding checklist.

---

## 5. Next Steps

1. **Prompt v4.0_tactical** — Edit [prompts/prompt_versions.yaml](prompts/prompt_versions.yaml): rewrite system prompt to emphasize tactical "why" over metric recitation. Re-run EDD to measure improvement on `tactical_insight` (currently 0.91 → target ≥0.95).

2. **EDD in CI** — Add `workflow_dispatch`-gated job to [.github/workflows/matchday_pipeline.yml](.github/workflows/matchday_pipeline.yml):
   ```yaml
   edd:
     if: github.event_name == 'workflow_dispatch'
     needs: unit-tests
     run: uv run pytest tests/test_edd.py --run-edd -v
   ```
   Requires `ANTHROPIC_API_KEY` + `MOTHERDUCK_TOKEN` + `OPIK_API_KEY` as GitHub secrets.

3. **First formal release** — Use `/release` skill to tag `v0.4.0` for Phase 4a. CHANGELOG is already updated. Only missing: annotated tag + `gh release create`.

4. **Dagster Asset Checks** — Migrate `test_phase1_pipeline.py` row-count assertions into `@asset_check` decorators so they run inside the pipeline, not outside it. Reference: [tests/test_phase1_pipeline.py](tests/test_phase1_pipeline.py).

5. **HF_TOKEN in GitHub Secrets** — `deploy_job` uses `HF_TOKEN` from local `.env`. Add to repo secrets so CI can also trigger deploys (needed for EDD-in-CI or future CD workflow).
