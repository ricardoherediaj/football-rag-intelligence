"""
Ingestion pipeline: MinIO → Narratives → ChromaDB

This module handles the extraction of match data from MinIO, generation of
narrative summaries, and ingestion into ChromaDB for RAG retrieval.
"""

import json
import logging
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path
from collections import defaultdict

from football_rag.storage.minio_client import MinIOClient
from football_rag.storage.vector_store import VectorStore

logger = logging.getLogger(__name__)


# =============================================================================
# DATA MODELS
# =============================================================================

class UnifiedMatch:
    """Represents a unified match with data from multiple sources."""

    def __init__(
        self,
        unified_id: str,
        whoscored_path: str,
        fotmob_path: str,
        home_team: str,
        away_team: str,
        match_date: str,
        league: str = "Eredivisie",
        season: str = "2025-2026"
    ):
        self.unified_id = unified_id
        self.whoscored_path = whoscored_path
        self.fotmob_path = fotmob_path
        self.home_team = home_team
        self.away_team = away_team
        self.match_date = match_date
        self.league = league
        self.season = season


# =============================================================================
# MATCH MAPPING LOADING
# =============================================================================

def load_match_mapping(minio_client: Optional[MinIOClient] = None) -> List[UnifiedMatch]:
    """
    Load match mapping from MinIO.

    For now, creates mapping by matching WhoScored and Fotmob files by index.
    In the future, this will load from a persisted mapping file.

    Args:
        minio_client: MinIO client instance (optional, creates new if None)

    Returns:
        List of UnifiedMatch objects
    """
    if minio_client is None:
        minio_client = MinIOClient()

    # List all files
    whoscored_files = sorted(minio_client.list_objects("whoscored/eredivisie/2025-2026/"))
    fotmob_files = sorted(minio_client.list_objects("fotmob/eredivisie/2025-2026/"))

    logger.info(f"Found {len(whoscored_files)} WhoScored files, {len(fotmob_files)} Fotmob files")

    # Simple mapping by index (assumes same order)
    matches = []
    for i, (ws_path, fm_path) in enumerate(zip(whoscored_files, fotmob_files)):
        # Extract match IDs from paths
        ws_match_id = ws_path.split('match_')[1].split('.json')[0] if 'match_' in ws_path else str(i)

        # Load a sample to get team names (we'll optimize this later)
        try:
            ws_data = json.loads(minio_client.download_file(ws_path).read())
            fm_data = json.loads(minio_client.download_file(fm_path).read())

            # Extract team names
            home_team = fm_data.get('home_team', 'Home')
            away_team = fm_data.get('away_team', 'Away')
            match_date = fm_data.get('match_date', '2025-09-01')

            match = UnifiedMatch(
                unified_id=f"unified_match_{i+1:03d}",
                whoscored_path=ws_path,
                fotmob_path=fm_path,
                home_team=home_team,
                away_team=away_team,
                match_date=match_date
            )
            matches.append(match)

        except Exception as e:
            logger.warning(f"Failed to load match {i}: {e}")
            continue

    logger.info(f"Loaded {len(matches)} unified matches")
    return matches


# =============================================================================
# NARRATIVE GENERATION
# =============================================================================

