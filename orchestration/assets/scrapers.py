from dagster import asset, AssetExecutionContext
import asyncio
from football_rag.data.whoscored_scraper import scrape_complete_season_async, save_matches_locally
from football_rag.data.fotmob_scraper import scrape_fotmob_season, save_fotmob_matches_locally

@asset(compute_kind="playwright")
async def whoscored_match_data(context: AssetExecutionContext):
    """Scrape Eredivisie matches using Playwright and save locally."""
    context.log.info("Starting WhoScored incremental scrape...")
    
    # We use incremental mode by default
    df = await scrape_complete_season_async(mode="incremental")
    
    if df is not None and not df.empty:
        count = save_matches_locally(df)
        context.log.info(f"Successfully scraped and saved {count} new matches")
        return count
    else:
        context.log.info("No new matches found to scrape")
        return 0

@asset(compute_kind="playwright")
async def fotmob_match_data(context: AssetExecutionContext):
    """Scrape Eredivisie matches from Fotmob using Playwright."""
    context.log.info("Starting Fotmob scrape...")
    
    # Scrape matches (limit to 5 for now to avoid massive initial load)
    matches = await scrape_fotmob_season(limit=5)
    
    if matches:
        count = save_fotmob_matches_locally(matches)
        context.log.info(f"Successfully scraped and saved {count} Fotmob matches")
        return count
    else:
        context.log.info("No matches found")
        return 0
