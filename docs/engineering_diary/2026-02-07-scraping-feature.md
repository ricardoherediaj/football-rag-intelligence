# Engineering Diary: Scraping Strategies & Infrastructure Cleanup (v1.1 Feature)
**Date:** 2026-02-07
**Tags:** `release:v1.0-mvp`, `feat:scraping`, `infrastructure`, `playwright`, `etl:bronze`

## 1. Release v1.0-mvp & Infrastructure Cleanup 🧹
Prior to starting new feature work, we tagged the repository state as `v1.0-mvp`. This serves as a critical "save point" for our initial working prototype. We then executed a major restructuring to professionalize the codebase:
*   **Moved Legacy Artifacts**: All old notebooks and submission files were moved to `archive/` to declutter the root.
*   **Data Isolation**: Raw `.tar.gz` files were moved to `data/archive/`, adhering to the separation of concerns (code vs. data).
*   **Documentation Home**: Created `docs/architecture/` to house ADRs and architectural overviews.
*   **Git Optimization**: Updated `.gitignore` to strictly exclude data and temporary files.

**Relevance**: This ensures that `main` remains clean and deployable, while preserving the history of our early experimentation. It aligns with the principle of "leaving the campground cleaner than you found it."

## 2. Configurable Scraping Strategies (The "Feed" Mechanism) 🕷️
We implemented a robust, configurable scraping layer using Playwright. This is the **Bronze Layer** ingestion engine of our Medallion Architecture.

### Strategies Implemented:
1.  **Most Recent Match**: Fetches only the latest available match (Limit=1). Ideal for daily incremental updates.
2.  **Last N Matches**: Fetches a configurable number of recent matches. Useful for catching up after a short downtime.
3.  **Full Season**: Fetches everything. Useful for initial backfilling or disaster recovery.

### Why Playwright?
Our data sources (WhoScored, FotMob) rely heavily on Client-Side Rendering (CSR) via JavaScript. Traditional requests (like `requests` or `httpx`) fail because the HTML is empty until JS executes. Playwright allows us to:
*   **Execute JS**: Wait for `matchCentreData` or API calls to populate.
*   **Intercept Network Traffic**: In FotMob's case, we intercept the internal API response directly from the browser context, bypassing complex signature headers.
*   **Mimic User Behavior**: Reduces bot detection likelihood compared to headless curl requests.

## 3. Verification Protocol ✅
We adopted a strict "Test First" verification protocol before merging to `main`.

### Test Results
| Test Type | Test Case | Status | Notes |
| :--- | :--- | :--- | :--- |
| **Unit Test** | `whoscored` limit logic | ✅ PASS | Verified slicing logic without network calls. |
| **Smoke Test** | `whoscored --mode recent` | ✅ PASS | **1492 events** scraped live. |
| **Smoke Test** | `whoscored --mode n_matches` | ✅ PASS | **2935 events** scraped (2 matches). |
| **Smoke Test** | `fotmob --mode recent` | ✅ PASS | **1 match** scraped live. |

## 4. Full-Season Scraping & Data Parity

### WhoScored Calendar Navigation Fix
The WhoScored fixtures page uses `#dayChangeBtn-prev`/`#dayChangeBtn-next` buttons to navigate weeks. Two critical issues were resolved:

1. **Ad Overlay Blocking Clicks**: A `<div class="a__sc-np32r2-0">` overlay intercepted pointer events on navigation buttons. `force=True` on Playwright clicks didn't work (the page content never changed). Fixed by using JS execution: `page.evaluate('document.querySelector("#dayChangeBtn-prev").click()')`.

2. **Incomplete Season Coverage**: Navigating backwards from the current week only found ~127/189 matches. Fixed by implementing a two-phase strategy for full scrapes: rewind to season start (35 weeks back), then traverse forward through the entire season. This correctly finds all 189 played matches.

### Scraper Refactoring
Extracted reusable helpers in `collect_all_season_matches`:
- `_js_click(selector)`: Clicks via JS to bypass ad overlays.
- `_collect_direction(btn_selector, max_weeks)`: Traverses calendar in one direction, collecting matches with stale-detection (stops after 3 weeks with no new matches).
- Strategy split: `limit` mode goes backward from current week; `full` mode rewinds to season start then goes forward.

### Final Data Parity
| Source | Files | Coverage |
| :--- | :--- | :--- |
| WhoScored | 189 | 100% of calendar |
| FotMob | 190 | 100% of API |
| **Matched (team pairs)** | **188** | **98.9%** |

Gap analysis:
- 2 FotMob-only matches: FC Groningen (H) vs NAC Breda, FC Twente (H) vs Excelsior — return-leg fixtures not yet on WhoScored calendar (future matches).
- 1 WhoScored-only match: FC Twente (H) vs SC Heerenveen — not yet in FotMob API.
- These 3 gaps are inherent source-availability differences, not scraping failures.

## 5. DuckDB Medallion Pipeline

### Bronze Layer (`raw_matches_bronze`)
- Loads all WhoScored and FotMob JSON files into `bronze_matches` table.
- Handles FotMob dual JSON format: 108 files use flat format (`data.home_team`), 82 use nested format (`data.match_info.home_team`).
- NaN sanitization: `_sanitize_json()` replaces `NaN` with `null` for DuckDB compatibility.

### Silver Layer
- `events_silver`: Flattens WhoScored events using `unnest(from_json())`. Extracts event type, coordinates, player/team IDs, minute/second, shot/goal/touch flags.
- `silver_fotmob`: Flattens FotMob shots with `COALESCE` for dual-format support. Extracts xG, shot type, situation, on-target flag.

### Gold Layer
- `gold_match_summary`: Joins WhoScored event aggregates (passes, shots, goals, tackles) with FotMob xG metrics per match/team.
- `gold_player_stats`: Aggregates player-level stats across all matches.

### Docker Integration
- Added `./data:/opt/dagster/app/data` volume mount to Dagster webserver and daemon containers.
- Local materialization preferred over Docker due to memory constraints (OOM at exit code 137).

## 6. Data Quality Tests (27 tests)

| Layer | Tests | Validates |
| :--- | :--- | :--- |
| Bronze | 5 | Data exists, both sources present, file counts match, no unknown IDs |
| Silver Events | 6 | Non-empty, required columns, coordinates (0-100), minutes (0-130), goals <= shots, events per match (500-2500) |
| Silver FotMob | 4 | Non-empty, xG range (0-1), team info present, goal consistency |
| Gold Match Summary | 3 | Non-empty, 2 teams per match, non-negative goals |
| Gold Player Stats | 3 | Non-empty, goals <= shots, positive match counts |
| Sanitize JSON | 3 | NaN handling |

All 27 tests pass. Ruff lint clean on all modified files.

## 7. Next Steps
- Multi-league expansion: The scraper strategy (rewind-to-start + forward) should generalize to other leagues by parameterizing the fixtures URL.
- Incremental pipeline: Bronze currently does full reload; add upsert logic for daily incremental runs.
- dbt migration: Move Silver/Gold SQL transformations from Python-embedded SQL to dbt models.