def generate_match_summary(whoscored_data: Dict, fotmob_data: Dict, match: UnifiedMatch) -> str:
    """
    Generate ~500 word match summary narrative.

    Args:
        whoscored_data: WhoScored match data with events
        fotmob_data: Fotmob match data with shots
        match: UnifiedMatch object with metadata

    Returns:
        Narrative text suitable for embedding
    """
    # Extract key statistics
    events = whoscored_data.get('events', [])
    shots = fotmob_data.get('shots', [])

    # Count events by type (simplified - WhoScored events don't have clear type in our data)
    total_events = len(events)
    total_shots = len(shots)

    # Count shots by team
    home_shots = [s for s in shots if s.get('teamId') == fotmob_data.get('home_team_id')]
    away_shots = [s for s in shots if s.get('teamId') == fotmob_data.get('away_team_id')]

    # Calculate xG
    home_xg = sum(s.get('expectedGoals', 0) for s in home_shots)
    away_xg = sum(s.get('expectedGoals', 0) for s in away_shots)

    # Count goals
    home_goals = sum(1 for s in home_shots if s.get('eventType') == 'Goal')
    away_goals = sum(1 for s in away_shots if s.get('eventType') == 'Goal')

    # Count shots on target
    home_on_target = sum(1 for s in home_shots if s.get('onTarget', False))
    away_on_target = sum(1 for s in away_shots if s.get('onTarget', False))

    # Build narrative
    narrative = f"""Match: {match.home_team} vs {match.away_team}
Date: {match.match_date}
League: {match.league}
Season: {match.season}
Final Score: {home_goals} - {away_goals}

Match Summary:
{match.home_team} {'won' if home_goals > away_goals else 'drew with' if home_goals == away_goals else 'lost to'} {match.away_team} in a {'dominant' if abs(home_goals - away_goals) > 2 else 'competitive' if home_goals == away_goals else 'close'} {match.league} encounter.

Shooting Statistics:
{match.home_team} created {len(home_shots)} shots with an expected goals (xG) of {home_xg:.2f}, while {match.away_team} managed {len(away_shots)} shots with {away_xg:.2f} xG.
The home side had {home_on_target} shots on target compared to {away_on_target} from the visitors.

Match Flow:
The match featured {total_events} recorded events, indicating a {'high-tempo' if total_events > 1000 else 'controlled' if total_events > 800 else 'tactical'} game.
{match.home_team}'s xG of {home_xg:.2f} {'exceeded' if home_xg > away_xg else 'matched' if abs(home_xg - away_xg) < 0.3 else 'fell short of'} {match.away_team}'s {away_xg:.2f},
{'suggesting they created better quality chances' if home_xg > away_xg else 'indicating relatively balanced opportunity creation' if abs(home_xg - away_xg) < 0.3 else 'showing the visitors had superior chances'}.

Key Takeaways:
- Total shots: {len(home_shots)} ({match.home_team}) vs {len(away_shots)} ({match.away_team})
- Expected Goals: {home_xg:.2f} vs {away_xg:.2f}
- Shots on target: {home_on_target} vs {away_on_target}
- Match events: {total_events}
"""

    return narrative.strip()


def generate_player_chunks(whoscored_data: Dict, match: UnifiedMatch) -> List[Tuple[str, Dict[str, Any]]]:
    """
    Generate per-player narrative chunks.

    Args:
        whoscored_data: WhoScored match data with events
        match: UnifiedMatch object with metadata

    Returns:
        List of (narrative, metadata) tuples, one per player
    """
    events = whoscored_data.get('events', [])

    # Aggregate events by player
    player_stats = defaultdict(lambda: {
        'events': [],
        'passes': 0,
        'shots': 0,
        'team_id': None
    })

    for event in events:
        player_id = event.get('player_id')
        if player_id:
            player_stats[player_id]['events'].append(event)
            player_stats[player_id]['team_id'] = event.get('team_id')

            # Simple event type detection (would be better with actual type field)
            if 'end_x' in event and 'end_y' in event:
                player_stats[player_id]['passes'] += 1

    # Generate chunks
    chunks = []
    for player_id, stats in player_stats.items():
        if len(stats['events']) < 5:  # Skip players with very few events
            continue

        # Determine team
        team_name = match.home_team  # Simplified - would need actual team mapping

        narrative = f"""Player Performance: Player {player_id}
Team: {team_name}
Match: {match.home_team} vs {match.away_team} ({match.match_date})

Activity Summary:
- Total actions: {len(stats['events'])}
- Passes: {stats['passes']}

This player was {'very active' if len(stats['events']) > 100 else 'moderately involved' if len(stats['events']) > 50 else 'present'} in the match,
recording {len(stats['events'])} total events including {stats['passes']} passes.
"""

        metadata = {
            "chunk_type": "player_events",
            "unified_match_id": match.unified_id,
            "player_id": str(player_id),
            "team_name": team_name,
            "home_team": match.home_team,
            "away_team": match.away_team,
            "league": match.league,
            "season": match.season,
            "match_date": match.match_date,
            "event_count": len(stats['events']),
            "raw_data_path": match.whoscored_path,
        }

        chunks.append((narrative.strip(), metadata))

    return chunks


