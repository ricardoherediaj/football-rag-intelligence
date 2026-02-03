import pytest
import asyncio
from pathlib import Path
from football_rag.data.whoscored_scraper import extract_match_id, scrape_single_match, MatchEvent
from playwright.async_api import async_playwright

def test_extract_match_id():
    """Test extracting match ID from various WhoScored link formats"""
    url = "https://www.whoscored.com/matches/1903856/live/netherlands-eredivisie-2025-2026-nac-breda-twente"
    assert extract_match_id(url) == "1903856"
    
    url2 = "https://www.whoscored.com/matches/123456/show"
    assert extract_match_id(url2) == "123456"
    
    with pytest.raises(ValueError):
        extract_match_id("https://google.com")

@pytest.mark.asyncio
async def test_scrape_single_match_structure():
    """
    Test that the scraper returns a DataFrame with the correct columns.
    Note: This test requires a live network connection or local mock.
    We'll test against a known match that is likely to remain stable.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        # Using a fresh 2025-2026 match: NAC Breda vs Twente
        test_url = "https://www.whoscored.com/matches/1903856/live/netherlands-eredivisie-2025-2026-nac-breda-twente"
        
        try:
            print(f"\n🕷️ Connecting to: {test_url}")
            df = await scrape_single_match(test_url, page)
            
            if df is not None:
                print(f"\n✅ Data fetched successfully!")
                print(f"📊 Total Events: {len(df)}")
                print(f"🔢 Columns found: {df.columns.tolist()}")
                print(f"👀 First 3 events:\n{df[['minute', 'type_display_name', 'player_id']].head(3)}")
                
                assert not df.empty
                # Check mandatory columns
                expected_cols = ['id', 'event_id', 'minute', 'team_id', 'player_id', 'match_url']
                for col in expected_cols:
                    assert col in df.columns
                
                # Check data types
                assert df['id'].dtype == 'int64'
                assert df['match_url'].iloc[0] == test_url
            else:
                pytest.skip("Scraper returned None - possibly due to bot detection or network issues")
                
        finally:
            await browser.close()

def test_match_event_pydantic():
    """Test the Pydantic model for match events"""
    sample_data = {
        "id": 1,
        "event_id": 101,
        "minute": 45,
        "second": 30.5,
        "team_id": 50,
        "player_id": 123,
        "x": 50.0,
        "y": 50.0,
        "qualifiers": [],
        "is_touch": True,
        "is_shot": False,
        "card_type": False,
        "is_goal": False,
        "type_display_name": "Pass",
        "outcome_type_display_name": "Successful",
        "period_display_name": "FirstHalf",
        "match_url": "http://test.com"
    }
    event = MatchEvent(**sample_data)
    assert event.id == 1
    assert event.type_display_name == "Pass"
