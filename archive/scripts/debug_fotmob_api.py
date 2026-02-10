"""
Debug script to inspect Fotmob API response structure.
"""

import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from src.football_rag.data.fotmob import FotmobScraper
import requests


def debug_fotmob_api():
    """Fetch and inspect Fotmob API response."""
    fotmob = FotmobScraper()

    # Get Eredivisie fixtures (league ID 57)
    url = '/api/leagues?id=57'
    token = fotmob._generate_fotmob_token(url)

    headers = {
        'referer': 'https://www.fotmob.com/leagues/57',
        'x-mas': token,
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }

    print("🔍 Fetching Eredivisie data from Fotmob API...")
    print(f"URL: https://www.fotmob.com{url}")
    print(f"Token: {token[:50]}...")
    print()

    response = requests.get(f'https://www.fotmob.com{url}', headers=headers)

    print(f"Status Code: {response.status_code}")
    print()

    if response.status_code != 200:
        print(f"❌ Request failed with status {response.status_code}")
        print(response.text[:500])
        return

    data = response.json()

    print("📋 Top-level keys in response:")
    for key in data.keys():
        print(f"  - {key}: {type(data[key]).__name__}")
    print()

    # Save full response for inspection
    output_file = Path("data/fotmob_api_debug.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"✅ Full response saved to: {output_file}")
    print()

    # Try to find matches data
    print("🔍 Looking for matches data...")

    if 'matches' in data:
        print("  ✅ Found 'matches' key")
        print(f"     Type: {type(data['matches'])}")
        if isinstance(data['matches'], dict):
            print(f"     Keys: {list(data['matches'].keys())}")
        elif isinstance(data['matches'], list):
            print(f"     Length: {len(data['matches'])}")
            if data['matches']:
                print(f"     First item keys: {list(data['matches'][0].keys())}")
    else:
        print("  ❌ No 'matches' key found")

        # Search for match-related keys
        match_keys = [k for k in data.keys() if 'match' in k.lower() or 'fixture' in k.lower()]
        if match_keys:
            print(f"  🔎 Found similar keys: {match_keys}")
            for key in match_keys[:3]:  # Show first 3
                print(f"     - {key}: {type(data[key])}")


if __name__ == "__main__":
    debug_fotmob_api()