def generate_shots_chunk(fotmob_data: Dict, match: UnifiedMatch) -> Tuple[str, Dict[str, Any]]:
    """
    Generate shots analysis narrative chunk.

    Args:
        fotmob_data: Fotmob match data with shots
        match: UnifiedMatch object with metadata

    Returns:
        (narrative, metadata) tuple
    """
    shots = fotmob_data.get('shots', [])
    home_team_id = fotmob_data.get('home_team_id')
    away_team_id = fotmob_data.get('away_team_id')

    # Separate shots by team
    home_shots = [s for s in shots if s.get('teamId') == home_team_id]
    away_shots = [s for s in shots if s.get('teamId') == away_team_id]

    # Calculate statistics
    home_xg = sum(s.get('expectedGoals', 0) for s in home_shots)
    away_xg = sum(s.get('expectedGoals', 0) for s in away_shots)

    home_on_target = sum(1 for s in home_shots if s.get('onTarget', False))
    away_on_target = sum(1 for s in away_shots if s.get('onTarget', False))

    home_goals = sum(1 for s in home_shots if s.get('eventType') == 'Goal')
    away_goals = sum(1 for s in away_shots if s.get('eventType') == 'Goal')

    # Build narrative
    narrative = f"""Shots Analysis: {match.home_team} vs {match.away_team}
Date: {match.match_date}

Shooting Statistics:
{match.home_team}:
- Total shots: {len(home_shots)}
- Shots on target: {home_on_target}
- Goals: {home_goals}
- Expected Goals (xG): {home_xg:.2f}

{match.away_team}:
- Total shots: {len(away_shots)}
- Shots on target: {away_on_target}
- Goals: {away_goals}
- Expected Goals (xG): {away_xg:.2f}

Analysis:
{match.home_team} generated {len(home_shots)} shots with a combined xG of {home_xg:.2f},
converting {home_goals} of these opportunities into goals ({'over-performing' if home_goals > home_xg else 'under-performing' if home_goals < home_xg - 0.5 else 'matching'} their xG).

{match.away_team} created {len(away_shots)} shots worth {away_xg:.2f} xG,
scoring {away_goals} goals ({'clinical finishing' if away_goals > away_xg else 'wasteful' if away_goals < away_xg - 0.5 else 'expected conversion'}).

Shot Quality:
The home side had {home_on_target}/{len(home_shots)} shots on target ({home_on_target/len(home_shots)*100 if home_shots else 0:.0f}% accuracy),
while the visitors managed {away_on_target}/{len(away_shots)} ({away_on_target/len(away_shots)*100 if away_shots else 0:.0f}% accuracy).
"""

    metadata = {
        "chunk_type": "shots_analysis",
        "unified_match_id": match.unified_id,
        "home_team": match.home_team,
        "away_team": match.away_team,
        "league": match.league,
        "season": match.season,
        "match_date": match.match_date,
        "total_shots": len(shots),
        "home_xg": float(home_xg),
        "away_xg": float(away_xg),
        "raw_data_path": match.whoscored_path,
        "fotmob_data_path": match.fotmob_path,
    }

    return narrative.strip(), metadata


# =============================================================================
# INGESTION ORCHESTRATION
# =============================================================================

