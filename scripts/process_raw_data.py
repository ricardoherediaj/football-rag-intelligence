"""
ETL Script: Raw Data -> Golden Dataset (Validated Match Profiles).
Output: data/processed/matches_gold.json
"""
import json
import sys
import logging
from pathlib import Path
from typing import Dict, Any, List
import pandas as pd
from tqdm import tqdm

# Add src to path to allow imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT / "src"))

from football_rag.analytics.metrics import calculate_all_metrics
from football_rag.data.models import MatchProfile, TeamMatchStats, MatchMetadata

# Configure Logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Paths
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
OUTPUT_FILE = DATA_DIR / "processed" / "matches_gold.json"

def load_json(path: Path) -> Any:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def resolve_team_ids(mapping: Dict) -> tuple[int, int]:
    """Dynamically resolve Home/Away Team IDs."""
    ws_map = mapping['ws_to_fotmob_team_mapping']
    fotmob_home_id = str(mapping['fotmob_home_team_id'])
    
    home_id = None
    for ws_id, fot_id in ws_map.items():
        if str(fot_id) == fotmob_home_id:
            home_id = int(ws_id)
            break
            
    if home_id is None:
        raise ValueError(f"Could not resolve Home ID for match {mapping.get('whoscored_id')}")

    ws_team_ids = [int(x) for x in mapping['whoscored_team_ids']]
    away_id = next(tid for tid in ws_team_ids if tid != home_id)
    
    return home_id, away_id

def map_metrics_to_model_dict(metrics: Dict, side: str, team_name: str, team_id: int) -> Dict:
    """Helper to transform flat metrics dict into TeamMatchStats schema."""
    prefix = f"{side}_"
    data = {k.replace(prefix, ''): v for k, v in metrics.items() if k.startswith(prefix)}
    
    rename_map = {
        "high_press": "high_press_events",
        "position": "median_position",
    }
    
    for old_key, new_key in rename_map.items():
        if old_key in data:
            data[new_key] = data.pop(old_key)
            
    data['team_name'] = team_name
    data['team_id'] = team_id
    
    return data

def process_matches():
    logger.info("Loading reference data...")
    mappings = load_json(DATA_DIR / "match_mapping.json")
    fotmob_bulk = load_json(RAW_DIR / "eredivisie_2025_2026_fotmob.json")
    
    processed_matches = []
    errors = []

    logger.info(f"🔄 Processing {len(mappings)} matches...")

    for whoscored_id, mapping in tqdm(mappings.items()):
        try:
            ws_path = RAW_DIR / f"whoscored_matches/eredivisie/2025-2026/match_{whoscored_id}.json"
            if not ws_path.exists():
                continue
                
            ws_data = load_json(ws_path)
            
            # 1. Resolve IDs
            home_team_id, away_team_id = resolve_team_ids(mapping)
            
            # 2. Prep Fotmob Data
            fotmob_match = next((m for m in fotmob_bulk if m['match_id'] == mapping['fotmob_id']), None)
            if not fotmob_match:
                continue

            fotmob_shots = fotmob_match.get('shots', [])
            fotmob_home_id = str(mapping['fotmob_home_team_id'])
            for shot in fotmob_shots:
                shot['is_home'] = (str(shot.get('teamId')) == fotmob_home_id)

            # 3. Calculate Metrics
            events_df = pd.DataFrame(ws_data['events'])
            raw_metrics = calculate_all_metrics(events_df, fotmob_shots, home_team_id, away_team_id)
            
            # --- FIX: CALCULATE SCORES FROM EVENTS ---
            # WhoScored raw JSONs often default 'home_score' to 0 if match not finished in their metadata
            # We calculate it ourselves from the 'is_goal' flag in events or fallback to metrics
            
            # Option A: Trust the metrics we just calculated (which count 'Goal' type events)
            # Note: metrics.py calculates 'home_shots' including goals, but maybe not score specifically
            # Let's count explicitly here for safety
            
            # Calculate from Fotmob shots (usually reliable for final score)
            home_goals = len([s for s in fotmob_shots if s['is_home'] and s['eventType'] == 'Goal'])
            away_goals = len([s for s in fotmob_shots if not s['is_home'] and s['eventType'] == 'Goal'])
            
            # -----------------------------------------

            # 4. Build Objects
            home_stats_data = map_metrics_to_model_dict(raw_metrics, "home", mapping['home_team'], home_team_id)
            # Inject actual goals into stats if needed
            home_stats_data['goals'] = home_goals
            
            away_stats_data = map_metrics_to_model_dict(raw_metrics, "away", mapping['away_team'], away_team_id)
            away_stats_data['goals'] = away_goals
            
            # 5. Create Golden Record
            match_profile = MatchProfile(
                metadata=MatchMetadata(
                    match_id=str(whoscored_id),
                    fotmob_id=mapping['fotmob_id'],
                    match_date=mapping['match_date']
                ),
                home_team=TeamMatchStats(**home_stats_data),
                away_team=TeamMatchStats(**away_stats_data),
                home_score=home_goals, # Use calculated score
                away_score=away_goals
            )
            
            processed_matches.append(json.loads(match_profile.model_dump_json()))

        except Exception as e:
            logger.error(f"Failed to process match {whoscored_id}: {e}")
            errors.append(whoscored_id)
            continue

    # Save
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(processed_matches, f, indent=2)
    
    logger.info(f"✅ Success! Processed {len(processed_matches)} matches.")
    logger.info(f"💾 Golden Dataset saved to: {OUTPUT_FILE}")

if __name__ == "__main__":
    process_matches()