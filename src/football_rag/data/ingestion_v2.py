"""Minimal chunk ingestion - v2 (150 words, tactical insights from visualizers.py).

Standalone version - includes UnifiedMatch and match mapping logic directly.
"""

import json
import logging
from typing import Dict, Any, List
from datetime import datetime
from pathlib import Path

import pandas as pd
from pydantic import BaseModel, Field

from football_rag.storage.minio_client import MinIOClient
from football_rag.storage.vector_store import VectorStore
from football_rag.data.tactical_rules import interpret_verticality, interpret_shot_quality, interpret_possession

logger = logging.getLogger(__name__)


class UnifiedMatch(BaseModel):
    """Unified match linking WhoScored and Fotmob data."""
    unified_id: str = Field(..., min_length=1)
    whoscored_path: str = Field(..., min_length=1)
    fotmob_path: str = Field(..., min_length=1)
    home_team: str = Field(..., min_length=1)
    away_team: str = Field(..., min_length=1)
    match_date: str
    league: str = "Eredivisie"
    season: str = "2025-2026"


def load_whoscored_team_ids() -> Dict[str, int]:
    """Load WhoScored team IDs from CSV."""
    csv_path = Path(__file__).parent.parent.parent.parent / "data" / "raw" / "eredivisie_whoscored_team_ids.csv"
    df = pd.read_csv(csv_path)
    team_map = dict(zip(df['team_name'], df['whoscored_id']))
    logger.info(f"Loaded {len(team_map)} WhoScored team IDs")
    return team_map


def load_match_mapping(minio_client: MinIOClient) -> List[UnifiedMatch]:
    """Load match mapping from MinIO mapping file."""
    mapping_obj = minio_client.download_file("mappings/eredivisie/2025-2026/match_mapping.json")
    mapping_data = json.loads(mapping_obj.read())

    matches = []
    for unified_id, match_info in mapping_data.items():
        ws_path = f"whoscored/eredivisie/2025-2026/match_{match_info['whoscored_id']}.json"
        fm_path = f"fotmob/eredivisie/2025-2026/match_{match_info['fotmob_id']}.json"

        match = UnifiedMatch(
            unified_id=unified_id,
            whoscored_path=ws_path,
            fotmob_path=fm_path,
            home_team=match_info['home_team'],
            away_team=match_info['away_team'],
            match_date=match_info['match_date']
        )
        matches.append(match)

    logger.info(f"Loaded {len(matches)} unified matches from mapping file")
    return matches


def calculate_stats(events: list, shots: list, ws_team_id: int, fm_team_id: int) -> Dict[str, Any]:
    """Calculate core stats from events and shots.

    Args:
        events: WhoScored events list
        shots: Fotmob shots list
        ws_team_id: WhoScored team ID (for filtering events)
        fm_team_id: Fotmob team ID (for filtering shots)

    Returns:
        Dictionary with tactical stats
    """
    import numpy as np

    # Filter WhoScored events by WhoScored team_id
    team_events = [e for e in events if e.get('team_id') == ws_team_id]

    # Passes for verticality (team-specific)
    passes = [e for e in team_events
              if e.get('type_display_name') == 'Pass'
              and e.get('outcome_type_display_name') == 'Successful']

    if passes:
        angles = [abs(np.degrees(np.arctan2(
            p.get('end_y', 0) - p.get('y', 0),
            p.get('end_x', 0) - p.get('x', 0)
        ))) for p in passes]
        verticality = round((1 - np.median(angles)/90) * 100, 2)
    else:
        verticality = 0.0

    # Filter Fotmob shots by Fotmob team_id (convert to int for comparison)
    fm_team_id_int = int(fm_team_id) if isinstance(fm_team_id, str) else fm_team_id
    team_shots = [s for s in shots if s.get('teamId') == fm_team_id_int]

    # Calculate xG (handle NaN values)
    xg_values = [s.get('expectedGoals', 0) for s in team_shots]
    xg_values_clean = [x for x in xg_values if not (isinstance(x, float) and np.isnan(x))]
    xg = sum(xg_values_clean) if xg_values_clean else 0.0
    xg_per_shot = xg / len(team_shots) if team_shots else 0.0
    goals = sum(1 for s in team_shots if s.get('eventType') == 'Goal')

    # Possession (% of team events)
    possession = round(len(team_events) / len(events) * 100, 1) if events else 0.0

    return {
        'verticality': verticality,
        'xg': round(xg, 2),
        'xg_per_shot': round(xg_per_shot, 3),
        'shots': len(team_shots),
        'goals': goals,
        'possession': possession
    }


