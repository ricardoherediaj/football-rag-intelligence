import duckdb
from typing import List, Dict, Any

def vector_search(query_embedding: List[float], limit: int = 5) -> List[Dict[str, Any]]:
    """Perform a vector similarity search in the DuckDB Gold layer."""
    db = duckdb.connect("data/lakehouse.duckdb")
    
    try:
        # Load VSS extension
        db.execute("INSTALL vss; LOAD vss;")
        
        # Query using array_distance (smaller is better)
        # We cast the query_embedding to FLOAT[N] to match the index
        results = db.execute(f"""
            SELECT 
                player_id, 
                total_shots, 
                goals,
                array_distance(embedding, ?::FLOAT[3]) as distance
            FROM gold_shooting_stats
            ORDER BY distance ASC
            LIMIT ?
        """, [query_embedding, limit]).df()
        
        return results.to_dict(orient='records')
    finally:
        db.close()

if __name__ == "__main__":
    # Example usage with a dummy vector
    # Imagine this search is "Find players similar to one with 10 shots and 2 goals"
    dummy_query = [10.0, 2.0, 50.0] 
    print(f"Searching for players similar to: {dummy_query}")
    matches = vector_search(dummy_query)
    
    for i, match in enumerate(matches, 1):
        print(f"{i}. Player ID: {match['player_id']}, Distance: {match['distance']:.4f}")
