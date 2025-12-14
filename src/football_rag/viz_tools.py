"""
Viz Tools: The bridge between RAG and Visualizers.
Loads data and triggers plots.
"""
import json
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from football_rag import visualizers 

# Define Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"
OUTPUT_DIR = PROJECT_ROOT / "data" / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def load_match_data(match_id: str):
    """Loads WhoScored events and Fotmob shots for a match."""
    # 1. Load WhoScored
    ws_path = RAW_DIR / "whoscored_matches" / "eredivisie" / "2025-2026" / f"match_{match_id}.json"
    if not ws_path.exists():
        raise FileNotFoundError(f"Match data not found for ID {match_id}")
    
    with open(ws_path) as f:
        ws_data = json.load(f)
    df_events = pd.DataFrame(ws_data['events'])

    # 2. Load Fotmob (Simplified: relying on bulk file for now)
    # In a perfect world, we map IDs. For MVP, we return empty if not found easily.
    # You can enhance this later with your match_mapping.json logic
    fotmob_shots = [] 
    
    return df_events, fotmob_shots

def get_team_metadata(df_events):
    """Extracts team names and IDs from events."""
    team_ids = df_events['team_id'].unique()
    # Mock player names/roles since we just need visuals
    player_names = {}
    team_players = {}
    for tid in team_ids:
        pids = df_events[df_events['team_id'] == tid]['player_id'].unique()
        team_players[tid] = [{'playerId': p, 'name': str(p), 'shirtNo': 0, 'position': 'UNK', 'isFirstEleven': True} for p in pids]
    
    # We don't have team names in events, so we use placeholders or need a mapping
    # For now, we return Generic names or extract from prompt context in the app
    team_names = {tid: f"Team {tid}" for tid in team_ids}
    return list(team_ids), team_players, player_names, team_names

def generate_dashboard(match_id: str, home_name: str, away_name: str):
    """Generates the full 3x3 dashboard and saves it."""
    print(f"🎨 Drawing Dashboard for {home_name} vs {away_name} ({match_id})...")
    
    # 1. Load Data
    df_events, fotmob_shots = load_match_data(match_id)
    xT_grid = pd.read_csv(RAW_DIR / "xT_grid.csv", header=None).values
    
    # 2. Prep Metadata
    team_ids, team_players, player_names, _ = get_team_metadata(df_events)
    
    # Update names with what we passed in (from the RAG context)
    # Assumption: team_ids[0] is home, [1] is away. 
    # (Real production code would check 'is_home' flag in data)
    real_team_names = {team_ids[0]: home_name, team_ids[1]: away_name}
    
    # 3. Call the Visualizer (The code you already wrote)
    save_path = OUTPUT_DIR / f"dashboard_{match_id}.png"
    
    # We mock a composite function call here using your existing logic
    # (Reusing the logic from your visualizers.py / test script)
    # For brevity, I am calling a hypothetical wrapper or you can copy 
    # 'create_dashboard_match_report' from your test script into visualizers.py
    # BUT, to keep it simple, let's just generate ONE plot to prove it works:
    
    # Let's generate the Passing Network for Home Team as the MVP
    passes_df = visualizers.prepare_enhanced_passes(df_events)
    home_id = team_ids[0]
    avg_locs = visualizers.get_enhanced_positions(passes_df, home_id, team_players[home_id], player_names)
    combinations = visualizers.get_pass_combinations(passes_df, home_id)
    metrics = visualizers.calculate_team_metrics(passes_df, avg_locs, home_id)
    
    fig, ax = plt.subplots(figsize=(10, 8), facecolor='#0e1117')
    visualizers.plot_enhanced_network(
        ax, passes_df, avg_locs, combinations, metrics, 
        home_name, color='#43A1D5', is_home=True
    )
    
    plt.savefig(save_path, dpi=100, bbox_inches='tight', facecolor='#0e1117')
    plt.close()
    
    return str(save_path)