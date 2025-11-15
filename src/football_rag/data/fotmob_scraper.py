"""
Fotmob scraper with MinIO integration and incremental support.
Based on the existing fotmob.py but adapted for production use.
"""

import json
import time
import argparse
import re
from pathlib import Path
from typing import Optional, List, Dict, Any
import pandas as pd
import requests

import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.football_rag.data.fotmob import FotmobScraper


def extract_fotmob_match_id(match_data: Dict[str, Any]) -> str:
    """Extract match ID from Fotmob match data.

    Args:
        match_data: Fotmob match object

    Returns:
        Match ID as string
    """
    return str(match_data["id"])


def collect_all_eredivisie_matches(exclude_match_ids: Optional[set] = None) -> List[Dict[str, Any]]:
    """Collect all finished Eredivisie matches from Fotmob API.

    Args:
        exclude_match_ids: Set of match IDs to exclude (already scraped)

    Returns:
        List of match data dictionaries to scrape
    """
    fotmob = FotmobScraper()
    exclude_match_ids = exclude_match_ids or set()

    print("🔍 Fetching Eredivisie fixtures from Fotmob...")

    # Get Eredivisie fixtures (league ID 57)
    url = '/api/leagues?id=57'
    token = fotmob._generate_fotmob_token(url)

    headers = {
        'referer': 'https://www.fotmob.com/leagues/57',
        'x-mas': token,
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }

    try:
        response = requests.get(f'https://www.fotmob.com{url}', headers=headers)

        if response.status_code != 200:
            print(f"❌ Failed to fetch fixtures: {response.status_code}")
            return []

        data = response.json()
        all_matches = data['matches']['allMatches']

        # Filter finished matches only
        finished_matches = [m for m in all_matches if m.get('status', {}).get('finished')]

        # Exclude already scraped matches
        new_matches = []
        for match in finished_matches:
            match_id = extract_fotmob_match_id(match)
            if match_id not in exclude_match_ids:
                new_matches.append(match)

        print(f"📊 Found {len(finished_matches)} finished matches")
        print(f"📊 {len(new_matches)} matches to scrape (excluding already scraped)")

        return new_matches

    except Exception as e:
        print(f"❌ Error fetching fixtures: {e}")
        return []


