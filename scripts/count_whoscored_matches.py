"""
Count total WhoScored matches available for scraping (calendar discovery test).
"""

import asyncio
from pathlib import Path
from playwright.async_api import async_playwright
import sys

sys.path.append(str(Path("src").resolve()))
from football_rag.data.whoscored_scraper import collect_all_season_matches

async def main():
    print("🔍 Scanning WhoScored calendar for Eredivisie 2025-2026...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        page = await context.new_page()

        try:
            # No limit = get all matches
            match_urls = await collect_all_season_matches(page, exclude_match_ids=None, limit=None)

            print(f"\n✅ Found {len(match_urls)} finished matches on WhoScored")
            print(f"📅 Season: August 2025 - February 2026")

            # Show sample
            if match_urls:
                print(f"\n📋 Sample matches:")
                for url in match_urls[:3]:
                    print(f"  - {url}")

        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
