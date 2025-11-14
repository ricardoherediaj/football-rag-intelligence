"""Generate match selection list for evaluation dataset.

This script helps you select 10 diverse matches for the evaluation dataset by:
1. Loading all matches from ChromaDB
2. Categorizing them by characteristics (dominant wins, close matches, etc.)
3. Recommending 10 diverse matches

Run: uv run python scripts/generate_eval_match_selector.py
"""

import sys
sys.path.insert(0, 'src')

from football_rag.storage.vector_store import VectorStore

def categorize_match(metadata):
    """Categorize match based on stats."""
    home_goals = metadata.get('home_goals', 0)
    away_goals = metadata.get('away_goals', 0)
    home_xg = float(metadata.get('home_xg', 0))
    away_xg = float(metadata.get('away_xg', 0))

    goal_diff = abs(home_goals - away_goals)
    total_goals = home_goals + away_goals
    total_xg = home_xg + away_xg

    # Categorize
    if goal_diff >= 3:
        return 'dominant_win'
    elif goal_diff <= 1 and total_goals <= 2:
        return 'close_match'
    elif total_goals >= 5:
        return 'high_scoring'
    elif total_xg < 2.0:
        return 'defensive'
    else:
        return 'balanced'

def main():
    # Connect to ChromaDB
    print("Connecting to ChromaDB...")
    store = VectorStore(
        collection_name="football_matches_eredivisie_2025",
        persist_directory="data/chroma"
    )

    # Get all documents
    results = store.collection.get()

    print(f"\n📊 Total matches in database: {len(results['ids'])}")
    print("=" * 140)

    # Categorize matches
    categories = {
        'dominant_win': [],
        'close_match': [],
        'high_scoring': [],
        'defensive': [],
        'balanced': []
    }

    for i in range(len(results['ids'])):
        meta = results['metadatas'][i]
        category = categorize_match(meta)

        match_info = {
            'index': i + 1,
            'id': meta.get('match_id', '?'),
            'home': meta.get('home_team', '?'),
            'away': meta.get('away_team', '?'),
            'score': f"{meta.get('home_goals', '?')}-{meta.get('away_goals', '?')}",
            'xg': f"{meta.get('home_xg', '?'):.2f}-{meta.get('away_xg', '?'):.2f}",
            'poss': meta.get('home_possession', '?'),
            'vert': meta.get('home_verticality', '?'),
            'metadata': meta
        }

        categories[category].append(match_info)

    # Print categorized matches
    print("\n🏆 DOMINANT WINS (goal difference ≥ 3):")
    print("-" * 140)
    for match in categories['dominant_win'][:5]:
        print(f"{match['index']:2}. {match['home']:20} {match['score']:5} {match['away']:20} | xG: {match['xg']:10} | Poss: {match['poss']:5}% | Vert: {match['vert']:5}%")

    print("\n⚖️  CLOSE MATCHES (goal diff ≤ 1, total goals ≤ 2):")
    print("-" * 140)
    for match in categories['close_match'][:5]:
        print(f"{match['index']:2}. {match['home']:20} {match['score']:5} {match['away']:20} | xG: {match['xg']:10} | Poss: {match['poss']:5}% | Vert: {match['vert']:5}%")

    print("\n🎯 HIGH SCORING (total goals ≥ 5):")
    print("-" * 140)
    for match in categories['high_scoring'][:3]:
        print(f"{match['index']:2}. {match['home']:20} {match['score']:5} {match['away']:20} | xG: {match['xg']:10} | Poss: {match['poss']:5}% | Vert: {match['vert']:5}%")

    print("\n🛡️  DEFENSIVE (total xG < 2.0):")
    print("-" * 140)
    for match in categories['defensive'][:3]:
        print(f"{match['index']:2}. {match['home']:20} {match['score']:5} {match['away']:20} | xG: {match['xg']:10} | Poss: {match['poss']:5}% | Vert: {match['vert']:5}%")

    print("\n" + "=" * 140)
    print("\n✅ RECOMMENDED 10 MATCHES FOR EVALUATION DATASET:\n")

    # Select diverse set
    selected = []
    selected.extend(categories['dominant_win'][:3])
    selected.extend(categories['close_match'][:3])
    selected.extend(categories['high_scoring'][:2])
    selected.extend(categories['defensive'][:2])

    for i, match in enumerate(selected[:10], 1):
        print(f"{i:2}. {match['home']:20} {match['score']:5} {match['away']:20} | xG: {match['xg']:10}")

    print("\n" + "=" * 140)
    print("\n📝 NEXT STEP: Copy these 10 match IDs and create eval dataset JSON")
    print("\nFor each match, you'll need to write:")
    print("  - Query: 'Analyze [team]'s passing network and build-up play'")
    print("  - Expected GOOD response (specific, tactical, uses numbers)")
    print("  - Expected BAD response (generic, no tactics)")
    print("\nSee: /docs/EVALUATION_CRITERIA.md for examples")

if __name__ == "__main__":
    main()
