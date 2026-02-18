# Engineering Diary: Playwright Migration & Docker Modernization
**Date:** 2026-02-01  
**Topic:** Scraper Scaling, Anti-Bot Evasion, and Infrastructure Reliability

## 1. The Scraper Reliability Problem
Our previous Selenium-based scrapers were flaky.
- **WhoScored**: The site is heavy with ads and trackers. Selenium's default page load strategy waits for *everything* (including ad pixels) to finish, causing timeouts.
- **Fotmob**: We were relying on a reverse-engineered token generator (python implementation of their "Three Lions" signing key). This is fragile; any change to their JS minification breaks our scraper.

## 2. Solution: Migration to Playwright (Async)
We moved both scrapers to **Playwright** for better control over the browser CDP (Chrome DevTools Protocol).

### WhoScored Optimization
Instead of waiting for `networkidle`, we now use a smarter predicate:
```python
await page.goto(url, wait_until="domcontentloaded")
await page.wait_for_selector(selector_for_match_data)
```
This ignores the subsequent loading of heavy ad scripts, reducing scrape time from ~20s to ~5s per match.

### Fotmob Strategy Pivot: "In-Browser Fetch"
We initially tried "Network Interception" (waiting for `api/matchDetails` in the network tab). However, Fotmob uses Next.js with Server-Side Rendering (SSR) for the initial load, so the JSON data wasn't always appearing as a separate XHR request.

**The Fix:**
We completely bypassed the need to generate signed tokens by piggybacking on the browser's valid session.
1. Navigate to the match page (establishing valid cookies/headers).
2. Execute a native JavaScript `fetch` *inside* the page context:
   ```javascript
   const response = await fetch('/api/matchDetails?matchId=123...');
   return await response.json();
   ```
This forces the browser to handle all the complex signing and header generation for us.

## 3. Infrastructure: Docker V2 with `uv`
We encountered a "works on my machine" issue where the Docker container lacked system dependencies.

**Improvements:**
- **Dependency Management**: We switched the Dockerfile to use `uv sync`. This ensures the container uses the exact same `uv.lock` as local dev.
- **Headless Support**: Added `libxrandr2`, `libgbm1`, and other low-level rendering libraries required for Chrome in a `python:3.12-slim` image.
- **Build Context**: Fixed `docker-compose.yml` to build from the root (`.`) context, allowing access to `uv.lock` and `src/` during the build phase.

## 4. Pipeline Integration (Dagster)
We now have two distinct assets feeding the Bronze layer:
- `whoscored_match_scrape`: Scrapes match stats.
- `fotmob_match_scrape`: Scrapes shot locations ("shotmaps").

These are ingested into DuckDB via a unified `raw_to_duckdb` loader that handles schema differences in the Silver layer (`silver_events` vs `silver_fotmob`).