def generate_chunk(home_stats: Dict, away_stats: Dict, match: Dict) -> str:
    """Generate 150-word tactical chunk."""

    style = interpret_verticality(home_stats['verticality'])
    quality = interpret_shot_quality(home_stats['xg_per_shot'])
    poss = interpret_possession(home_stats['possession'])

    result = 'won' if home_stats['goals'] > away_stats['goals'] else 'drew' if home_stats['goals'] == away_stats['goals'] else 'lost'

    return f"""Match: {match['home_team']} vs {match['away_team']} ({home_stats['goals']}-{away_stats['goals']})
League: {match['league']} | Date: {match['match_date']}

Tactical Summary:
{match['home_team']} {style}, {quality}.
They {poss} ({home_stats['possession']:.1f}%).

Key Stats:
- Possession: {home_stats['possession']:.1f}% - {away_stats['possession']:.1f}%
- Verticality: {home_stats['verticality']:.1f}% (higher = more direct)
- Shots: {home_stats['shots']} - {away_stats['shots']}
- xG: {home_stats['xg']} - {away_stats['xg']}
- xG/Shot: {home_stats['xg_per_shot']:.3f} vs {away_stats['xg_per_shot']:.3f}

Result: {match['home_team']} {result}.

Visualizations: passing_network, shot_map, match_stats
"""


def ingest_match(ws_path: str, fm_path: str, match: Dict, ws_team_ids: Dict[str, int],
                 minio: MinIOClient, store: VectorStore) -> str:
    """Ingest single match with minimal chunk.

    Args:
        ws_path: Path to WhoScored data in MinIO
        fm_path: Path to Fotmob data in MinIO
        match: Match info dict with team names
        ws_team_ids: Mapping of team name -> WhoScored team ID
        minio: MinIO client
        store: Vector store
    """
    # Load data
    ws_obj = minio.download_file(ws_path)
    fm_obj = minio.download_file(fm_path)
    ws_data = json.loads(ws_obj.read())
    fm_data = json.loads(fm_obj.read())

    # Lookup WhoScored team IDs by team name
    ws_home_id = ws_team_ids[match['home_team']]
    ws_away_id = ws_team_ids[match['away_team']]

    # Calculate stats (WhoScored IDs for events, Fotmob IDs for shots)
    home_stats = calculate_stats(
        ws_data['events'], fm_data['shots'],
        ws_team_id=ws_home_id,
        fm_team_id=fm_data['home_team_id']
    )
    away_stats = calculate_stats(
        ws_data['events'], fm_data['shots'],
        ws_team_id=ws_away_id,
        fm_team_id=fm_data['away_team_id']
    )

    # Generate chunk
    chunk = generate_chunk(home_stats, away_stats, match)

    # Metadata
    metadata = {
        "chunk_type": "match_summary",
        "unified_match_id": match['unified_match_id'],
        "home_team": match['home_team'],
        "away_team": match['away_team'],
        "league": match['league'],
        "season": match['season'],
        "match_date": match['match_date'],
        "raw_data_path": ws_path,
        "fotmob_data_path": fm_path,
        "ingestion_timestamp": datetime.now().isoformat(),
        "verticality": home_stats['verticality'],
        "xg_home": home_stats['xg'],
        "xg_away": away_stats['xg']
    }

    # Store
    chunk_id = f"match_summary_{match['unified_match_id']}"
    store.add_documents([chunk], [metadata], [chunk_id])

    return chunk


def ingest_all(test_mode: bool = True, count: int = 5):
    """Main ingestion pipeline v2."""
    from football_rag.config.settings import settings

    logger.info("INGESTION V2: Minimal chunks with tactical insights")

    # Load WhoScored team IDs
    ws_team_ids = load_whoscored_team_ids()

    # Initialize clients
    minio = MinIOClient(
        endpoint=settings.database.minio_endpoint,
        access_key=settings.database.minio_access_key,
        secret_key=settings.database.minio_secret_key
    )

    store = VectorStore(
        host=settings.database.chroma_host,
        port=settings.database.chroma_port
    )

    # Load matches
    matches = load_match_mapping(minio)
    if test_mode:
        matches = matches[:count]

    logger.info(f"Processing {len(matches)} matches...")

    # Ingest each match
    for i, m in enumerate(matches, 1):
        match_info = {
            'unified_match_id': m.unified_id,
            'home_team': m.home_team,
            'away_team': m.away_team,
            'league': m.league,
            'season': m.season,
            'match_date': m.match_date
        }

        ingest_match(m.whoscored_path, m.fotmob_path, match_info, ws_team_ids, minio, store)
        logger.info(f"[{i}/{len(matches)}] ✓ {m.home_team} vs {m.away_team}")

    stats = store.get_stats()
    logger.info(f"✅ Complete: {stats['document_count']} docs in ChromaDB")

    return {'processed': len(matches), 'total_docs': stats['document_count']}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = ingest_all(test_mode=True, count=5)
    print(f"✅ {result}")
