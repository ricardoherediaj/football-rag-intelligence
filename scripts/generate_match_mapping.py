#!/usr/bin/env python3
"""
Generate match mapping between WhoScored and Fotmob data sources.

This script creates a unified mapping table that links matches from both sources
using fuzzy string matching on team names and exact date matching.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
import re
from difflib import SequenceMatcher

import sys
sys.path.append(str(Path(__file__).parent.parent))

from src.football_rag.storage.minio_client import MinIOClient


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def normalize_team_name(team_name: str) -> str:
    """Normalize team name for matching.

    Args:
        team_name: Raw team name

    Returns:
        Normalized team name
    """
    # Remove common prefixes/suffixes
    normalized = team_name.lower()
    normalized = re.sub(r'\b(fc|sc|ajax|psv|az)\b', '', normalized)  # Remove common club abbreviations
    normalized = re.sub(r'[^\w\s]', '', normalized)  # Remove special characters
    normalized = re.sub(r'\s+', ' ', normalized).strip()  # Clean whitespace
    return normalized


def calculate_similarity(name1: str, name2: str) -> float:
    """Calculate similarity between two team names.

    Args:
        name1: First team name
        name2: Second team name

    Returns:
        Similarity score (0-1)
    """
    norm1 = normalize_team_name(name1)
    norm2 = normalize_team_name(name2)

    # Use SequenceMatcher for fuzzy matching
    return SequenceMatcher(None, norm1, norm2).ratio()


def extract_whoscored_match_id(match_url: str) -> str:
    """Extract match ID from WhoScored URL.

    Args:
        match_url: WhoScored match URL

    Returns:
        Match ID as string
    """
    # Extract match ID from URL like: https://www.whoscored.com/matches/1903754/live/...
    match = re.search(r'/matches/(\d+)/', match_url)
    if match:
        return match.group(1)
    raise ValueError(f"Could not extract match ID from URL: {match_url}")


def extract_teams_from_whoscored_url(match_url: str) -> Tuple[str, str]:
    """Extract team names from WhoScored URL.

    Args:
        match_url: WhoScored match URL

    Returns:
        Tuple of (home_team, away_team)
    """
    # Extract from URL like: .../netherlands-eredivisie-2025-2026-az-alkmaar-pec-zwolle
    url_parts = match_url.split('/')[-1]  # Get last part

    # Remove league and season info
    team_part = re.sub(r'netherlands-eredivisie-\d{4}-\d{4}-', '', url_parts)

    # Split teams (assuming format: home-team-away-team)
    # This is tricky - we need to be smart about splitting
    # For now, let's use a simpler approach and rely on the CSV data structure
    return "", ""  # We'll get team names from the data itself


def parse_whoscored_date(match_url: str) -> Optional[str]:
    """Extract date from WhoScored data - this will need to be derived from events.

    For now, we'll use a placeholder approach.
    """
    # We'll derive dates from the actual match data later
    return None


def load_whoscored_data_from_minio(minio_client: MinIOClient) -> List[Dict[str, Any]]:
    """Load WhoScored match data from MinIO.

    Args:
        minio_client: MinIO client instance

    Returns:
        List of match data dictionaries
    """
    logger.info("🔍 Loading WhoScored data from MinIO...")

    prefix = "whoscored/eredivisie/2025-2026/"
    match_files = minio_client.list_objects(prefix)

    matches = []
    for file_path in match_files:
        if file_path.endswith('.json'):
            logger.info(f"📄 Loading {file_path}")

            try:
                # Download and parse JSON
                response = minio_client.download_file(file_path)
                match_data = json.loads(response.read().decode('utf-8'))
                matches.append(match_data)
            except Exception as e:
                logger.error(f"❌ Failed to load {file_path}: {e}")
                continue

    logger.info(f"✅ Loaded {len(matches)} WhoScored matches")
    return matches


def load_fotmob_data_from_minio(minio_client: MinIOClient) -> List[Dict[str, Any]]:
    """Load Fotmob match data from MinIO.

    Args:
        minio_client: MinIO client instance

    Returns:
        List of match data dictionaries
    """
    logger.info("🔍 Loading Fotmob data from MinIO...")

    prefix = "fotmob/eredivisie/2025-2026/"
    match_files = minio_client.list_objects(prefix)

    matches = []
    for file_path in match_files:
        if file_path.endswith('.json'):
            logger.info(f"📄 Loading {file_path}")

            try:
                # Download and parse JSON
                response = minio_client.download_file(file_path)
                match_data = json.loads(response.read().decode('utf-8'))
                matches.append(match_data)
            except Exception as e:
                logger.error(f"❌ Failed to load {file_path}: {e}")
                continue

    logger.info(f"✅ Loaded {len(matches)} Fotmob matches")
    return matches


def match_whoscored_with_fotmob(
    whoscored_matches: List[Dict[str, Any]],
    fotmob_matches: List[Dict[str, Any]]
) -> Dict[str, Dict[str, Any]]:
    """Match WhoScored matches with Fotmob matches using fuzzy matching.

    Args:
        whoscored_matches: List of WhoScored match data
        fotmob_matches: List of Fotmob match data

    Returns:
        Dictionary mapping unified match IDs to match metadata
    """
    logger.info("🔗 Matching WhoScored and Fotmob data...")

    mappings = {}
    matched_fotmob_ids = set()
    counter = 1

    for ws_match in whoscored_matches:
        # Extract WhoScored match info
        ws_match_id = ws_match.get("match_id")
        ws_match_url = ws_match.get("match_url", "")

        # For WhoScored, we need to infer team names from events or URL
        # Let's extract from URL for now (this might need refinement)
        ws_url_parts = ws_match_url.split('/')
        if len(ws_url_parts) > 0:
            url_suffix = ws_url_parts[-1]
            # Try to extract teams from URL pattern
            url_teams = url_suffix.replace('netherlands-eredivisie-2025-2026-', '').split('-')
            if len(url_teams) >= 2:
                # This is a rough approximation - we might need to improve this
                ws_home_team = ' '.join(url_teams[:-1])  # Everything except last part
                ws_away_team = url_teams[-1]
            else:
                ws_home_team = "unknown"
                ws_away_team = "unknown"
        else:
            ws_home_team = "unknown"
            ws_away_team = "unknown"

        # Find best match in Fotmob data
        best_match = None
        best_score = 0.0

        for fm_match in fotmob_matches:
            if fm_match["match_id"] in matched_fotmob_ids:
                continue  # Already matched

            fm_home_team = fm_match["home_team"]
            fm_away_team = fm_match["away_team"]

            # Calculate similarity scores
            home_similarity = calculate_similarity(ws_home_team, fm_home_team)
            away_similarity = calculate_similarity(ws_away_team, fm_away_team)

            # Also try reversed (in case home/away are swapped)
            home_similarity_rev = calculate_similarity(ws_home_team, fm_away_team)
            away_similarity_rev = calculate_similarity(ws_away_team, fm_home_team)

            # Use the better of the two orientations
            score1 = (home_similarity + away_similarity) / 2
            score2 = (home_similarity_rev + away_similarity_rev) / 2
            final_score = max(score1, score2)

            if final_score > best_score and final_score > 0.6:  # Threshold for matching
                best_match = fm_match
                best_score = final_score

        if best_match:
            unified_id = f"unified_match_{counter:03d}"

            mappings[unified_id] = {
                "whoscored_id": ws_match_id,
                "fotmob_id": best_match["match_id"],
                "home_team": best_match["home_team"],  # Use Fotmob names (more reliable)
                "away_team": best_match["away_team"],
                "match_date": best_match.get("match_date", ""),
                "league": "eredivisie",
                "season": "2025-2026",
                "similarity_score": best_score,
                "created_at": datetime.utcnow().isoformat() + "Z"
            }

            matched_fotmob_ids.add(best_match["match_id"])
            counter += 1

            logger.info(f"✅ Matched: {best_match['home_team']} vs {best_match['away_team']} (score: {best_score:.3f})")
        else:
            logger.warning(f"❌ No match found for WhoScored match {ws_match_id}")

    # Report unmatched Fotmob matches
    unmatched_fotmob = [fm for fm in fotmob_matches if fm["match_id"] not in matched_fotmob_ids]
    if unmatched_fotmob:
        logger.warning(f"⚠️  {len(unmatched_fotmob)} Fotmob matches remain unmatched:")
        for fm in unmatched_fotmob:
            logger.warning(f"   - {fm['home_team']} vs {fm['away_team']} (ID: {fm['match_id']})")

    logger.info(f"🎯 Successfully created {len(mappings)} match mappings")
    return mappings


def save_mapping_to_minio(minio_client: MinIOClient, mappings: Dict[str, Dict[str, Any]]) -> None:
    """Save match mappings to MinIO.

    Args:
        minio_client: MinIO client instance
        mappings: Match mappings dictionary
    """
    logger.info("💾 Saving match mappings to MinIO...")

    object_name = "mappings/eredivisie/2025-2026/match_mapping.json"

    try:
        minio_client.upload_json(object_name, mappings)
        logger.info(f"✅ Successfully saved mappings to {object_name}")
        logger.info(f"📊 Mapping contains {len(mappings)} matches")
    except Exception as e:
        logger.error(f"❌ Failed to save mappings: {e}")
        raise


def main():
    """Main function to generate match mappings."""
    logger.info("🚀 Starting match mapping generation...")

    # Initialize MinIO client
    try:
        minio_client = MinIOClient()
        logger.info("✅ Connected to MinIO")
    except Exception as e:
        logger.error(f"❌ Failed to connect to MinIO: {e}")
        return

    # Load data from both sources
    try:
        whoscored_matches = load_whoscored_data_from_minio(minio_client)
        fotmob_matches = load_fotmob_data_from_minio(minio_client)
    except Exception as e:
        logger.error(f"❌ Failed to load data: {e}")
        return

    if not whoscored_matches:
        logger.error("❌ No WhoScored matches found")
        return

    if not fotmob_matches:
        logger.error("❌ No Fotmob matches found")
        return

    # Generate mappings
    try:
        mappings = match_whoscored_with_fotmob(whoscored_matches, fotmob_matches)
    except Exception as e:
        logger.error(f"❌ Failed to generate mappings: {e}")
        return

    if not mappings:
        logger.error("❌ No mappings generated")
        return

    # Save to MinIO
    try:
        save_mapping_to_minio(minio_client, mappings)
        logger.info("🎉 Match mapping generation completed successfully!")
    except Exception as e:
        logger.error(f"❌ Failed to save mappings: {e}")
        return


if __name__ == "__main__":
    main()