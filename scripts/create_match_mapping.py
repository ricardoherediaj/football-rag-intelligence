"""Create complete match mapping between WhoScored and Fotmob for entire season.

This mapping is essential for:
1. Extracting combined metrics (WhoScored events + Fotmob shots)
2. RAG retrieval (matching queries to correct matches across both data sources)
3. Ensuring data consistency across the system
"""

import json
from pathlib import Path
from difflib import SequenceMatcher
import re

def normalize_team_name(name: str) -> str:
    """Normalize team name for fuzzy matching."""
    normalized = name.lower()
    # Remove common prefixes/suffixes
    normalized = normalized.replace('fc ', '').replace(' fc', '')
    normalized = normalized.replace('sc ', '').replace(' sc', '')
    # Remove special characters
    normalized = re.sub(r'[^\w\s]', '', normalized)
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    return normalized

def calculate_similarity(name1: str, name2: str) -> float:
    """Calculate similarity score between two team names."""
    norm1 = normalize_team_name(name1)
    norm2 = normalize_team_name(name2)
    return SequenceMatcher(None, norm1, norm2).ratio()

def extract_team_names_from_url(url: str) -> tuple:
    """Extract team names from WhoScored URL.

    URL format: .../netherlands-eredivisie-2025-2026-home-team-away-team
    """
    parts = url.split('/')[-1]
    parts = parts.replace('netherlands-eredivisie-2025-2026-', '')
    parts = parts.replace('netherlands-eredivisie-2024-2025-', '')

    # Split on hyphens and try to reconstruct team names
    tokens = parts.split('-')

    # Common multi-word teams
    multi_word_teams = {
        'pec zwolle': ['pec', 'zwolle'],
        'nec nijmegen': ['nec', 'nijmegen'],
        'psv eindhoven': ['psv', 'eindhoven'],
        'go ahead eagles': ['go', 'ahead', 'eagles'],
        'nac breda': ['nac', 'breda'],
        'sparta rotterdam': ['sparta', 'rotterdam'],
        'az alkmaar': ['az', 'alkmaar'],
        'fc volendam': ['volendam'],
        'fortuna sittard': ['fortuna', 'sittard'],
        'rkc waalwijk': ['rkc', 'waalwijk'],
        'sc heerenveen': ['heerenveen'],
        'fc utrecht': ['utrecht'],
        'fc groningen': ['groningen']
    }

    # Try to identify teams
    i = 0
    home_team_tokens = []

    while i < len(tokens):
        # Try to match multi-word teams
        matched = False
        for team_name, team_tokens in multi_word_teams.items():
            if tokens[i:i+len(team_tokens)] == team_tokens:
                home_team_tokens = team_tokens
                i += len(team_tokens)
                matched = True
                break

        if not matched:
            home_team_tokens.append(tokens[i])
            i += 1

        # Check if we might have found the home team
        home_candidate = ' '.join(home_team_tokens)
        if home_candidate in multi_word_teams or i >= len(tokens) // 2:
            break

    # Remaining tokens are away team
    away_team_tokens = tokens[i:]

    home_team = ' '.join(home_team_tokens).strip()
    away_team = ' '.join(away_team_tokens).strip()

    return home_team, away_team

def main():
    base_dir = Path(__file__).parent.parent

    print("🚀 Creating match mapping for entire season...")

    # Load Fotmob data (has all matches)
    fotmob_path = base_dir / "data" / "raw" / "eredivisie_2025_2026_fotmob.json"
    with open(fotmob_path) as f:
        fotmob_matches = json.load(f)

    print(f"📊 Loaded {len(fotmob_matches)} Fotmob matches")

    # Load all WhoScored matches
    ws_dir = base_dir / "data" / "raw" / "whoscored_matches" / "eredivisie" / "2025-2026"
    ws_files = sorted(ws_dir.glob("match_*.json"))

    print(f"📊 Found {len(ws_files)} WhoScored matches")

    mappings = {}
    matched_fotmob = set()

    for ws_file in ws_files:
        # Extract match ID from filename
        ws_id = ws_file.stem.replace('match_', '')

        # Load match data
        with open(ws_file) as f:
            ws_data = json.load(f)

        ws_url = ws_data.get('match_url', '')

        # Extract team IDs from events
        events = ws_data.get('events', [])
        team_ids = sorted(set(e['team_id'] for e in events if 'team_id' in e))

        if len(team_ids) != 2:
            print(f"⚠️  Skipping {ws_id} - couldn't find 2 teams")
            continue

        # Extract team names from URL
        url_home, url_away = extract_team_names_from_url(ws_url)

        # Find best match in Fotmob
        best_match = None
        best_score = 0.0

        for fm_match in fotmob_matches:
            if fm_match['match_id'] in matched_fotmob:
                continue  # Already matched

            fm_home = fm_match['home_team']
            fm_away = fm_match['away_team']

            # Calculate similarity in both orientations
            score_normal = (
                calculate_similarity(url_home, fm_home) +
                calculate_similarity(url_away, fm_away)
            ) / 2

            score_reversed = (
                calculate_similarity(url_home, fm_away) +
                calculate_similarity(url_away, fm_home)
            ) / 2

            score = max(score_normal, score_reversed)

            if score > best_score:
                best_match = fm_match
                best_score = score

        if best_match and best_score > 0.5:  # Threshold for matching
            mappings[ws_id] = {
                "whoscored_id": ws_id,
                "whoscored_url": ws_url,
                "whoscored_team_ids": team_ids,
                "fotmob_id": str(best_match['match_id']),
                "fotmob_home_team_id": best_match['home_team_id'],
                "fotmob_away_team_id": best_match['away_team_id'],
                "home_team": best_match['home_team'],
                "away_team": best_match['away_team'],
                "match_date": best_match['match_date'],
                "similarity_score": round(best_score, 3)
            }

            matched_fotmob.add(best_match['match_id'])

            status = "✅" if best_score > 0.8 else "⚠️ "
            print(f"{status} {ws_id}: {best_match['home_team']} vs {best_match['away_team']} (score: {best_score:.3f})")
        else:
            print(f"❌ {ws_id}: No match found (best: {best_score:.3f}) - URL teams: {url_home} vs {url_away}")

    # Report summary
    print(f"\n{'='*60}")
    print(f"✅ Successfully mapped: {len(mappings)}/{len(ws_files)} matches")
    print(f"📊 Fotmob matches used: {len(matched_fotmob)}/{len(fotmob_matches)}")

    # Save mappings
    output_path = base_dir / "data" / "match_mapping.json"
    with open(output_path, 'w') as f:
        json.dump(mappings, f, indent=2)

    print(f"💾 Saved mapping to: {output_path}")

    # Save inverse mapping (Fotmob ID -> WhoScored ID) for quick lookups
    inverse_mapping = {
        v['fotmob_id']: {
            'whoscored_id': k,
            'home_team': v['home_team'],
            'away_team': v['away_team']
        }
        for k, v in mappings.items()
    }

    inverse_path = base_dir / "data" / "fotmob_to_whoscored_mapping.json"
    with open(inverse_path, 'w') as f:
        json.dump(inverse_mapping, f, indent=2)

    print(f"💾 Saved inverse mapping to: {inverse_path}")
    print("\n🎉 Mapping complete!")

if __name__ == "__main__":
    main()
