"""
Simple WhoScored scraper based on working notebook code.
"""

import json
import time
import pandas as pd
import re
import argparse
from pathlib import Path
from typing import Optional, List
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By

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


def scrape_single_match(url, driver):
    """Scrape match events from a single WhoScored URL"""
    print(f"Scraping: {url}")
    
    driver.get(url)
    time.sleep(3)
    
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    element = soup.select_one('script:-soup-contains("matchCentreData")')
    
    if not element:
        print("❌ matchCentreData not found")
        return None
    
    # Extract and parse match data
    match_data_raw = element.text.split("matchCentreData: ")[1].split(',\n')[0]
    matchdict = json.loads(match_data_raw)
    
    # Process events
    match_events = matchdict['events']
    df = pd.DataFrame(match_events)
    
    if df.empty:
        print("⚠️ No events found")
        return None
    
    # Clean and transform data
    df.dropna(subset='playerId', inplace=True)
    df = df.where(pd.notnull(df), None)
    
    # Rename columns
    df = df.rename({
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
    }, axis=1)
    
    # Add display names
    df['period_display_name'] = df['period'].apply(lambda x: x['displayName'])
    df['type_display_name'] = df['type'].apply(lambda x: x['displayName'])
    df['outcome_type_display_name'] = df['outcome_type'].apply(lambda x: x['displayName'])
    
    # Drop original columns
    df.drop(columns=["period", "type", "outcome_type"], inplace=True)
    
    # Handle missing columns
    if 'is_goal' not in df.columns:
        df['is_goal'] = False
    if 'card_type' not in df.columns:
        df['card_type'] = False
    
    # Filter and select columns
    df = df[~(df['type_display_name'] == "OffsideGiven")]
    
    df = df[[
        'id', 'event_id', 'minute', 'second', 'team_id', 'player_id', 'x', 'y', 'end_x', 'end_y',
        'qualifiers', 'is_touch', 'blocked_x', 'blocked_y', 'goal_mouth_z', 'goal_mouth_y', 'is_shot',
        'card_type', 'is_goal', 'type_display_name', 'outcome_type_display_name', 'period_display_name'
    ]]
    
    # Convert data types
    df[['id', 'event_id', 'minute', 'team_id', 'player_id']] = df[['id', 'event_id', 'minute', 'team_id', 'player_id']].astype('int64')
    df[['second', 'x', 'y', 'end_x', 'end_y']] = df[['second', 'x', 'y', 'end_x', 'end_y']].astype(float)
    df[['is_shot', 'is_goal', 'card_type']] = df[['is_shot', 'is_goal', 'card_type']].astype(bool)
    
    # Handle NaN values
    df['is_goal'] = df['is_goal'].fillna(False)
    df['is_shot'] = df['is_shot'].fillna(False)
    
    # Add match URL to each row
    df['match_url'] = url
    
    # Validate with Pydantic
    validated_events = []
    for _, row in df.iterrows():
        try:
            event = MatchEvent(**row.to_dict())
            validated_events.append(event.model_dump())
        except Exception as e:
            print(f"Validation error: {e}")
    
    validated_df = pd.DataFrame(validated_events)
    print(f'✅ Successfully scraped {len(validated_df)} events')
    return validated_df


def extract_match_id(match_url: str) -> str:
    """Extract match ID from WhoScored URL.

    Args:
        match_url: Full WhoScored match URL

    Returns:
        Match ID as string
    """
    match = re.search(r'/matches/(\d+)/', match_url)
    if match:
        return match.group(1)
    raise ValueError(f"Could not extract match ID from URL: {match_url}")


def collect_all_season_matches(driver, exclude_match_ids: Optional[set] = None):
    """Navigate through calendar to collect all season matches.

    Args:
        driver: Selenium WebDriver instance
        exclude_match_ids: Set of match IDs to exclude (already scraped)

    Returns:
        List of match URLs to scrape
    """
    fixtures_url = "https://www.whoscored.com/Regions/155/Tournaments/13/Seasons/10752/Stages/24542/Fixtures/Netherlands-Eredivisie-2025-2026"
    driver.get(fixtures_url)
    time.sleep(5)

    all_match_urls = set()
    exclude_match_ids = exclude_match_ids or set()

    def collect_matches_from_page():
        """Collect all finished matches from current page view"""
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        matches_found = 0
        containers = soup.find_all('div', class_='Match-module_match__XlKTY')

        for container in containers:
            if container.find('span', class_='Match-module_FT__2rmH7'):
                score_link = container.find('a', class_='Match-module_score__5Ghhj')
                if score_link and score_link.get('href'):
                    match_url = f"https://www.whoscored.com{score_link['href']}"
                    match_id = extract_match_id(match_url)

                    if match_id not in exclude_match_ids:
                        all_match_urls.add(match_url)
                        matches_found += 1

        return matches_found

    # Go back to season start, collecting matches along the way
    print("Going back to season start...")
    weeks_back = 0
    max_weeks_back = 20  # Aug to Nov = ~14 weeks, add buffer

    while weeks_back < max_weeks_back:
        # Collect matches from current week view
        matches = collect_matches_from_page()
        if matches > 0:
            print(f"  Week {weeks_back}: Found {matches} finished matches")

        # Try to go back one more week
        try:
            prev_button = driver.find_element(By.ID, "dayChangeBtn-prev")
            if not prev_button.is_enabled():
                print(f"Reached beginning of calendar at {weeks_back} weeks back")
                break
            prev_button.click()
            time.sleep(2)
            weeks_back += 1
        except Exception as e:
            print(f"Stopped going back after {weeks_back} weeks: {e}")
            break

    print(f"Went back {weeks_back} weeks to season start")

    # Now go forward from season start, collecting matches
    print("Going forward through season...")
    weeks_forward = 0
    max_weeks_forward = 25  # Extra buffer to reach current date

    while weeks_forward < max_weeks_forward:
        # Collect matches from current week view
        matches = collect_matches_from_page()
        if matches > 0:
            print(f"  Week +{weeks_forward}: Found {matches} finished matches")

        # Try to go forward one more week
        try:
            next_button = driver.find_element(By.ID, "dayChangeBtn-next")
            if not next_button.is_enabled():
                print(f"Reached current week at +{weeks_forward} weeks forward")
                break
            next_button.click()
            time.sleep(2)
            weeks_forward += 1
        except Exception as e:
            print(f"Stopped going forward after {weeks_forward} weeks: {e}")
            break

    print(f"Scanned {weeks_back + weeks_forward} total weeks")
    print(f"Found {len(all_match_urls)} unique matches to scrape")
    return list(all_match_urls)


