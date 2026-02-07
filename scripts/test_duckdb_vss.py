import duckdb
import numpy as np

def test_vss():
    db = duckdb.connect(":memory:")
    
    try:
        print("🔍 Checking VSS extension...")
        db.execute("INSTALL vss; LOAD vss;")
        print("✅ VSS extension loaded successfully")
        
        # Create a table with a vector column
        db.execute("CREATE TABLE test_vectors (id INTEGER, vec FLOAT[3])")
        
        # Insert some dummy vectors
        vectors = [
            (1, [1.0, 0.0, 0.0]),
            (2, [0.0, 1.0, 0.0]),
            (3, [0.0, 0.0, 1.0]),
            (4, [0.7, 0.7, 0.0]) # Mix of 1 and 2
        ]
        
        for vid, vec in vectors:
            db.execute("INSERT INTO test_vectors VALUES (?, ?)", [vid, vec])
        
        print(f"✅ Inserted {len(vectors)} test vectors")
        
        # Create HNSW index
        print("🏗️ Creating HNSW index...")
        db.execute("CREATE INDEX test_idx ON test_vectors USING HNSW (vec)")
        print("✅ HNSW index created")
        
        # Perform a vector search
        print("🎯 Testing vector search...")
        # Search for something close to [1, 0, 0]
        query_vec = [0.9, 0.1, 0.0]
        res = db.execute("""
            SELECT id, array_distance(vec, ?::FLOAT[3]) as dist
            FROM test_vectors
            ORDER BY dist ASC
            LIMIT 2
        """, [query_vec]).fetchall()
        
        print("Search results (id, distance):")
        for row in res:
            print(f"  ID: {row[0]}, Distance: {row[1]:.4f}")
            
    except Exception as e:
        print(f"❌ Verification failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    test_vss()
