"""Generate match mapping from LOCAL files (no MinIO).

Reads:
- data/raw/eredivisie_2025_2026_whoscored.csv
- data/raw/eredivisie_2025_2026_fotmob.json

Outputs:
- data/datasets/match_mapping.json (WhoScored ↔ Fotmob mapping)

This replaces the MinIO-based generate_match_mapping.py for MVP.
"""

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from difflib import SequenceMatcher
import pandas as pd

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def normalize_team_name(team_name: str) -> str:
    """Normalize team name for matching."""
    normalized = team_name.lower()
    normalized = re.sub(r'\b(fc|sc)\b', '', normalized)  # Remove common prefixes
    normalized = re.sub(r'[^\w\s]', '', normalized)  # Remove special characters
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    return normalized


def calculate_similarity(name1: str, name2: str) -> float:
    """Calculate similarity between two team names (0-1)."""
    norm1 = normalize_team_name(name1)
    norm2 = normalize_team_name(name2)
    return SequenceMatcher(None, norm1, norm2).ratio()


def load_whoscored_from_csv() -> list:
    """Load WhoScored data from CSV."""
    csv_path = Path("data/raw/eredivisie_2025_2026_whoscored.csv")
    logger.info(f"Loading WhoScored data from {csv_path}")

    df = pd.read_csv(csv_path)

    # Group by match (each match has multiple event rows)
    matches = []
    for match_url, group in df.groupby('match_url'):
        match_id = re.search(r'/matches/(\d+)/', match_url)
        if match_id:
            match_id = match_id.group(1)
        else:
            continue

        # Get team names from first row (they're the same for all events)
        first_row = group.iloc[0]

        matches.append({
            'match_id': match_id,
            'match_url': match_url,
            'home_team': first_row.get('home_team', 'Unknown'),
            'away_team': first_row.get('away_team', 'Unknown'),
            'event_count': len(group)
        })

    logger.info(f"✅ Loaded {len(matches)} WhoScored matches")
    return matches


def load_fotmob_from_json() -> list:
    """Load Fotmob data from JSON."""
    json_path = Path("data/raw/eredivisie_2025_2026_fotmob.json")
    logger.info(f"Loading Fotmob data from {json_path}")

    with open(json_path, 'r') as f:
        matches = json.load(f)

    logger.info(f"✅ Loaded {len(matches)} Fotmob matches")
    return matches


def match_whoscored_with_fotmob(whoscored_matches: list, fotmob_matches: list) -> dict:
    """Match WhoScored and Fotmob using fuzzy team name matching."""
    logger.info("🔗 Matching WhoScored ↔ Fotmob...")

    mappings = {}
    matched_fotmob_ids = set()
    counter = 1

    for ws_match in whoscored_matches:
        ws_home = ws_match['home_team']
        ws_away = ws_match['away_team']

        best_match = None
        best_score = 0.0

        for fm_match in fotmob_matches:
            if fm_match["match_id"] in matched_fotmob_ids:
                continue

            fm_home = fm_match["home_team"]
            fm_away = fm_match["away_team"]

            # Calculate similarity (both orientations)
            home_sim = calculate_similarity(ws_home, fm_home)
            away_sim = calculate_similarity(ws_away, fm_away)
            score1 = (home_sim + away_sim) / 2

            # Try reversed
            home_sim_rev = calculate_similarity(ws_home, fm_away)
            away_sim_rev = calculate_similarity(ws_away, fm_home)
            score2 = (home_sim_rev + away_sim_rev) / 2

            final_score = max(score1, score2)

            if final_score > best_score and final_score > 0.6:  # 60% threshold
                best_match = fm_match
                best_score = final_score

        if best_match:
            unified_id = f"unified_match_{counter:03d}"

            mappings[unified_id] = {
                "whoscored_id": ws_match["match_id"],
                "fotmob_id": best_match["match_id"],
                "home_team": best_match["home_team"],  # Use Fotmob names (cleaner)
                "away_team": best_match["away_team"],
                "match_date": best_match.get("match_date", ""),
                "league": "Eredivisie",
                "season": "2025-2026",
                "similarity_score": round(best_score, 3),
                "created_at": datetime.utcnow().isoformat() + "Z"
            }

            matched_fotmob_ids.add(best_match["match_id"])
            counter += 1

            logger.info(f"✅ Match #{counter-1}: {best_match['home_team']} vs {best_match['away_team']} (score: {best_score:.3f})")
        else:
            logger.warning(f"❌ No match for: {ws_home} vs {ws_away}")

    # Report unmatched Fotmob
    unmatched = [fm for fm in fotmob_matches if fm["match_id"] not in matched_fotmob_ids]
    if unmatched:
        logger.warning(f"⚠️  {len(unmatched)} Fotmob matches unmatched")

    logger.info(f"🎯 Created {len(mappings)} mappings")
    return mappings


def save_mapping_locally(mappings: dict):
    """Save mappings to data/datasets/match_mapping.json."""
    output_path = Path("data/datasets/match_mapping.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info(f"💾 Saving to {output_path}")

    with open(output_path, 'w') as f:
        json.dump(mappings, f, indent=2)

    logger.info(f"✅ Saved {len(mappings)} mappings")


def main():
    logger.info("🚀 Generating local match mapping...")

    # Load data
    whoscored_matches = load_whoscored_from_csv()
    fotmob_matches = load_fotmob_from_json()

    if not whoscored_matches or not fotmob_matches:
        logger.error("❌ Failed to load data")
        return

    # Generate mappings
    mappings = match_whoscored_with_fotmob(whoscored_matches, fotmob_matches)

    if not mappings:
        logger.error("❌ No mappings created")
        return

    # Save locally
    save_mapping_locally(mappings)

    logger.info("🎉 Match mapping complete!")
    logger.info(f"📁 Output: data/datasets/match_mapping.json")
    logger.info(f"📊 Next: Use this mapping for ingestion")


if __name__ == "__main__":
    main()
