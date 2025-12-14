"""Ingestion Script: Golden Data -> ChromaDB.
Reads pre-calculated, validated metrics from matches_gold.json and indexes them.
Includes defensive sanitization to prevent NoneType errors.
"""
import json
import shutil
import logging
from pathlib import Path
import chromadb
from tqdm import tqdm

# Configure Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def sanitize_metadata(metadata: dict) -> dict:
    """
    Firewall: ChromaDB crashes on None values. 
    This function recursively finds None and replaces it with safe defaults.
    """
    clean = {}
    for k, v in metadata.items():
        if v is None:
            # Context-aware defaults for numeric fields
            if any(x in k for x in ['score', 'shots', 'xg', 'passes', 'ppda', 'intensity', 'line', 'possession', 'tilt', 'compactness']):
                clean[k] = 0
            else:
                clean[k] = "N/A"
        else:
            clean[k] = v
    return clean

def main():
    logger.info("🔄 Starting ChromaDB ingestion (Golden Data Layer)...")
    
    # 1. Setup DB Paths
    project_root = Path(__file__).parent.parent
    chroma_path = project_root / "data" / "chroma"
    gold_file = project_root / "data" / "processed" / "matches_gold.json"

    # 2. Check Input
    if not gold_file.exists():
        logger.error(f"❌ Golden dataset not found at {gold_file}")
        return

    # 3. Wipe & Re-Initialize DB
    if chroma_path.exists():
        logger.info(f"🗑️  Wiping existing ChromaDB at {chroma_path}")
        shutil.rmtree(chroma_path)
    
    client = chromadb.PersistentClient(path=str(chroma_path))
    collection = client.create_collection(
        name="eredivisie_matches_2025",
        metadata={"description": "Eredivisie 2025-2026 season matches (Processed)"}
    )
    
    # 4. Load Data
    logger.info("📖 Loading golden dataset...")
    with open(gold_file) as f:
        matches = json.load(f)
        
    logger.info(f"📊 Found {len(matches)} validated matches to index.")

    # 5. Prepare Batches
    documents = []
    metadatas = []
    ids = []
    
    for match in tqdm(matches, desc="Indexing matches"):
        # Correctly extract ID from metadata block (Fix 1)
        meta_block = match.get('metadata', {})
        match_id = meta_block.get('match_id')
        match_date = meta_block.get('match_date', 'N/A')
        season = meta_block.get('season', '2025-2026')

        if not match_id:
             # Fallback if metadata is missing ID (shouldn't happen with valid gold data)
             match_id = match.get('match_id', 'unknown')

        m_home = match['home_team']
        m_away = match['away_team']
        
        # --- Chunk 1: Match Summary ---
        summary_text = (
            f"{m_home['team_name']} vs {m_away['team_name']} "
            f"({match['home_score']}-{match['away_score']}) on {match_date[:10]}. "
            f"Possession: {m_home['possession']}% vs {m_away['possession']}%. "
            f"xG: {m_home['xg']} vs {m_away['xg']}."
        )
        
        summary_meta = {
            "match_id": match_id,
            "chunk_type": "summary",
            "home_team": m_home['team_name'],
            "away_team": m_away['team_name'],
            "home_score": match['home_score'],
            "away_score": match['away_score'],
            "match_date": match_date,
            "season": season
        }
        
        ids.append(f"{match_id}_summary")
        documents.append(summary_text)
        metadatas.append(sanitize_metadata(summary_meta)) # Fix 2: Sanitize
        
        # --- Chunk 2: Tactical Metrics ---
        flat_metrics = {
            "match_id": match_id,
            "chunk_type": "tactical_metrics",
            "home_team": m_home['team_name'],
            "away_team": m_away['team_name'],
            "home_score": match['home_score'],
            "away_score": match['away_score'],
            
            # --- HOME METRICS ---
            "home_progressive_passes": m_home['progressive_passes'],
            "home_total_passes": m_home['total_passes'],
            "home_pass_accuracy": m_home['pass_accuracy'],
            "home_verticality": m_home['verticality'],
            "home_ppda": m_home['ppda'],
            "home_high_press": m_home['high_press_events'],
            "home_shots": m_home['shots'],
            "home_shots_on_target": m_home['shots_on_target'],
            "home_xg": m_home['xg'],
            "home_position": m_home['median_position'],
            "home_defense_line": m_home['defense_line'],
            "home_compactness": m_home['compactness'],
            "home_possession": m_home['possession'],
            "home_field_tilt": m_home['field_tilt'],
            
            # --- AWAY METRICS ---
            "away_progressive_passes": m_away['progressive_passes'],
            "away_total_passes": m_away['total_passes'],
            "away_pass_accuracy": m_away['pass_accuracy'],
            "away_verticality": m_away['verticality'],
            "away_ppda": m_away['ppda'],
            "away_high_press": m_away['high_press_events'],
            "away_shots": m_away['shots'],
            "away_shots_on_target": m_away['shots_on_target'],
            "away_xg": m_away['xg'],
            "away_position": m_away['median_position'],
            "away_defense_line": m_away['defense_line'],
            "away_compactness": m_away['compactness'],
            "away_possession": m_away['possession'],
            "away_field_tilt": m_away['field_tilt']
        }
        
        metrics_text = (
            f"Tactical metrics for {m_home['team_name']} vs {m_away['team_name']}: "
            f"Home Shots {m_home['shots']}, Away Shots {m_away['shots']}. "
            f"Home xG {m_home['xg']}, Away xG {m_away['xg']}."
        )
        
        ids.append(f"{match_id}_tactical_metrics")
        documents.append(metrics_text)
        metadatas.append(sanitize_metadata(flat_metrics)) # Fix 2: Sanitize

    # 6. Upsert in Batches
    logger.info(f"💾 Indexing {len(documents)} chunks...")
    batch_size = 100
    for i in range(0, len(documents), batch_size):
        end = i + batch_size
        collection.add(
            documents=documents[i:end],
            metadatas=metadatas[i:end],
            ids=ids[i:end]
        )
    
    logger.info(f"✅ Ingestion complete. Collection: {collection.count()} docs.")

if __name__ == "__main__":
    main()