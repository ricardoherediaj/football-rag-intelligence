"""Diagnostic script to inspect ChromaDB schema and keys."""
import chromadb
from pathlib import Path
import pprint

def inspect_db():
    # 1. Connect to the DB
    # We use the path relative to the project root
    db_path = Path("data/chroma").resolve()
    print(f"📂 connecting to: {db_path}")
    
    if not db_path.exists():
        print("❌ Error: DB path does not exist. Did you run rebuild_chromadb.py?")
        return

    client = chromadb.PersistentClient(path=str(db_path))
    
    # 2. Get the collection
    try:
        collection = client.get_collection("eredivisie_matches_2025")
        print(f"✅ Found collection: {collection.name}")
        print(f"📊 Total documents: {collection.count()}")
    except Exception as e:
        print(f"❌ Error finding collection: {e}")
        return

    # 3. Fetch a specific "Tactical Metrics" chunk
    # We query for Heracles to keep it relevant to your test case
    print("\n🔎 Searching for 'Heracles' metrics chunk...")
    
    results = collection.query(
        query_texts=["Heracles"],
        n_results=1,
        where={"chunk_type": "tactical_metrics"}
    )

    if not results['ids'] or not results['ids'][0]:
        print("❌ No tactical_metrics chunk found for Heracles.")
        return

    # 4. Print the keys found
    metadata = results['metadatas'][0][0]
    
    print("\n🔑 KEYS FOUND IN 'tactical_metrics' CHUNK:")
    print("-" * 50)
    
    # Sort keys for easier reading
    sorted_keys = sorted(metadata.keys())
    for key in sorted_keys:
        # Print key and type of value (to check if it's float/int/str)
        value = metadata[key]
        print(f"{key:<30} | {type(value).__name__:<10} | Example: {str(value)[:20]}")
    
    print("-" * 50)

    # 5. Check for the missing suspects specifically
    print("\n🕵️‍♂️ DETECTIVE CHECK:")
    missing_suspects = ['home_median_pos', 'home_def_line', 'home_verticality']
    for suspect in missing_suspects:
        if suspect in metadata:
            print(f"✅ {suspect} EXISTS")
        else:
            # Try to find close matches
            matches = [k for k in sorted_keys if suspect.split('_')[1] in k] # heuristic match
            print(f"❌ {suspect} MISSING. Did you mean: {matches}?")

if __name__ == "__main__":
    inspect_db()