
import asyncio
import sys
from pathlib import Path
from playwright.async_api import async_playwright

# Add src to path
sys.path.append(str(Path("src").resolve()))

from football_rag.data.fotmob_scraper import collect_fixture_ids

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        # Navigate to FotMob first to establish browser session
        await page.goto("https://www.fotmob.com", wait_until="domcontentloaded")

        print("🔍 Scanning Eredivisie 2025-2026 (League 57) on FotMob...")
        # League 57 is Eredivisie
        match_ids = await collect_fixture_ids(page, league_id=57)
        
        print(f"\n✅ Found {len(match_ids)} matches available for scraping.")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
