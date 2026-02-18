"""Identify unmapped WhoScored matches and extract metadata for FotMob re-scraping."""

import csv
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

import duckdb


def main():
    base_dir = Path(__file__).parent.parent

    # Connect to DuckDB
    db = duckdb.connect(str(base_dir / "data" / "lakehouse.duckdb"))

    # Load WhoScored team ID mapping
    csv_path = base_dir / "data" / "raw" / "eredivisie_whoscored_team_ids.csv"
    ws_team_map = {}
    with open(csv_path) as f:
        for row in csv.DictReader(f):
            ws_team_map[int(row['whoscored_id'])] = row['team_name']
    print(f"📊 Loaded {len(ws_team_map)} WhoScored team mappings")

    # Get existing mappings
    try:
        mapped_ws_ids = {
            str(row[0])
            for row in db.execute("SELECT whoscored_match_id FROM match_mapping").fetchall()
        }
        print(f"📊 Found {len(mapped_ws_ids)} existing mappings in DuckDB")
    except:
        # Fallback to JSON file
        mapping_file = base_dir / "data" / "match_mapping.json"
        if mapping_file.exists():
            with open(mapping_file) as f:
                mapping_data = json.load(f)
                mapped_ws_ids = set(mapping_data.keys())
            print(f"📊 Found {len(mapped_ws_ids)} existing mappings in JSON")
        else:
            mapped_ws_ids = set()
            print("⚠️  No existing mappings found")

    # Get all WhoScored matches
    ws_query = "SELECT match_id, data FROM bronze_matches WHERE source='whoscored'"
    ws_matches = db.execute(ws_query).fetchall()
    print(f"📊 Total WhoScored matches: {len(ws_matches)}")

    # Identify unmapped matches
    targets: List[Dict[str, Any]] = []

    for ws_id, ws_data_json in ws_matches:
        if str(ws_id) in mapped_ws_ids:
            continue  # Already mapped

        # Parse match data
        ws_data = json.loads(ws_data_json)
        events = ws_data.get('events', [])

        if not events:
            print(f"⚠️  {ws_id}: No events found, skipping")
            continue

        # Extract team IDs from events
        ws_team_ids = {e['team_id'] for e in events if 'team_id' in e}
        if len(ws_team_ids) != 2:
            print(f"⚠️  {ws_id}: Expected 2 teams, found {len(ws_team_ids)}, skipping")
            continue

        # Convert to team names
        try:
            team_names = [ws_team_map[tid] for tid in sorted(ws_team_ids)]
        except KeyError as e:
            print(f"⚠️  {ws_id}: Unknown team ID {e}, skipping")
            continue

        # Extract match date from first event (rough estimate)
        # WhoScored events don't have absolute timestamps, only minute/second
        # We'll use match URL as fallback
        match_url = ws_data.get('match_url', '')

        targets.append({
            'whoscored_id': str(ws_id),
            'team1': team_names[0],
            'team2': team_names[1],
            'match_url': match_url,
            'event_count': len(events)
        })

        print(f"✅ {ws_id}: {team_names[0]} vs {team_names[1]}")

    print(f"\n📋 Identified {len(targets)} unmapped WhoScored matches")

    # Save to JSON for next script
    output_file = base_dir / "data" / "fotmob_rescrape_targets.json"
    with open(output_file, 'w') as f:
        json.dump(targets, f, indent=2)
    print(f"💾 Saved targets to: {output_file}")

    # Also save CSV for manual review
    csv_file = base_dir / "data" / "unmapped_whoscored_matches.csv"
    with open(csv_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['whoscored_id', 'team1', 'team2', 'match_url', 'event_count'])
        writer.writeheader()
        writer.writerows(targets)
    print(f"📝 CSV report: {csv_file}")

    db.close()


if __name__ == "__main__":
    main()
