"""
Fotmob scraper using Playwright to execute in-browser fetches.
This leverages the browser's context to handle session/auth automatically
while targeting the known internal API endpoints.
"""

import json
import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any
from playwright.async_api import Page, async_playwright

import sys
sys.path.append(str(Path(__file__).parent.parent.parent))


async def scrape_fotmob_match_details(match_id: str, page: Page) -> Optional[Dict[str, Any]]:
    """
    Scrape match data by executing a fetch inside the browser context.
    This bypasses the need to manually generate signatures (x-mas header) 
    as we piggyback on the browser's active session.
    """
    # 1. Go to the match page to ensure we have the right context/cookies
    # We don't need to wait for everything to load, just the document
    url = f"https://www.fotmob.com/matches/match/{match_id}"
    print(f"�️ Navigating to context: {url}")
    
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
    except Exception as e:
        print(f"Warning: Navigation timeout, trying to proceed with fetch anyway: {e}")

    # 2. Execute fetch within the page
    # We use the same endpoint as the original script: /api/matchDetails
    print(f"🔄 Executing in-browser fetch for match {match_id}...")
    
    try:
        data = await page.evaluate(f"""async () => {{
            const response = await fetch('/api/matchDetails?matchId={match_id}&showNewUefaBracket=true');
            if (!response.ok) {{
                throw new Error('Fetch failed with status ' + response.status);
            }}
            return await response.json();
        }}""")
        
        captured_data = {}
        
        # Extract shots
        try:
            content = data.get('content', {})
            shotmap = content.get('shotmap', {}).get('shots', [])
            captured_data['shots'] = shotmap
            
            # Extract basic info
            general = data.get('general', {})
            if not general:
                 general = content.get('general', {})
                 
            captured_data['match_info'] = {
                'match_id': match_id,
                'home_team': general.get('homeTeam', {}).get('name'),
                'away_team': general.get('awayTeam', {}).get('name'),
                'home_team_id': general.get('homeTeam', {}).get('id'),
                'away_team_id': general.get('awayTeam', {}).get('id'),
                'score': general.get('matchTime', {}).get('scoreString'),
                'utc_time': general.get('matchTime', {}).get('utcTime')
            }
            print(f"✅ Successfully fetched data via browser API for {match_id}")
            return captured_data

        except Exception as e:
            print(f"⚠️ Error parsing fetched data: {e}")
            # print(f"DEBUG: Data keys: {list(data.keys())}")
            return None

    except Exception as e:
        print(f"❌ In-browser fetch failed: {e}")
        return None

async def collect_fixture_ids(page: Page, league_id: int = 57) -> List[str]:
    """
    Fetch all match IDs for a league from the fixtures endpoint.
    League 57 = Eredivisie.
    """
    print(f"📅 Fetching fixtures for league {league_id}...")
    try:
        data = await page.evaluate(f"""async () => {{
            const response = await fetch('/api/leagues?id={league_id}');
            return await response.json();
        }}""")
        
        matches = data.get('fixtures', {}).get('allMatches', [])
        # Filter for finished matches with scores
        finished = [
            str(m['id']) for m in matches 
            if m.get('status', {}).get('finished') and not m.get('status', {}).get('cancelled')
        ]
        
        print(f"✅ Found {len(finished)} finished matches")
        return finished
        
    except Exception as e:
        print(f"❌ Failed to fetch fixtures: {e}")
        return []


async def scrape_fotmob_season(league_id: int = 57, limit: int = None) -> List[Dict]:
    """
    Main entry point for scraping a season.
    """
    results = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Use a real user agent to look legitimate
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        # 1. Go to homepage to init session
        await page.goto("https://www.fotmob.com", wait_until="domcontentloaded")
        
        # 2. Get Fixtures
        match_ids = await collect_fixture_ids(page, league_id)
        
        # Apply limit if needed (for testing)
        if limit:
            match_ids = match_ids[:limit]
            
        print(f"🚀 Starting scrape of {len(match_ids)} matches...")
        
        for mid in match_ids:
            # Check if we already have it locally? (Logic moved to Dagster/Orchestrator usually, 
            # but we can do a simple check here if needed. For now, we scrape all requested.)
            match_data = await scrape_fotmob_match_details(mid, page)
            if match_data:
                results.append(match_data)
                # Small delay to be polite
                await asyncio.sleep(1) 
                
        await browser.close()
        
    return results

def save_fotmob_matches_locally(matches: List[Dict]) -> int:
    """Save scraped matches to data/raw/fotmob_matches"""
    save_dir = Path("data/raw/fotmob_matches/eredivisie/2025-2026")
    save_dir.mkdir(parents=True, exist_ok=True)
    
    count = 0
    for m in matches:
        mid = m['match_info']['match_id']
        path = save_dir / f"match_{mid}.json"
        with open(path, "w") as f:
            json.dump(m, f, indent=2)
        count += 1
        
    print(f"💾 Saved {count} matches locally")
    return count

if __name__ == "__main__":
    async def main():
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            # Test with the user provided ID
            test_id = "4815418"
            data = await scrape_fotmob_match_details(test_id, page)
            
            if data:
                print(f"Found {len(data.get('shots', []))} shots")
                print(json.dumps(data.get('match_info'), indent=2))
            
            await browser.close()

    asyncio.run(main())