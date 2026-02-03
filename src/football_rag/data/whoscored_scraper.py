"""
WhoScored scraper refactored to use Playwright (async).
"""

import json
import asyncio
import pandas as pd
import re
import argparse
from pathlib import Path
from typing import Optional, List, Dict, Any
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Page

from pydantic import BaseModel

import sys
sys.path.append(str(Path(__file__).parent.parent.parent))


class MatchEvent(BaseModel):
    id: int
    event_id: int
    minute: int
    second: Optional[float] = None
    team_id: int
    player_id: int
    x: float
    y: float
    end_x: Optional[float] = None
    end_y: Optional[float] = None
    qualifiers: List[dict]
    is_touch: bool
    blocked_x: Optional[float] = None
    blocked_y: Optional[float] = None
    goal_mouth_z: Optional[float] = None
    goal_mouth_y: Optional[float] = None
    is_shot: bool
    card_type: bool
    is_goal: bool
    type_display_name: str
    outcome_type_display_name: str
    period_display_name: str
    match_url: str


async def scrape_single_match(url: str, page: Page) -> Optional[pd.DataFrame]:
    """Scrape match events from a single WhoScored URL using Playwright"""
    print(f"Scraping: {url}")
    
    try:
        # Changed to domcontentloaded to avoid timeouts on heavy ad scripts
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        
        # Explicitly wait for the data script we need
        try:
            await page.wait_for_selector('script:-soup-contains("matchCentreData")', state="attached", timeout=30000)
        except Exception:
            print("Warning: Timeout waiting for matchCentreData script, attempting to parse anyway...")
        
        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')
        element = soup.select_one('script:-soup-contains("matchCentreData")')
        
        if not element:
            print("❌ matchCentreData not found")
            return None
        
        # Extract and parse match data
        # The script usually looks like: var matchCentreData = {...};
        pattern = r"matchCentreData:\s*(\{.*?\})(?:,\n|;)"
        match = re.search(pattern, element.text)
        
        if not match:
            # Fallback to older split logic if regex fails
            try:
                match_data_raw = element.text.split("matchCentreData: ")[1].split(',\n')[0]
            except IndexError:
                print("❌ Could not parse matchCentreData from script")
                return None
        else:
            match_data_raw = match.group(1)

        matchdict = json.loads(match_data_raw)
        
        # Process events
        match_events = matchdict['events']
        df = pd.DataFrame(match_events)
        
        if df.empty:
            print("⚠️ No events found")
            return None
        
        # Clean and transform data
        df = df[df['playerId'].notna()].copy()
        df = df.where(pd.notnull(df), None)
        
        # Rename columns
        rename_map = {
            'eventId': 'event_id',
            'outcomeType': 'outcome_type',
            'isTouch': 'is_touch',
            'playerId': 'player_id',
            'teamId': 'team_id',
            'endX': 'end_x',
            'endY': 'end_y',
            'blockedX': 'blocked_x',
            'blockedY': 'blocked_y',
            'goalMouthZ': 'goal_mouth_z',
            'goalMouthY': 'goal_mouth_y',
            'isShot': 'is_shot',
            'cardType': 'card_type',
            'isGoal': 'is_goal'
        }
        df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
        
        # Add display names
        df['period_display_name'] = df['period'].apply(lambda x: x['displayName'] if isinstance(x, dict) else x)
        df['type_display_name'] = df['type'].apply(lambda x: x['displayName'] if isinstance(x, dict) else x)
        df['outcome_type_display_name'] = df['outcome_type'].apply(lambda x: x['displayName'] if isinstance(x, dict) else x)
        
        # Drop original columns
        df.drop(columns=["period", "type", "outcome_type"], inplace=True, errors='ignore')
        
        # Handle missing columns
        for col in ['is_goal', 'card_type', 'is_shot']:
            if col not in df.columns:
                df[col] = False
        
        # Filter and select columns
        df = df[~(df['type_display_name'] == "OffsideGiven")]
        
        final_cols = [
            'id', 'event_id', 'minute', 'second', 'team_id', 'player_id', 'x', 'y', 'end_x', 'end_y',
            'qualifiers', 'is_touch', 'blocked_x', 'blocked_y', 'goal_mouth_z', 'goal_mouth_y', 'is_shot',
            'card_type', 'is_goal', 'type_display_name', 'outcome_type_display_name', 'period_display_name'
        ]
        
        # Ensure all columns exist
        for col in final_cols:
            if col not in df.columns:
                df[col] = None

        df = df[final_cols]
        
        # Convert data types safely
        int_cols = ['id', 'event_id', 'minute', 'team_id', 'player_id']
        for col in int_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype('int64')

        float_cols = ['second', 'x', 'y', 'end_x', 'end_y']
        for col in float_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce').astype(float)

        bool_cols = ['is_shot', 'is_goal', 'card_type']
        for col in bool_cols:
            df[col] = df[col].fillna(False).astype(bool)
        
        # Add match URL to each row
        df['match_url'] = url
        
        # Validate with Pydantic
        validated_events = []
        for _, row in df.iterrows():
            try:
                event = MatchEvent(**row.to_dict())
                validated_events.append(event.model_dump())
            except Exception as e:
                # Silently skip validation errors for minor fields but log if widespread
                pass
        
        if not validated_events:
            print("⚠️ All events failed validation")
            return None

        validated_df = pd.DataFrame(validated_events)
        print(f'✅ Successfully scraped {len(validated_df)} events')
        return validated_df

    except Exception as e:
        print(f"❌ Error scraping {url}: {e}")
        return None


