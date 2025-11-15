"""
Simple script to check scraped data status.
Shows count of matches from each source.
"""

from pathlib import Path
import json


def check_data_status():
    print("📊 Data Status Report")
    print("=" * 60)

    # Check WhoScored matches
    whoscored_dir = Path("data/raw/whoscored_matches/eredivisie/2025-2026")
    if whoscored_dir.exists():
        whoscored_files = list(whoscored_dir.glob("match_*.json"))
        print(f"\n✅ WhoScored: {len(whoscored_files)} matches")
        print(f"   Location: {whoscored_dir}")
    else:
        print(f"\n❌ WhoScored: No data found")
        print(f"   Expected: {whoscored_dir}")

    # Check Fotmob matches
    fotmob_dir = Path("data/raw/fotmob_matches/eredivisie/2025-2026")
    if fotmob_dir.exists():
        fotmob_files = list(fotmob_dir.glob("match_*.json"))
        print(f"\n✅ Fotmob: {len(fotmob_files)} matches")
        print(f"   Location: {fotmob_dir}")

        # Sample a match to show structure
        if fotmob_files:
            sample_file = fotmob_files[0]
            with open(sample_file) as f:
                data = json.load(f)
            print(f"\n   Sample match: {data.get('home_team')} vs {data.get('away_team')}")
            print(f"   Shots: {len(data.get('shots', []))}")
    else:
        print(f"\n❌ Fotmob: No data found")
        print(f"   Expected: {fotmob_dir}")

    # Check legacy CSV/JSON files
    legacy_csv = Path("data/raw/eredivisie_2025_2026_whoscored.csv")
    legacy_json = Path("data/raw/eredivisie_2025_2026_fotmob.json")

    print(f"\n📁 Legacy files:")
    if legacy_csv.exists():
        print(f"   ✅ WhoScored CSV: {legacy_csv.stat().st_size / 1024 / 1024:.1f}MB")
    else:
        print(f"   ❌ WhoScored CSV: Not found")

    if legacy_json.exists():
        print(f"   ✅ Fotmob JSON: {legacy_json.stat().st_size / 1024 / 1024:.1f}MB")
    else:
        print(f"   ❌ Fotmob JSON: Not found")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    check_data_status()
