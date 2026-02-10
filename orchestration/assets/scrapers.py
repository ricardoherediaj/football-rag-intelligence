import json
from pathlib import Path
from typing import Optional

from dagster import asset, AssetExecutionContext, Config

from football_rag.data.whoscored_scraper import scrape_complete_season_async, save_matches_locally
from football_rag.data.fotmob_scraper import scrape_fotmob_season, save_fotmob_matches_locally
from football_rag.storage.minio_client import MinIOClient, DEFAULT_BUCKET


class ScraperConfig(Config):
    mode: str = "incremental"
    limit: Optional[int] = None


def _sync_to_minio(local_dir: Path, prefix: str, context: AssetExecutionContext) -> int:
    """Upload all JSON files from a local directory to MinIO."""
    client = MinIOClient()
    client.ensure_bucket(DEFAULT_BUCKET)
    count = 0
    for json_file in sorted(local_dir.glob("*.json")):
        key = f"{prefix}/{json_file.name}"
        with open(json_file) as f:
            data = json.load(f)
        client.upload_json(DEFAULT_BUCKET, key, data)
        count += 1
    context.log.info(f"Synced {count} files to MinIO: {prefix}/")
    return count


@asset(compute_kind="playwright")
async def whoscored_match_data(context: AssetExecutionContext, config: ScraperConfig):
    """
    Scrape Eredivisie matches using Playwright.
    Config:
      - mode: 'incremental', 'full', 'recent', 'n_matches'
      - limit: Number of matches (for 'n_matches')
    """
    context.log.info(f"Starting WhoScored scrape (Mode: {config.mode}, Limit: {config.limit})...")

    df = await scrape_complete_season_async(mode=config.mode, limit=config.limit)

    if df is not None and not df.empty:
        count = save_matches_locally(df)
        context.log.info(f"Successfully scraped and saved {count} matches")

        local_dir = Path("data/raw/whoscored_matches/eredivisie/2025-2026")
        _sync_to_minio(local_dir, "whoscored/eredivisie/2025-2026", context)
        return count
    else:
        context.log.info("No matches found to scrape")
        return 0


@asset(compute_kind="playwright")
async def fotmob_match_data(context: AssetExecutionContext, config: ScraperConfig):
    """
    Scrape Eredivisie matches from Fotmob using Playwright.
    Config:
      - mode: 'incremental', 'full', 'recent', 'n_matches'
      - limit: Number of matches (for 'n_matches')
    """
    context.log.info(f"Starting Fotmob scrape (Mode: {config.mode}, Limit: {config.limit})...")

    matches = await scrape_fotmob_season(mode=config.mode, limit=config.limit)

    if matches:
        count = save_fotmob_matches_locally(matches)
        context.log.info(f"Successfully scraped and saved {count} Fotmob matches")

        local_dir = Path("data/raw/fotmob_matches/eredivisie/2025-2026")
        _sync_to_minio(local_dir, "fotmob/eredivisie/2025-2026", context)
        return count
    else:
        context.log.info("No matches found")
        return 0
