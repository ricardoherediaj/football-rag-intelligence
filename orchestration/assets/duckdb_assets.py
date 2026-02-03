from dagster import asset, AssetExecutionContext, Config
import duckdb
import pandas as pd
import json
from pathlib import Path
from typing import List

class DuckDBConfig(Config):
    database_path: str = "data/lakehouse.duckdb"

@asset(compute_kind="python")
def raw_matches_bronze(context: AssetExecutionContext, config: DuckDBConfig):
    """Load raw JSON matches from local storage into DuckDB Bronze layer."""
    db = duckdb.connect(config.database_path)
    
    # Ensure raw table exists
    db.execute("CREATE TABLE IF NOT EXISTS bronze_matches (match_id VARCHAR, source VARCHAR, data JSON)")
    
    raw_dir_ws = Path("data/raw/whoscored_matches")
    raw_dir_fm = Path("data/raw/fotmob_matches")
    
    count = 0
    
    # Ingest WhoScored
    if raw_dir_ws.exists():
        for json_file in raw_dir_ws.rglob("*.json"):
            with open(json_file, 'r') as f:
                data = json.load(f)
                match_id = str(data.get('match_id', 'unknown'))
                db.execute("INSERT INTO bronze_matches SELECT ?, 'whoscored', ?", [match_id, json.dumps(data)])
                count += 1

    # Ingest Fotmob
    if raw_dir_fm.exists():
        for json_file in raw_dir_fm.rglob("*.json"):
            with open(json_file, 'r') as f:
                data = json.load(f)
                match_id = str(data.get('match_info', {}).get('match_id', 'unknown'))
                db.execute("INSERT INTO bronze_matches SELECT ?, 'fotmob', ?", [match_id, json.dumps(data)])
                count += 1
                
    db.close()
    context.add_output_metadata({"matches_loaded": count})
    return count

@asset(deps=[raw_matches_bronze], compute_kind="duckdb")
def events_silver(config: DuckDBConfig):
    """Clean and normalize events from Bronze to Silver layer."""
    db = duckdb.connect(config.database_path)
    
    db.execute("""
        CREATE OR REPLACE TABLE silver_events AS 
        SELECT 
            match_id,
            UNNEST(data->'$.events')->>'$.id' as event_id,
            UNNEST(data->'$.events')->>'$.type_display_name' as event_type,
            UNNEST(data->'$.events')->>'$.player_id' as player_id,
            UNNEST(data->'$.events')->>'$.team_id' as team_id,
            CAST(UNNEST(data->'$.events')->>'$.x' AS DOUBLE) as x,
            CAST(UNNEST(data->'$.events')->>'$.y' AS DOUBLE) as y,
            CAST(UNNEST(data->'$.events')->>'$.minute' AS INTEGER) as minute,
            CAST(UNNEST(data->'$.events')->>'$.is_shot' AS BOOLEAN) as is_shot,
            CAST(UNNEST(data->'$.events')->>'$.is_goal' AS BOOLEAN) as is_goal
        FROM bronze_matches
        WHERE source = 'whoscored'
    """)
    
    db.close()

@asset(deps=[raw_matches_bronze], compute_kind="duckdb")
def silver_fotmob(config: DuckDBConfig):
    """Clean and normalize Fotmob shots."""
    db = duckdb.connect(config.database_path)
    
    # Fotmob usually stores shots with x,y (0-100 or specific coords), 
    # we might need to normalize, but for now we extract raw.
    db.execute("""
        CREATE OR REPLACE TABLE silver_fotmob_shots AS 
        SELECT 
            match_id,
            UNNEST(data->'$.shots')->>'$.id' as shot_id,
            UNNEST(data->'$.shots')->>'$.eventType' as event_type,
            UNNEST(data->'$.shots')->>'$.playerId' as player_id,
            UNNEST(data->'$.shots')->>'$.teamId' as team_id,
            CAST(UNNEST(data->'$.shots')->>'$.x' AS DOUBLE) as x,
            CAST(UNNEST(data->'$.shots')->>'$.y' AS DOUBLE) as y,
            CAST(UNNEST(data->'$.shots')->>'$.min' AS INTEGER) as minute,
            TRUE as is_shot,
            CASE WHEN UNNEST(data->'$.shots')->>'$.eventType' = 'Goal' THEN TRUE ELSE FALSE END as is_goal
        FROM bronze_matches
        WHERE source = 'fotmob'
    """)
    
    db.close()

@asset(deps=[events_silver], compute_kind="duckdb")
def shooting_gold_vss(config: DuckDBConfig):
    """Create Gold layer for shooting stats and initialize VSS vector index."""
    db = duckdb.connect(config.database_path)
    
    # Load VSS extension
    db.execute("INSTALL vss; LOAD vss;")
    
    # Create summarized gold table
    db.execute("""
        CREATE OR REPLACE TABLE gold_shooting_stats AS 
        SELECT 
            player_id,
            COUNT(*) as total_shots,
            SUM(CASE WHEN is_goal THEN 1 ELSE 0 END) as goals,
            AVG(x) as avg_shot_distance_x -- Simplified proxy
        FROM silver_events
        WHERE is_shot = True
        GROUP BY player_id
    """)
    
    # Initialize Vector Index (Placeholder for embeddings)
    # In a real scenario, we'd use a UDF to generate embeddings first
    # For now, we create a dummy vector column to demonstrate the VSS capability
    db.execute("ALTER TABLE gold_shooting_stats ADD COLUMN embedding FLOAT[3]")
    db.execute("UPDATE gold_shooting_stats SET embedding = [total_shots, goals, avg_shot_distance_x]")
    
    # Create HNSW Index
    db.execute("CREATE INDEX shots_vss_idx ON gold_shooting_stats USING HNSW (embedding)")
    
    db.close()
