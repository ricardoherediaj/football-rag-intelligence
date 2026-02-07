import pytest
import asyncio
from playwright.async_api import async_playwright
from football_rag.data.fotmob_scraper import scrape_fotmob_match_details

@pytest.mark.asyncio
async def test_fotmob_interception():
    """
    Test Fotmob scraping via in-browser fetch.
    Uses a known recent match ID.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        # Fotmob Match URL: https://www.fotmob.com/es/matches/psv-eindhoven-vs-feyenoord/2y2e3u#4815418
        # Match ID: 4815418 (Cruijff Schaal)
        test_id = "4815418" 
        
        print(f"\n🕷️ Fetching Fotmob Match: {test_id}")
        data = await scrape_fotmob_match_details(test_id, page)
        
        if data:
            print("✅ Data intercepted!")
            match_info = data.get('match_info', {})
            print(f"🏠 Home: {match_info.get('home_team')}")
            print(f"🚌 Away: {match_info.get('away_team')}")
            print(f"⚽ Score: {match_info.get('score')}")
            
            shots = data.get('shots', [])
            print(f"📊 Shots found: {len(shots)}")
            
            assert match_info.get('match_id') == test_id
            assert len(shots) > 0
            assert 'home_team' in match_info
        else:
            pytest.fail("Scraper returned None (Capture failed)")
            
        await browser.close()
