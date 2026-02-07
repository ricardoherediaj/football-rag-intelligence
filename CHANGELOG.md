# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Added
- **Infrastructure V2 (The Data Foundation)**
    - Added `docker-compose.yml` orchestrating MinIO, Dagster, and Postgres.
    - Added `ops/Dockerfile` for custom Dagster Webserver and Daemon images.
    - Added `orchestration/` directory for Dagster code locations.
    - Added `ops/dagster_home/` for Dagster instance configuration.
    - Added `data_lake/` volume mapping for local MinIO storage.

### Added
- **Scrapers V2 (Playwright)**
    - Replaced Selenium with **Playwright** for async scraping.
    - Implemented **In-Browser Fetch** strategy for Fotmob to bypass complex token generation.
    - Added automated tests for both scrapers (`tests/test_fotmob_scraper.py`, `tests/test_whoscored_scraper.py`).
- **Data Pipeline (Dagster & DuckDB)**
    - Implemented **Medallion Architecture** (Bronze -> Silver -> Gold).
    - Added `silver_fotmob` transformation layer for specialized shot map data.
    - Integrated **DuckDB VSS** (Vector Similarity Search) for creating HNSW indices on player stats.
- **Infrastructure V2**
    - Transitioned Docker build to use `uv sync` for strictly reproducible builds.
    - Added `libxrandr2` and other system deps for Headless Chrome in Docker.

### Changed
- Refactored `docker-compose.yml` to use root build context for `uv.lock` access.
- Updated `workspace.yaml` to point to `orchestration/defs.py`.

### Fixed
- **Dagster UI Connectivity**: Resolved issue where Web Server UI was unreachable. Verified Docker container port mapping and `workspace.yaml` paths. UI is now fully accessible at `localhost:3000`.

- **Full-Season Scraping (Configurable Modes)**
    - Implemented configurable scraping strategies: `recent`, `n_matches`, `full`.
    - WhoScored: JS-click calendar navigation bypassing ad overlays, two-phase strategy for full-season coverage.
    - FotMob: In-browser fetch with league fixture crawling.
    - Achieved 188/190 match parity (98.9%) between WhoScored and FotMob for Eredivisie 2025-2026.
- **DuckDB Medallion Pipeline (`duckdb_assets.py`)**
    - Bronze: Loads WhoScored + FotMob JSON with dual-format handling and NaN sanitization.
    - Silver: `events_silver` (WhoScored events), `silver_fotmob_shots` (FotMob xG/shot data).
    - Gold: `gold_match_summary` (match-level join of both sources), `gold_player_stats`.
- **Data Quality Tests (27 tests)**
    - `tests/test_duckdb_pipeline.py`: Bronze/Silver/Gold layer validation.
    - `tests/test_scraping_logic.py`: Unit tests for scraper logic with mocked Playwright.

### Changed
- Added `./data:/opt/dagster/app/data` volume mount to Dagster containers.
- Refactored `whoscored_scraper.py` with `_js_click` and `_collect_direction` helpers.

### Fixed
- **WhoScored Calendar Navigation**: Ad overlay blocking clicks; fixed with JS `document.querySelector().click()`.
- **FotMob Dual JSON Format**: 82 files used nested `match_info` format; fixed with fallback parsing and COALESCE SQL.

### Known Issues / Next Steps
- 3 unmatched fixtures due to source-availability differences (not scraping failures).
- Dagster Docker containers OOM on full pipeline materialization; local execution works.
- Multi-league expansion: Parameterize fixtures URL for other leagues.
