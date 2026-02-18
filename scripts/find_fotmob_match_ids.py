"""Find FotMob match IDs for unmapped WhoScored matches by querying FotMob API."""

import asyncio
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

from playwright.async_api import async_playwright


async def collect_all_eredivisie_fixtures() -> List[Dict[str, Any]]:
    """
    Fetch all Eredivisie match fixtures from FotMob API.
    Returns list of match dictionaries with id, home team, away team.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Navigate to FotMob to get cookies
        await page.goto("https://www.fotmob.com", wait_until="domcontentloaded")

        # Fetch fixtures for Eredivisie (league ID = 57)
        print("📅 Fetching all Eredivisie fixtures from FotMob...")
        data = await page.evaluate("""async () => {
            const response = await fetch('/api/leagues?id=57');
            return await response.json();
        }""")

        all_matches = data.get('fixtures', {}).get('allMatches', [])
        print(f"✅ Found {len(all_matches)} total matches in FotMob")

        # Extract relevant info
        fixtures = []
        for match in all_matches:
            home_team = match.get('home', {}).get('name')
            away_team = match.get('away', {}).get('name')
            match_id = str(match.get('id'))
            status = match.get('status', {})
            finished = status.get('finished', False)
            cancelled = status.get('cancelled', False)

            if home_team and away_team:
                fixtures.append({
                    'fotmob_match_id': match_id,
                    'home_team': home_team,
                    'away_team': away_team,
                    'finished': finished,
                    'cancelled': cancelled
                })

        await browser.close()
        return fixtures


def normalize_team_name(team_name: str) -> str:
    """Normalize team name for matching."""
    # Remove common variations
    normalized = team_name.lower().strip()
    normalized = normalized.replace('fc ', '').replace('sc ', '')
    normalized = normalized.replace('-', ' ').replace('_', ' ')
    return normalized


def find_best_match(
    target_team1: str,
    target_team2: str,
    fixtures: List[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """
    Find FotMob match that best matches the target teams.
    Returns match dict or None if no good match found.
    """
    norm_target1 = normalize_team_name(target_team1)
    norm_target2 = normalize_team_name(target_team2)

    for fixture in fixtures:
        norm_home = normalize_team_name(fixture['home_team'])
        norm_away = normalize_team_name(fixture['away_team'])

        # Try both orientations (home/away might be swapped)
        if (norm_target1 in norm_home or norm_home in norm_target1) and \
           (norm_target2 in norm_away or norm_away in norm_target2):
            return fixture

        if (norm_target1 in norm_away or norm_away in norm_target1) and \
           (norm_target2 in norm_home or norm_home in norm_target2):
            return fixture

    return None


async def main():
    base_dir = Path(__file__).parent.parent

    # Load targets from Phase 1
    targets_file = base_dir / "data" / "fotmob_rescrape_targets.json"
    with open(targets_file) as f:
        targets = json.load(f)
    print(f"📊 Loaded {len(targets)} unmapped WhoScored matches")

    # Fetch all Eredivisie fixtures from FotMob
    fixtures = await collect_all_eredivisie_fixtures()
    print(f"📊 Loaded {len(fixtures)} FotMob fixtures")

    # Match WhoScored targets to FotMob fixtures
    matches_to_scrape = []
    not_found = []

    for target in targets:
        ws_id = target['whoscored_id']
        team1 = target['team1']
        team2 = target['team2']

        # Find best match
        best_match = find_best_match(team1, team2, fixtures)

        if best_match:
            matches_to_scrape.append({
                'fotmob_match_id': best_match['fotmob_match_id'],
                'whoscored_id': ws_id,
                'home_team': best_match['home_team'],
                'away_team': best_match['away_team'],
                'finished': best_match['finished'],
                'cancelled': best_match['cancelled']
            })
            print(f"✅ {ws_id}: Found FotMob ID {best_match['fotmob_match_id']} "
                  f"({best_match['home_team']} vs {best_match['away_team']})")
        else:
            not_found.append(target)
            print(f"❌ {ws_id}: No FotMob match found for {team1} vs {team2}")

    # Save results
    output_file = base_dir / "data" / "fotmob_match_ids_to_scrape.json"
    with open(output_file, 'w') as f:
        json.dump(matches_to_scrape, f, indent=2)

    print(f"\n✅ Matched {len(matches_to_scrape)}/{len(targets)} WhoScored matches to FotMob")
    print(f"💾 Saved to: {output_file}")

    if not_found:
        print(f"\n⚠️  {len(not_found)} matches not found in FotMob:")
        for target in not_found[:10]:
            print(f"   - {target['whoscored_id']}: {target['team1']} vs {target['team2']}")
        if len(not_found) > 10:
            print(f"   ... and {len(not_found) - 10} more")


if __name__ == "__main__":
    asyncio.run(main())
