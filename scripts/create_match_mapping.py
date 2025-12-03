"""Create match mapping between WhoScored and Fotmob using team IDs."""

import json
import csv
from pathlib import Path


def main():
    base_dir = Path(__file__).parent.parent

    print("🚀 Creating match mapping using team IDs...")

    # Load WhoScored team ID → name mapping
    csv_path = base_dir / "data" / "raw" / "eredivisie_whoscored_team_ids.csv"
    ws_team_map = {}
    with open(csv_path) as f:
        for row in csv.DictReader(f):
            ws_team_map[int(row['whoscored_id'])] = row['team_name']
    print(f"📊 Loaded {len(ws_team_map)} WhoScored teams")

    # Load Fotmob matches
    fotmob_path = base_dir / "data" / "raw" / "eredivisie_2025_2026_fotmob.json"
    with open(fotmob_path) as f:
        fotmob_matches = json.load(f)
    print(f"📊 Loaded {len(fotmob_matches)} Fotmob matches")

    # Load WhoScored matches
    ws_dir = base_dir / "data" / "raw" / "whoscored_matches" / "eredivisie" / "2025-2026"
    ws_files = sorted(ws_dir.glob("match_*.json"))
    print(f"📊 Found {len(ws_files)} WhoScored matches")

    mappings = {}
    matched_fotmob = set()

    for ws_file in ws_files:
        ws_id = ws_file.stem.replace('match_', '')

        # Extract team IDs from events
        with open(ws_file) as f:
            events = json.load(f).get('events', [])
        ws_team_ids = {e['team_id'] for e in events if 'team_id' in e}

        if len(ws_team_ids) != 2:
            print(f"❌ {ws_id}: Expected 2 teams, found {len(ws_team_ids)}")
            continue

        # Convert to team names
        ws_team_names = {ws_team_map[tid] for tid in ws_team_ids}

        # Find matching Fotmob match
        fm_match = None
        for fm in fotmob_matches:
            if {fm['home_team'], fm['away_team']} == ws_team_names:
                if fm['match_id'] not in matched_fotmob:
                    fm_match = fm
                    break

        if not fm_match:
            print(f"❌ {ws_id}: No match for {ws_team_names}")
            continue

        # Map WhoScored team ID → Fotmob team ID
        team_id_map = {}
        for ws_tid in ws_team_ids:
            name = ws_team_map[ws_tid]
            team_id_map[ws_tid] = (fm_match['home_team_id'] if name == fm_match['home_team']
                                   else fm_match['away_team_id'])

        mappings[ws_id] = {
            "whoscored_id": ws_id,
            "whoscored_team_ids": sorted(list(ws_team_ids)),
            "fotmob_id": str(fm_match['match_id']),
            "fotmob_home_team_id": fm_match['home_team_id'],
            "fotmob_away_team_id": fm_match['away_team_id'],
            "ws_to_fotmob_team_mapping": team_id_map,
            "home_team": fm_match['home_team'],
            "away_team": fm_match['away_team'],
            "match_date": fm_match.get('match_date', '')
        }

        matched_fotmob.add(fm_match['match_id'])
        print(f"✅ {ws_id}: {fm_match['home_team']} vs {fm_match['away_team']}")

    # Save mapping
    output_path = base_dir / "data" / "match_mapping.json"
    with open(output_path, 'w') as f:
        json.dump(mappings, f, indent=2)

    print(f"\n✅ Mapped {len(mappings)}/{len(ws_files)} matches")
    print(f"💾 Saved to: {output_path}")


if __name__ == "__main__":
    main()