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

### Known Issues / Next Steps
- **Dagster UI Connectivity**: The Docker containers spin up, but the Web Server UI (`localhost:3000`) is currently unreachable or throwing errors.
    - *Investigation needed*: Verify container port mapping, check logs for `dagster-webserver` startup crashes, and ensure `workspace.yaml` paths are perfectly aligned with volume mounts.
- **Verification**: End-to-end pipeline run from the UI is pending resolution of the connectivity issue.