def extract_match_id(match_url: str) -> str:
    """Extract match ID from WhoScored URL."""
    match = re.search(r'/[Mm]atches/(\d+)/', match_url)
    if match:
        return match.group(1)
    raise ValueError(f"Could not extract match ID from URL: {match_url}")


async def collect_all_season_matches(page: Page, exclude_match_ids: Optional[set] = None):
    """Navigate through calendar to collect all season matches using Playwright."""
    fixtures_url = "https://www.whoscored.com/Regions/155/Tournaments/13/Seasons/10752/Stages/24542/Fixtures/Netherlands-Eredivisie-2025-2026"
    await page.goto(fixtures_url, wait_until="domcontentloaded", timeout=60000)
    await page.wait_for_selector(".Match-module_match__XlKTY", timeout=30000)

    all_match_urls = set()
    exclude_match_ids = exclude_match_ids or set()

    async def collect_matches_from_page():
        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')
        matches_found = 0
        containers = soup.find_all('div', class_='Match-module_match__XlKTY')

        for container in containers:
            if container.find('span', class_='Match-module_FT__2rmH7'):
                score_link = container.find('a', class_='Match-module_score__5Ghhj')
                if score_link and score_link.get('href'):
                    match_url = f"https://www.whoscored.com{score_link['href']}"
                    try:
                        match_id = extract_match_id(match_url)
                        if match_id not in exclude_match_ids:
                            all_match_urls.add(match_url)
                            matches_found += 1
                    except ValueError:
                        continue

        return matches_found

    # Go back to season start
    print("Going back to season start...")
    weeks_back = 0
    max_weeks_back = 15

    while weeks_back < max_weeks_back:
        matches = await collect_matches_from_page()
        if matches > 0:
            print(f"  Week -{weeks_back}: Found {matches} finished matches")

        try:
            prev_button = page.locator("#dayChangeBtn-prev")
            if await prev_button.is_visible() and await prev_button.is_enabled():
                await prev_button.click()
                await asyncio.sleep(2)
                weeks_back += 1
            else:
                break
        except Exception:
            break

    # Go forward to current week
    print("Going forward through season...")
    weeks_forward = 0
    max_weeks_forward = 30

    while weeks_forward < max_weeks_forward:
        matches = await collect_matches_from_page()
        
        try:
            next_button = page.locator("#dayChangeBtn-next")
            if await next_button.is_visible() and await next_button.is_enabled():
                await next_button.click()
                await asyncio.sleep(2)
                weeks_forward += 1
            else:
                break
        except Exception:
            break

    print(f"Found {len(all_match_urls)} unique matches to scrape")
    return list(all_match_urls)


async def scrape_complete_season_async(mode: str = "full", league: str = "eredivisie", season: str = "2025-2026"):
    """Main async function to scrape complete season."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Use a realistic user agent
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        try:
            exclude_match_ids = set()
            if mode == "incremental":
                output_dir = Path(f"data/raw/whoscored_matches/{league}/{season}")
                if output_dir.exists():
                    for file in output_dir.glob("match_*.json"):
                        exclude_match_ids.add(file.stem.replace("match_", ""))

            print(f"Starting {mode} season collection...")
            all_match_urls = await collect_all_season_matches(page, exclude_match_ids)
            
            all_match_data = []
            for i, url in enumerate(all_match_urls, 1):
                print(f"Match {i}/{len(all_match_urls)}")
                df = await scrape_single_match(url, page)
                if df is not None:
                    all_match_data.append(df)
                await asyncio.sleep(1) # Small delay between matches

            if not all_match_data:
                return None
                
            return pd.concat(all_match_data, ignore_index=True)

        finally:
            await browser.close()


def save_matches_locally(matches_df: pd.DataFrame, league: str = "eredivisie", season: str = "2025-2026"):
    output_dir = Path(f"data/raw/whoscored_matches/{league}/{season}")
    output_dir.mkdir(parents=True, exist_ok=True)
    saved_count = 0

    for match_url in matches_df['match_url'].unique():
        match_id = extract_match_id(match_url)
        file_path = output_dir / f"match_{match_id}.json"

        if file_path.exists():
            continue

        match_events = matches_df[matches_df['match_url'] == match_url].to_dict(orient='records')
        match_data = {
            'match_id': match_id,
            'match_url': match_url,
            'league': league,
            'season': season,
            'events': match_events
        }

        with open(file_path, 'w') as f:
            json.dump(match_data, f, indent=2)
        saved_count += 1

    return saved_count


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["full", "incremental"], default="incremental")
    parser.add_argument("--league", default="eredivisie")
    parser.add_argument("--season", default="2025-2026")
    args = parser.parse_args()

    loop = asyncio.get_event_loop()
    season_data = loop.run_until_complete(scrape_complete_season_async(args.mode, args.league, args.season))

    if season_data is not None:
        save_matches_locally(season_data, args.league, args.season)
        print(f"Done. Scraped {len(season_data)} events.")
    else:
        print("No matches to scrape.")