def scrape_fotmob_match(match_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Scrape shot data from a single Fotmob match.

    Args:
        match_data: Fotmob match object

    Returns:
        Dictionary with match info and shot data, or None if failed
    """
    match_id = extract_fotmob_match_id(match_data)

    print(f"🎯 Scraping Fotmob match {match_id}: {match_data['home']['name']} vs {match_data['away']['name']}")

    fotmob = FotmobScraper()

    try:
        shots_df = fotmob.scrape_shots(int(match_id))

        if shots_df is not None and len(shots_df) > 0:
            match_info = {
                'match_id': match_id,
                'home_team': match_data['home']['name'],
                'away_team': match_data['away']['name'],
                'home_team_id': match_data['home']['id'],
                'away_team_id': match_data['away']['id'],
                'league': 'eredivisie',
                'season': '2025-2026',
                'match_date': match_data.get('status', {}).get('utcTime', ''),
                'shots': shots_df.to_dict(orient='records')
            }

            print(f"✅ Successfully scraped {len(shots_df)} shots")
            return match_info
        else:
            print("⚠️ No shots found for this match")
            return None

    except Exception as e:
        print(f"❌ Error scraping match {match_id}: {e}")
        return None


def collect_and_scrape_eredivisie(exclude_match_ids: Optional[set] = None) -> List[Dict[str, Any]]:
    """Complete Eredivisie collection and scraping.

    Args:
        exclude_match_ids: Set of match IDs to exclude (already scraped)

    Returns:
        List of successfully scraped match data
    """
    print("🚀 Starting Fotmob Eredivisie collection...")

    # Step 1: Get all match fixtures
    matches_to_scrape = collect_all_eredivisie_matches(exclude_match_ids)

    if not matches_to_scrape:
        print("❌ No matches found to scrape")
        return []

    # Step 2: Scrape each match
    scraped_matches = []

    for i, match_data in enumerate(matches_to_scrape, 1):
        print(f"\n📈 Progress: {i}/{len(matches_to_scrape)}")

        match_info = scrape_fotmob_match(match_data)
        if match_info:
            scraped_matches.append(match_info)

        # Rate limiting
        time.sleep(1)

    print(f"\n🎉 Scraping complete: {len(scraped_matches)} matches scraped successfully")
    return scraped_matches


def save_fotmob_matches_to_minio(matches_data: List[Dict[str, Any]], league: str = "eredivisie", season: str = "2025-2026") -> int:
    """Save individual Fotmob matches as JSON files (local storage for MVP).

    Args:
        matches_data: List of match data dictionaries
        league: League name (default: eredivisie)
        season: Season identifier (default: 2025-2026)

    Returns:
        Number of matches saved successfully
    """
    output_dir = Path(f"data/raw/fotmob_matches/{league}/{season}")
    output_dir.mkdir(parents=True, exist_ok=True)
    saved_count = 0

    for match_data in matches_data:
        match_id = match_data['match_id']
        file_path = output_dir / f"match_{match_id}.json"

        if file_path.exists():
            print(f"⏭️  Match {match_id} already exists, skipping...")
            continue

        with open(file_path, 'w') as f:
            json.dump(match_data, f, indent=2)
        print(f"✅ Saved match {match_id} ({len(match_data['shots'])} shots)")
        saved_count += 1

    return saved_count


def scrape_fotmob_eredivisie(mode: str = "full", league: str = "eredivisie", season: str = "2025-2026") -> List[Dict[str, Any]]:
    """Main function to scrape Fotmob Eredivisie.

    Args:
        mode: 'full' for complete scrape, 'incremental' for only new matches
        league: League name (default: eredivisie)
        season: Season identifier (default: 2025-2026)

    Returns:
        List of scraped match data
    """
    exclude_match_ids = set()

    if mode == "incremental":
        print("🔄 Incremental mode: Checking for already scraped matches...")
        output_dir = Path(f"data/raw/fotmob_matches/{league}/{season}")
        exclude_match_ids = set()
        if output_dir.exists():
            for file in output_dir.glob("match_*.json"):
                exclude_match_ids.add(file.stem.replace("match_", ""))
        print(f"Found {len(exclude_match_ids)} already scraped matches\n")

    print(f"🚀 Starting {mode} Fotmob scraping...\n")
    scraped_data = collect_and_scrape_eredivisie(exclude_match_ids)
    return scraped_data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fotmob scraper for Eredivisie matches")
    parser.add_argument(
        "--mode",
        choices=["full", "incremental"],
        default="incremental",
        help="Scraping mode: 'full' for complete scrape, 'incremental' for only new matches"
    )
    parser.add_argument("--league", default="eredivisie", help="League name")
    parser.add_argument("--season", default="2025-2026", help="Season identifier")

    args = parser.parse_args()

    scraped_data = scrape_fotmob_eredivisie(mode=args.mode, league=args.league, season=args.season)

    if scraped_data and len(scraped_data) > 0:
        # Ensure data directory exists
        Path("data/raw").mkdir(parents=True, exist_ok=True)

        # Save to local JSON (backup)
        local_file = f'data/raw/{args.league}_{args.season.replace("-", "_")}_fotmob.json'
        with open(local_file, 'w') as f:
            json.dump(scraped_data, f, indent=2)
        print(f"✅ Saved locally: {local_file}")

        # Save to MinIO
        uploaded = save_fotmob_matches_to_minio(scraped_data, league=args.league, season=args.season)

        print(f"\n📊 Final Results:")
        print(f"- Total matches scraped: {len(scraped_data)}")
        print(f"- Total shots scraped: {sum(len(m['shots']) for m in scraped_data)}")
        print(f"- Matches uploaded to MinIO: {uploaded}")
    else:
        print("\n⚠️  No new matches to scrape")