def ingest_match(
    match: UnifiedMatch,
    minio_client: MinIOClient,
    vector_store: VectorStore,
    include_players: bool = False
) -> int:
    """
    Ingest a single match into ChromaDB.

    Args:
        match: UnifiedMatch object
        minio_client: MinIO client instance
        vector_store: VectorStore instance
        include_players: Whether to generate player chunks (can create many chunks)

    Returns:
        Number of chunks created
    """
    logger.info(f"Ingesting match: {match.home_team} vs {match.away_team}")

    # Fetch data from MinIO
    whoscored_response = minio_client.download_file(match.whoscored_path)
    fotmob_response = minio_client.download_file(match.fotmob_path)

    whoscored_data = json.loads(whoscored_response.read())
    fotmob_data = json.loads(fotmob_response.read())

    chunks_created = 0

    # 1. Generate and ingest match summary
    summary_text = generate_match_summary(whoscored_data, fotmob_data, match)
    summary_metadata = {
        "chunk_type": "match_summary",
        "unified_match_id": match.unified_id,
        "home_team": match.home_team,
        "away_team": match.away_team,
        "league": match.league,
        "season": match.season,
        "match_date": match.match_date,
        "raw_data_path": match.whoscored_path,
        "fotmob_data_path": match.fotmob_path,
    }

    vector_store.add_documents(
        documents=[summary_text],
        metadatas=[summary_metadata],
        ids=[f"match_summary_{match.unified_id}"]
    )
    chunks_created += 1
    logger.info(f"  ✓ Match summary chunk created")

    # 2. Generate and ingest shots analysis
    shots_text, shots_metadata = generate_shots_chunk(fotmob_data, match)
    vector_store.add_documents(
        documents=[shots_text],
        metadatas=[shots_metadata],
        ids=[f"shots_analysis_{match.unified_id}"]
    )
    chunks_created += 1
    logger.info(f"  ✓ Shots analysis chunk created")

    # 3. Optionally generate and ingest player chunks
    if include_players:
        player_chunks = generate_player_chunks(whoscored_data, match)
        if player_chunks:
            player_texts = [text for text, _ in player_chunks]
            player_metadatas = [metadata for _, metadata in player_chunks]
            player_ids = [f"player_events_{match.unified_id}_{meta['player_id']}" for meta in player_metadatas]

            vector_store.add_documents(
                documents=player_texts,
                metadatas=player_metadatas,
                ids=player_ids
            )
            chunks_created += len(player_chunks)
            logger.info(f"  ✓ {len(player_chunks)} player chunks created")

    logger.info(f"  ✓ Total chunks for match: {chunks_created}")
    return chunks_created


def ingest_all_matches(
    test_mode: bool = True,
    test_count: int = 5,
    include_players: bool = False,
    host: str = "localhost",
    port: int = 8000
) -> Dict[str, Any]:
    """
    Main ingestion pipeline: MinIO → Narratives → ChromaDB

    Args:
        test_mode: If True, only ingest first `test_count` matches
        test_count: Number of matches to ingest in test mode
        include_players: Whether to generate player chunks
        host: ChromaDB host
        port: ChromaDB port

    Returns:
        Statistics dict with counts
    """
    logger.info("=" * 80)
    logger.info("FOOTBALL RAG INGESTION PIPELINE")
    logger.info("=" * 80)

    # Initialize clients
    minio_client = MinIOClient()
    vector_store = VectorStore(host=host, port=port)

    # Load match mapping
    logger.info("\n1. Loading match mapping...")
    matches = load_match_mapping(minio_client)

    if test_mode:
        matches = matches[:test_count]
        logger.info(f"   TEST MODE: Processing {len(matches)} matches")
    else:
        logger.info(f"   FULL MODE: Processing {len(matches)} matches")

    # Ingest matches
    logger.info("\n2. Ingesting matches...")
    total_chunks = 0
    successful_matches = 0

    for i, match in enumerate(matches, 1):
        try:
            chunks = ingest_match(match, minio_client, vector_store, include_players)
            total_chunks += chunks
            successful_matches += 1
            logger.info(f"   [{i}/{len(matches)}] ✓ {match.home_team} vs {match.away_team}")
        except Exception as e:
            logger.error(f"   [{i}/{len(matches)}] ✗ Failed: {e}")
            continue

    # Get final stats
    stats = vector_store.get_stats()

    logger.info("\n" + "=" * 80)
    logger.info("INGESTION COMPLETE")
    logger.info("=" * 80)
    logger.info(f"Matches processed: {successful_matches}/{len(matches)}")
    logger.info(f"Chunks created: {total_chunks}")
    logger.info(f"Total documents in ChromaDB: {stats['document_count']}")
    logger.info(f"Collection: {stats['collection_name']}")
    logger.info("=" * 80)

    return {
        "matches_processed": successful_matches,
        "matches_total": len(matches),
        "chunks_created": total_chunks,
        "chromadb_total": stats['document_count'],
        "collection": stats['collection_name']
    }


# =============================================================================
# CLI ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Parse args
    test_mode = "--full" not in sys.argv
    include_players = "--players" in sys.argv

    # Run ingestion
    stats = ingest_all_matches(
        test_mode=test_mode,
        test_count=5,
        include_players=include_players
    )

    print("\n✅ Ingestion complete!")
    print(f"📊 Stats: {stats}")
