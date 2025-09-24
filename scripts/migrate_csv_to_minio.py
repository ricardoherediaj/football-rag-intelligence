"""
Migrate existing WhoScored CSV data to MinIO as individual match JSON files.
"""

import pandas as pd
from pathlib import Path
import re
import sys

sys.path.append(str(Path(__file__).parent.parent))

from src.football_rag.storage.minio_client import MinIOClient


def extract_match_id(match_url: str) -> str:
    """Extract match ID from WhoScored URL.

    Args:
        match_url: Full WhoScored match URL

    Returns:
        Match ID as string

    Example:
        'https://www.whoscored.com/matches/1903740/live/...' -> '1903740'
    """
    match = re.search(r'/matches/(\d+)/', match_url)
    if match:
        return match.group(1)
    raise ValueError(f"Could not extract match ID from URL: {match_url}")


def migrate_csv_to_minio(csv_path: str, league: str = "eredivisie", season: str = "2025-2026"):
    """Migrate CSV data to MinIO as individual match files.

    Args:
        csv_path: Path to the CSV file
        league: League name (default: eredivisie)
        season: Season identifier (default: 2025-2026)
    """
    print(f"Loading CSV from: {csv_path}")
    df = pd.read_csv(csv_path)

    print(f"Total events in CSV: {len(df)}")
    print(f"Unique matches: {df['match_url'].nunique()}")

    minio_client = MinIOClient()
    prefix = f"whoscored/{league}/{season}/"

    uploaded_count = 0
    skipped_count = 0

    for match_url in df['match_url'].unique():
        match_id = extract_match_id(match_url)

        if minio_client.match_exists(prefix, match_id):
            print(f"⏭️  Match {match_id} already exists, skipping...")
            skipped_count += 1
            continue

        match_events = df[df['match_url'] == match_url].to_dict(orient='records')

        match_data = {
            'match_id': match_id,
            'match_url': match_url,
            'league': league,
            'season': season,
            'events': match_events
        }

        object_name = f"{prefix}match_{match_id}.json"

        try:
            minio_client.upload_json(object_name, match_data)
            print(f"✅ Uploaded match {match_id} ({len(match_events)} events)")
            uploaded_count += 1
        except Exception as e:
            print(f"❌ Failed to upload match {match_id}: {e}")

    print(f"\n📊 Migration complete:")
    print(f"  - Uploaded: {uploaded_count} matches")
    print(f"  - Skipped: {skipped_count} matches")
    print(f"  - Total: {uploaded_count + skipped_count} matches")


if __name__ == "__main__":
    csv_file = "data/raw/eredivisie_2025_2026_whoscored.csv"

    if not Path(csv_file).exists():
        print(f"❌ CSV file not found: {csv_file}")
        sys.exit(1)

    migrate_csv_to_minio(csv_file)