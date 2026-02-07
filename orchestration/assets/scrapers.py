from dagster import asset, AssetExecutionContext, Config
from typing import Optional
from football_rag.data.whoscored_scraper import scrape_complete_season_async, save_matches_locally
from football_rag.data.fotmob_scraper import scrape_fotmob_season, save_fotmob_matches_locally

class ScraperConfig(Config):
    mode: str = "incremental"
    limit: Optional[int] = None

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
        return count
    else:
        context.log.info("No matches found")
        return 0
