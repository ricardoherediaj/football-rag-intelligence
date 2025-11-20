"""
Select 10 diverse matches for evaluation dataset.
"""

import json
from pathlib import Path
import pandas as pd


def analyze_matches():
    """Analyze all matches and return diversity metrics."""
    whoscored_dir = Path("data/raw/whoscored_matches/eredivisie/2025-2026")
    fotmob_dir = Path("data/raw/fotmob_matches/eredivisie/2025-2026")

    matches = []

    for ws_file in sorted(whoscored_dir.glob("match_*.json")):
        with open(ws_file) as f:
            ws_data = json.load(f)

        if not ws_data.get('events'):
            continue

        events = ws_data['events']

        # Count goals
        goals = [e for e in events if e.get('is_goal')]
        home_team_id = events[0]['team_id']
        home_goals = len([g for g in goals if g['team_id'] == home_team_id])
        away_goals = len(goals) - home_goals

        # Find matching Fotmob file
        match_id = ws_data['match_id']
        fotmob_shots = 0
        for fm_file in fotmob_dir.glob("*.json"):
            with open(fm_file) as f:
                fm_data = json.load(f)
                fotmob_shots = len(fm_data.get('shots', []))
                break  # Simplified for now

        matches.append({
            'whoscored_id': match_id,
            'url': ws_data['match_url'],
            'score': f"{home_goals}-{away_goals}",
            'total_goals': home_goals + away_goals,
            'shots': len([e for e in events if e.get('is_shot')]),
            'events': len(events),
            'fotmob_shots': fotmob_shots
        })

    return pd.DataFrame(matches)


def select_top_10(df):
    """Select 10 diverse matches."""
    # Sort by different criteria to get variety
    selected = []

    # High-scoring (2 matches)
    selected.extend(df.nlargest(2, 'total_goals').to_dict('records'))

    # Low-scoring (2 matches)
    selected.extend(df.nsmallest(2, 'total_goals').to_dict('records'))

    # High shots (2 matches)
    remaining = df[~df['whoscored_id'].isin([m['whoscored_id'] for m in selected])]
    selected.extend(remaining.nlargest(2, 'shots').to_dict('records'))

    # Low shots (2 matches)
    remaining = df[~df['whoscored_id'].isin([m['whoscored_id'] for m in selected])]
    selected.extend(remaining.nsmallest(2, 'shots').to_dict('records'))

    # Random variety (2 matches from middle)
    remaining = df[~df['whoscored_id'].isin([m['whoscored_id'] for m in selected])]
    selected.extend(remaining.sample(2).to_dict('records'))

    return selected[:10]


if __name__ == "__main__":
    print("🔍 Analyzing matches...\n")

    df = analyze_matches()
    print(f"✅ Loaded {len(df)} matches\n")

    print(f"Goals: {df['total_goals'].min()}-{df['total_goals'].max()}")
    print(f"Shots: {df['shots'].min()}-{df['shots'].max()}\n")

    selected = select_top_10(df)

    print("🎯 Selected 10 matches:\n")
    for i, m in enumerate(selected, 1):
        print(f"{i}. {m['whoscored_id']}: {m['score']} ({m['shots']} shots)")

    Path("data/evaluation_matches.json").write_text(json.dumps(selected, indent=2))
    print(f"\n✅ Saved to data/evaluation_matches.json")