def collect_and_scrape_complete_season(driver, exclude_match_ids: Optional[set] = None):
    """Complete season collection with detailed progress output.

    Args:
        driver: Selenium WebDriver instance
        exclude_match_ids: Set of match IDs to exclude (already scraped)
    """

    print("Step 1: Collecting all match URLs...")
    all_match_urls = collect_all_season_matches(driver, exclude_match_ids)
    print(f"Found {len(all_match_urls)} finished matches\n")
    
    if not all_match_urls:
        print("No matches found. Exiting.")
        return None
    
    print("Step 2: Scraping match data...")
    all_match_data = []
    
    for i, url in enumerate(all_match_urls, 1):
        print(f"Scraping match {i}/{len(all_match_urls)}")
        print(f"Scraping: {url}")
        
        try:
            match_df = scrape_single_match(url, driver)
            
            if match_df is not None:
                all_match_data.append(match_df)
                print(f"✅ Successfully scraped {len(match_df)} events\n")
            else:
                print("❌ No data returned\n")
                
        except Exception as e:
            print(f"❌ Error scraping {url}: {str(e)}\n")
            continue
        
        time.sleep(2)
    
    if all_match_data:
        combined_df = pd.concat(all_match_data, ignore_index=True)
        print(f"✅ Successfully scraped {len(all_match_data)} matches with {len(combined_df)} total events")
        return combined_df
    else:
        print("❌ No match data was scraped")
        return None


def scrape_complete_season(mode: str = "full", league: str = "eredivisie", season: str = "2025-2026"):
    """Main function to scrape complete season.

    Args:
        mode: 'full' for complete scrape, 'incremental' for only new matches
        league: League name (default: eredivisie)
        season: Season identifier (default: 2025-2026)

    Returns:
        DataFrame with scraped match data
    """
    driver = webdriver.Chrome()

    try:
        exclude_match_ids = set()

        if mode == "incremental":
            print("🔄 Incremental mode: Checking for already scraped matches...")
            output_dir = Path(f"data/raw/whoscored_matches/{league}/{season}")
            exclude_match_ids = set()
            if output_dir.exists():
                for file in output_dir.glob("match_*.json"):
                    exclude_match_ids.add(file.stem.replace("match_", ""))
            print(f"Found {len(exclude_match_ids)} already scraped matches\n")

        print(f"Starting {mode} season collection...\n")
        season_data = collect_and_scrape_complete_season(driver, exclude_match_ids)
        return season_data

    finally:
        driver.quit()


def save_matches_to_minio(matches_df: pd.DataFrame, league: str = "eredivisie", season: str = "2025-2026") -> int:
    """Save individual matches as JSON files (local storage for MVP).

    Args:
        matches_df: DataFrame containing all match events
        league: League name (default: eredivisie)
        season: Season identifier (default: 2025-2026)

    Returns:
        Number of matches saved successfully
    """
    output_dir = Path(f"data/raw/whoscored_matches/{league}/{season}")
    output_dir.mkdir(parents=True, exist_ok=True)
    saved_count = 0

    for match_url in matches_df['match_url'].unique():
        match_id = extract_match_id(match_url)
        file_path = output_dir / f"match_{match_id}.json"

        if file_path.exists():
            print(f"⏭️  Match {match_id} already exists, skipping...")
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
        print(f"✅ Saved match {match_id} ({len(match_events)} events)")
        saved_count += 1

    return saved_count


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WhoScored scraper for Eredivisie matches")
    parser.add_argument(
        "--mode",
        choices=["full", "incremental"],
        default="incremental",
        help="Scraping mode: 'full' for complete scrape, 'incremental' for only new matches"
    )
    parser.add_argument("--league", default="eredivisie", help="League name")
    parser.add_argument("--season", default="2025-2026", help="Season identifier")

    args = parser.parse_args()

    season_data = scrape_complete_season(mode=args.mode, league=args.league, season=args.season)

    if season_data is not None and len(season_data) > 0:
        # Ensure data directory exists
        Path("data/raw").mkdir(parents=True, exist_ok=True)

        # Save to local CSV (backup)
        local_file = f'data/raw/{args.league}_{args.season.replace("-", "_")}_whoscored.csv'
        season_data.to_csv(local_file, index=False)
        print(f"✅ Saved locally: {local_file}")

        # Save to MinIO
        uploaded = save_matches_to_minio(season_data, league=args.league, season=args.season)

        print("\n📊 Final Results:")
        print(f"- Total events scraped: {len(season_data)}")
        print(f"- Unique matches scraped: {season_data['match_url'].nunique()}")
        print(f"- Matches uploaded to MinIO: {uploaded}")
    else:
        print("\n⚠️  No new matches to scrape")