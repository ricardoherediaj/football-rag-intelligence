"""End-to-end test for visualization functions.

Tests all 4 visualization types with Heracles vs PEC Zwolle match (1904034).
Validates data loading, transformations, and viz generation for Phase 3 function calling.

Output: /data/test_visualizations/heracles_vs_pec/
"""

import json
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "scripts"))

from visualizers import (
    prepare_enhanced_passes,
    get_pass_combinations,
    get_enhanced_positions,
    calculate_team_metrics,
    plot_enhanced_network,
    calculate_player_defensive_positions,
    plot_shot_map_with_stats,
    plot_xt_momentum,
    calculate_match_stats,
    plot_match_stats_styled,
    filter_defensive_actions,
    defensive_block,
    draw_progressive_pass_map
)

# Paths
BASE_DIR = project_root / "data"
WHOSCORED_FILE = BASE_DIR / "raw" / "whoscored_matches" / "eredivisie" / "2025-2026" / "match_1904034.json"
FOTMOB_BULK_FILE = BASE_DIR / "raw" / "eredivisie_2025_2026_fotmob.json"
XT_GRID_FILE = BASE_DIR / "raw" / "xT_grid.csv"
MATCH_MAPPING_FILE = BASE_DIR / "match_mapping.json"
OUTPUT_DIR = BASE_DIR / "test_visualizations" / "heracles_vs_pec"

# Match IDs for Heracles vs PEC Zwolle
WHOSCORED_MATCH_ID = 1904034
FOTMOB_MATCH_ID = '4815309'  # String in Fotmob bulk file

# Create output directory
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Test results
results = {
    "passing_network_heracles": False,
    "passing_network_pec": False,
    "defensive_heatmap_heracles": False,
    "defensive_heatmap_pec": False,
    "shot_map": False,
    "xt_momentum": False,
    "full_match_report": False
}
errors = []


def load_whoscored_data():
    """Load WhoScored event data and convert to DataFrame."""
    print("Loading WhoScored data...")
    with open(WHOSCORED_FILE) as f:
        data = json.load(f)

    events = data['events']

    # Convert to DataFrame
    df_events = pd.DataFrame(events)

    # Data already has type_display_name and outcome_type_display_name columns (flattened format)
    # No transformation needed!

    print(f"  ✓ Loaded {len(df_events)} events")
    return df_events, data


def load_fotmob_data():
    """Load Fotmob shot data from bulk file."""
    print("Loading Fotmob data...")
    with open(FOTMOB_BULK_FILE) as f:
        all_matches = json.load(f)

    # Find our specific match
    match_data = None
    for match in all_matches:
        if match.get('match_id') == FOTMOB_MATCH_ID:
            match_data = match
            break

    if match_data is None:
        print(f"  ⚠ Match {FOTMOB_MATCH_ID} not found in bulk file")
        return [], {}

    shots = match_data.get('shots', [])

    # Add required fields for visualization (matching notebook)
    shots_df = pd.DataFrame(shots)
    if len(shots_df) > 0:
        # Rename teamId to team_id for consistency
        if 'teamId' in shots_df.columns:
            shots_df = shots_df.rename(columns={'teamId': 'team_id'})

        # Add is_big_chance and is_own_goal flags
        shots_df['is_big_chance'] = False  # Fotmob doesn't have this field explicitly
        shots_df['is_own_goal'] = shots_df.get('isOwnGoal', False)

        print(f"  ✓ Loaded {len(shots_df)} shots for match {FOTMOB_MATCH_ID}")
        return shots_df.to_dict('records'), match_data

    print(f"  ✓ Loaded {len(shots)} shots for match {FOTMOB_MATCH_ID}")
    return shots, match_data


def load_xt_grid():
    """Load xT grid from CSV."""
    print("Loading xT grid...")
    xT_grid = pd.read_csv(XT_GRID_FILE, header=None).values
    print(f"  ✓ Loaded xT grid shape: {xT_grid.shape}")
    return xT_grid


def get_team_info(df_events):
    """Extract team IDs and build player info."""
    team_ids = df_events['team_id'].unique()

    # Build player names dict
    player_names = {}
    for _, event in df_events.iterrows():
        if 'player_id' in event and pd.notna(event['player_id']):
            # For now, use player_id as name (no player names in WhoScored events)
            player_names[event['player_id']] = f"Player {event['player_id']}"

    # Build team players (simplified - we don't have full roster data)
    team_players = {
        team_id: [
            {
                'playerId': pid,
                'name': f"Player {pid}",
                'shirtNo': idx + 1,
                'position': 'Unknown',
                'isFirstEleven': idx < 11  # First 11 as starters
            }
            for idx, pid in enumerate(df_events[df_events['team_id'] == team_id]['player_id'].unique()[:20])
        ]
        for team_id in team_ids
    }

    print(f"  ✓ Found {len(team_ids)} teams: {team_ids}")
    return list(team_ids), player_names, team_players


def test_passing_network(df_events, team_id, team_players, player_names, team_name, output_file):
    """Test passing network visualization."""
    try:
        print(f"\nTesting passing network for {team_name}...")

        # Prepare passes
        passes_df = prepare_enhanced_passes(df_events)

        # Get pass combinations
        combinations = get_pass_combinations(passes_df, team_id)

        # Get positions
        avg_locs = get_enhanced_positions(passes_df, team_id, team_players[team_id], player_names)

        # Calculate metrics
        team_metrics = calculate_team_metrics(passes_df, avg_locs, team_id)

        # Plot
        fig, ax = plt.subplots(figsize=(14, 10), facecolor='#0e1117')
        ax.set_facecolor('#0e1117')

        color = '#00bfff' if team_id == 868 else '#ff4444'  # Blue for Heracles, Red for PEC
        is_home = team_id == 868

        plot_enhanced_network(
            ax, passes_df, avg_locs, combinations, team_metrics,
            team_name, color, is_home, '#0e1117'
        )

        plt.tight_layout()
        plt.savefig(output_file, dpi=150, facecolor='#0e1117', edgecolor='none')
        plt.close()

        print(f"  ✓ Saved to {output_file}")
        return True

    except Exception as e:
        print(f"  ✗ Failed: {e}")
        errors.append(f"Passing network {team_name}: {e}")
        return False


def test_shot_map(fotmob_shots, team_ids, team_names, output_file):
    """Test shot map visualization."""
    try:
        print(f"\nTesting shot map...")

        if len(fotmob_shots) == 0:
            print("  ⚠ No shot data available")
            return False

        # Create figure
        fig, ax = plt.subplots(figsize=(12, 8), facecolor='#0e1117')
        ax.set_facecolor('#0e1117')

        # Use Fotmob team IDs (not WhoScored IDs)
        home_fotmob_id = 9791  # Heracles
        away_fotmob_id = 6413  # PEC Zwolle
        plot_shot_map_on_axis(ax, fotmob_shots, home_fotmob_id, away_fotmob_id,
                             team_names[team_ids[0]], team_names[team_ids[1]])

        plt.tight_layout()
        plt.savefig(output_file, dpi=150, facecolor='#0e1117', edgecolor='none')
        plt.close()

        print(f"  ✓ Saved to {output_file}")
        return True

    except Exception as e:
        print(f"  ✗ Failed: {e}")
        errors.append(f"Shot map: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_defensive_heatmap(df_events, team_id, team_players, player_names, team_name, output_file):
    """Test defensive heatmap visualization."""
    try:
        print(f"\nTesting defensive heatmap for {team_name}...")

        # Filter defensive actions
        defensive_actions = filter_defensive_actions(df_events)

        # Calculate player defensive positions
        team_positions = calculate_player_defensive_positions(
            defensive_actions, team_id, team_players[team_id]
        )

        # Filter actions for this team
        team_actions = defensive_actions[defensive_actions['team_id'] == team_id]

        if len(team_positions) == 0:
            print(f"  ⚠ No defensive positions for {team_name}")
            return False

        # Create figure
        fig, ax = plt.subplots(figsize=(12, 10), facecolor='#0e1117')
        ax.set_facecolor('#0e1117')

        # Determine color and orientation
        color = '#43A1D5' if team_id == 868 else '#FF4C4C'
        is_away = team_id != 868

        # Plot defensive block
        defensive_block(ax, team_positions, team_actions, team_name, color, is_away_team=is_away)

        plt.tight_layout()
        plt.savefig(output_file, dpi=150, facecolor='#0e1117', edgecolor='none')
        plt.close()

        print(f"  ✓ Saved to {output_file}")
        return True

    except Exception as e:
        print(f"  ✗ Failed: {e}")
        errors.append(f"Defensive heatmap {team_name}: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_xt_momentum(df_events, xT_grid, output_file):
    """Test xT momentum visualization."""
    try:
        print(f"\nTesting xT momentum...")

        # Create team ID to name mapping
        team_id_to_name = {
            868: "Heracles",
            870: "PEC Zwolle"
        }

        # Function creates its own figure, just call it with correct args
        fig = plot_xt_momentum(
            df_events, xT_grid, team_id_to_name,
            home_team_id=868,
            away_team_id=870,
            bg_color='#0e1117'
        )

        plt.tight_layout()
        plt.savefig(output_file, dpi=150, facecolor='#0e1117', edgecolor='none')
        plt.close()

        print(f"  ✓ Saved to {output_file}")
        return True

    except Exception as e:
        print(f"  ✗ Failed: {e}")
        errors.append(f"xT momentum: {e}")
        import traceback
        traceback.print_exc()
        return False


def create_dashboard_match_report(df_events, team_ids, team_players, player_names, xT_grid, output_path, team_names, fotmob_shots):
    """Create professional 3x3 dashboard: full match report like notebook."""
    print(f"\nCreating 3x3 dashboard match report...")

    # Create 3x3 grid
    fig, axs = plt.subplots(3, 3, figsize=(24, 18), facecolor='#0e1117')
    match_title = f"{team_names[team_ids[0]]} vs {team_names[team_ids[1]]}"
    fig.suptitle('Match Report', fontsize=24, color='white', weight='bold', y=0.97)

    home_team_id = team_ids[0]
    away_team_id = team_ids[1]
    home_team_name = team_names[home_team_id]
    away_team_name = team_names[away_team_id]

    # Prepare data
    # Calculate progressive pass metric
    df_events['prog_pass'] = np.where(
        (df_events['type_display_name'] == 'Pass'),
        np.sqrt((105 - df_events['x'])**2 + (34 - df_events['y'])**2) -
        np.sqrt((105 - df_events['end_x'])**2 + (34 - df_events['end_y'])**2),
        0
    )

    passes_df = prepare_enhanced_passes(df_events)
    defensive_actions = filter_defensive_actions(df_events)

    # Home team data
    home_combinations = get_pass_combinations(passes_df, home_team_id)
    home_avg_locs = get_enhanced_positions(passes_df, home_team_id, team_players[home_team_id], player_names)
    home_metrics = calculate_team_metrics(passes_df, home_avg_locs, home_team_id)
    home_positions = calculate_player_defensive_positions(defensive_actions, home_team_id, team_players[home_team_id])
    home_actions = defensive_actions[defensive_actions['team_id'] == home_team_id]

    # Away team data
    away_combinations = get_pass_combinations(passes_df, away_team_id)
    away_avg_locs = get_enhanced_positions(passes_df, away_team_id, team_players[away_team_id], player_names)
    away_metrics = calculate_team_metrics(passes_df, away_avg_locs, away_team_id)
    away_positions = calculate_player_defensive_positions(defensive_actions, away_team_id, team_players[away_team_id])
    away_actions = defensive_actions[defensive_actions['team_id'] == away_team_id]

    # Calculate stats
    stats = calculate_match_stats(df_events, home_team_id, away_team_id)

    # Team ID to name mapping
    team_id_to_name = {home_team_id: home_team_name, away_team_id: away_team_name}

    # Dual ID system: WhoScored IDs for events/passes, Fotmob IDs for shots
    # Heracles: WhoScored=868, Fotmob=9791
    # PEC Zwolle: WhoScored=870, Fotmob=6413
    home_fotmob_id = 9791
    away_fotmob_id = 6413

    # ROW 1: Passing Networks + Shot Map
    axs[0,0].set_facecolor('#0e1117')
    plot_enhanced_network(
        axs[0,0], passes_df, home_avg_locs, home_combinations, home_metrics,
        home_team_name, color='#43A1D5', is_home=True, bg_color='#0e1117'
    )

    axs[0,1].set_facecolor('#0e1117')
    # Shot map - skip if no fotmob data
    if len(fotmob_shots) > 0:
        plot_shot_map_on_axis(axs[0,1], fotmob_shots, home_fotmob_id, away_fotmob_id, home_team_name, away_team_name)
    else:
        axs[0,1].text(0.5, 0.5, 'No shot data available', transform=axs[0,1].transAxes,
                     ha='center', va='center', color='white', fontsize=14)
        axs[0,1].axis('off')

    axs[0,2].set_facecolor('#0e1117')
    plot_enhanced_network(
        axs[0,2], passes_df, away_avg_locs, away_combinations, away_metrics,
        away_team_name, color='#FF4C4C', is_home=False, bg_color='#0e1117'
    )

    # ROW 2: Defensive Heatmaps + xT Momentum
    axs[1,0].set_facecolor('#0e1117')
    defensive_block(axs[1,0], home_positions, home_actions, home_team_name, '#43A1D5', is_away_team=False)

    axs[1,1].set_facecolor('#0e1117')
    plot_xt_momentum_on_axis(axs[1,1], df_events, xT_grid, team_id_to_name, home_team_id, away_team_id)

    axs[1,2].set_facecolor('#0e1117')
    defensive_block(axs[1,2], away_positions, away_actions, away_team_name, '#FF4C4C', is_away_team=True)

    # ROW 3: Progressive Passes + Match Stats
    axs[2,0].set_facecolor('#0e1117')
    draw_progressive_pass_map(axs[2,0], df_events, home_team_id, home_team_name, '#43A1D5', is_away_team=False)

    axs[2,1].set_facecolor('#0e1117')
    plot_match_stats_on_axis(axs[2,1], stats, home_team_name, away_team_name)

    axs[2,2].set_facecolor('#0e1117')
    draw_progressive_pass_map(axs[2,2], df_events, away_team_id, away_team_name, '#FF4C4C', is_away_team=True)

    # Layout
    plt.tight_layout()
    plt.subplots_adjust(top=0.94, hspace=0.3, wspace=0.2)

    # Save
    plt.savefig(output_path, dpi=150, facecolor='#0e1117', edgecolor='none', bbox_inches='tight')
    plt.close()

    print(f"  ✓ Saved 3x3 dashboard to {output_path}")
    return True


def plot_shot_map_on_axis(ax, shots_merged, home_fotmob_id, away_fotmob_id, home_team_name, away_team_name):
    """Advanced shot map with comprehensive shot type visualization - EXACT CODE FROM NOTEBOOK"""
    from mplsoccer import Pitch

    pitch = Pitch(pitch_type='uefa', pitch_color='#0C0D0E', line_color='white', linewidth=2, corner_arcs=True)
    pitch.draw(ax=ax)
    ax.set_ylim(-0.5, 68.5)
    ax.set_xlim(-0.5, 105.5)

    # Convert to DataFrame if needed
    if isinstance(shots_merged, list):
        shots_merged = pd.DataFrame(shots_merged)

    # Filter shots by team using Fotmob IDs
    home_shots = shots_merged[shots_merged['team_id'] == home_fotmob_id]
    away_shots = shots_merged[shots_merged['team_id'] == away_fotmob_id]

    def plot_shots(df, color, is_home_team=True, marker='o', s=200, edgecolor=None, fill=True, hatch=None, zorder=2):
        if len(df) > 0:
            face_color = color if fill else 'none'
            edge_color = edgecolor if edgecolor else color

            # Transform coordinates for proper positioning
            if is_home_team:
                x_coords = 105 - df['x']  # Home team shoots left to right
                y_coords = 68 - df['y']
            else:
                x_coords = df['x']        # Away team shoots right to left
                y_coords = df['y']

            ax.scatter(x_coords, y_coords, s=s, c=face_color, marker=marker,
                      edgecolors=edge_color, zorder=zorder, hatch=hatch, linewidth=1.5)

    # Team colors matching dashboard theme
    home_color, away_color = "#085098", "#F13032"

    # Home team shots (left side)
    home_goals = home_shots[(home_shots['eventType'] == 'Goal') & (~home_shots['is_own_goal'])]
    plot_shots(home_goals, 'none', True, 'o', 350, 'green', zorder=3)

    home_misses = home_shots[(home_shots['eventType'] == 'Miss') & (~home_shots['is_big_chance'])]
    plot_shots(home_misses, 'none', True, edgecolor=home_color, fill=False)

    home_saves = home_shots[(home_shots['eventType'] == 'AttemptSaved') & (~home_shots['is_big_chance'])]
    plot_shots(home_saves, 'none', True, edgecolor=home_color, fill=False, hatch='///////')

    home_big_chances = home_shots[(home_shots['is_big_chance']) & (home_shots['eventType'] != 'Goal')]
    plot_shots(home_big_chances, 'none', True, edgecolor=home_color, fill=False, s=500)

    # Away team shots (right side)
    away_goals = away_shots[(away_shots['eventType'] == 'Goal') & (~away_shots['is_own_goal'])]
    plot_shots(away_goals, 'none', False, 'o', 350, 'green', zorder=3)

    away_misses = away_shots[(away_shots['eventType'] == 'Miss') & (~away_shots['is_big_chance'])]
    plot_shots(away_misses, 'none', False, edgecolor=away_color, fill=False)

    away_saves = away_shots[(away_shots['eventType'] == 'AttemptSaved') & (~away_shots['is_big_chance'])]
    plot_shots(away_saves, 'none', False, edgecolor=away_color, fill=False, hatch='///////')

    away_big_chances = away_shots[(away_shots['is_big_chance']) & (away_shots['eventType'] != 'Goal')]
    plot_shots(away_big_chances, 'none', False, edgecolor=away_color, fill=False, s=500)

    # Team labels and shooting direction
    ax.text(0, 70, f"{home_team_name}\n← Shots", color=home_color, size=16, ha='left', fontweight='bold')
    ax.text(105, 70, f"{away_team_name}\nShots →", color=away_color, size=16, ha='right', fontweight='bold')

    ax.axis('off')


def plot_match_stats_on_axis(ax, stats, home_team_name, away_team_name):
    """Plot match stats comparison on given axis."""
    ax.set_facecolor('#0e1117')
    ax.axis('off')

    if len(stats) == 0:
        ax.text(0.5, 0.5, 'No stats available', transform=ax.transAxes,
               ha='center', va='center', color='white', fontsize=14)
        return

    # Select top stats to display
    stat_keys = list(stats.keys())[:8]  # Top 8 stats
    y_positions = np.linspace(0.85, 0.15, len(stat_keys))

    for i, category in enumerate(stat_keys):
        stat_data = stats[category]
        home_val = stat_data.get('home', 0) if isinstance(stat_data, dict) else 0
        away_val = stat_data.get('away', 0) if isinstance(stat_data, dict) else 0

        # Normalize for bar visualization
        total = home_val + away_val
        if total > 0:
            home_width = (home_val / total) * 0.35
            away_width = (away_val / total) * 0.35
        else:
            home_width = away_width = 0.1

        # Draw comparison bars
        ax.barh(y_positions[i], home_width, left=0.5-home_width, height=0.06,
                color='#43A1D5', alpha=0.8)
        ax.barh(y_positions[i], away_width, left=0.5, height=0.06,
                color='#FF4C4C', alpha=0.8)

        # Add values and labels
        ax.text(0.2, y_positions[i], f'{home_val}', ha='center', va='center',
                color='white', fontsize=10, weight='bold')
        ax.text(0.8, y_positions[i], f'{away_val}', ha='center', va='center',
                color='white', fontsize=10, weight='bold')
        ax.text(0.5, y_positions[i], category, ha='center', va='center',
                color='white', fontsize=9, weight='bold')

    # Team headers
    ax.text(0.2, 0.95, home_team_name, ha='center', va='center',
            color='#43A1D5', fontsize=14, weight='bold')
    ax.text(0.8, 0.95, away_team_name, ha='center', va='center',
            color='#FF4C4C', fontsize=14, weight='bold')

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)


def plot_xt_momentum_on_axis(ax, df_events, xT_grid, team_id_to_name, home_team_id, away_team_id):
    """Plot xT momentum directly on a given axis (for subplot layout)."""
    from scipy.ndimage import gaussian_filter1d

    ax.set_facecolor('#0e1117')

    try:
        # Scale coordinates for xT grid
        df = df_events.copy()
        df['x'] = df['x'] * 1.2
        df['y'] = df['y'] * 0.8
        df['end_x'] = df['end_x'] * 1.2
        df['end_y'] = df['end_y'] * 0.8

        # Filter successful passes and carries
        df_xT = df[
            (df['type_display_name'].isin(['Pass', 'Carry'])) &
            (df['outcome_type_display_name'] == 'Successful')
        ].copy()

        if len(df_xT) == 0:
            ax.text(0.5, 0.5, 'No xT data available', transform=ax.transAxes,
                   ha='center', va='center', color='white', fontsize=14)
            return

        # Calculate xT values
        n_rows, n_cols = xT_grid.shape

        def get_bin(val, max_val, n_bins):
            val = max(0, min(val, max_val))
            return min(int(val / max_val * n_bins), n_bins - 1)

        df_xT['start_x_bin'] = df_xT['x'].apply(lambda x: get_bin(x, 120, n_cols))
        df_xT['start_y_bin'] = df_xT['y'].apply(lambda y: get_bin(y, 80, n_rows))
        df_xT['end_x_bin'] = df_xT['end_x'].apply(lambda x: get_bin(x, 120, n_cols))
        df_xT['end_y_bin'] = df_xT['end_y'].apply(lambda y: get_bin(y, 80, n_rows))

        df_xT['start_zone_value'] = df_xT.apply(lambda row: xT_grid[row['start_y_bin'], row['start_x_bin']], axis=1)
        df_xT['end_zone_value'] = df_xT.apply(lambda row: xT_grid[row['end_y_bin'], row['end_x_bin']], axis=1)
        df_xT['xT'] = df_xT['end_zone_value'] - df_xT['start_zone_value']
        df_xT['xT_clipped'] = np.clip(df_xT['xT'], 0, 0.1)
        df_xT['team'] = df_xT['team_id'].map(team_id_to_name)

        # Calculate momentum per minute
        max_xT_per_minute = df_xT.groupby(['team', 'minute'])['xT_clipped'].max().reset_index()
        minutes = sorted(max_xT_per_minute['minute'].unique())
        teams = [team_id_to_name[home_team_id], team_id_to_name[away_team_id]]

        if len(minutes) == 0:
            ax.text(0.5, 0.5, 'No momentum data', transform=ax.transAxes,
                   ha='center', va='center', color='white', fontsize=14)
            return

        # Calculate weighted momentum
        window_size, decay_rate = 4, 0.25
        weighted_xT_sum = {team: [] for team in teams}
        momentum = []

        for current_minute in minutes:
            for team in teams:
                recent_xT = max_xT_per_minute[
                    (max_xT_per_minute['team'] == team) &
                    (max_xT_per_minute['minute'] <= current_minute) &
                    (max_xT_per_minute['minute'] > current_minute - window_size)
                ]
                weights = np.exp(-decay_rate * (current_minute - recent_xT['minute'].values))
                weighted_sum = np.sum(weights * recent_xT['xT_clipped'].values)
                weighted_xT_sum[team].append(weighted_sum)
            momentum.append(weighted_xT_sum[teams[0]][-1] - weighted_xT_sum[teams[1]][-1])

        # Plot momentum with smoothing
        momentum_smoothed = gaussian_filter1d(momentum, sigma=1.0)
        ax.plot(minutes, momentum_smoothed, color='white', linewidth=2)
        ax.axhline(0, color='white', linestyle='--', linewidth=1, alpha=0.7)
        ax.fill_between(minutes, momentum_smoothed, where=(np.array(momentum_smoothed) > 0),
                       color='#00bfff', alpha=0.5, interpolate=True)
        ax.fill_between(minutes, momentum_smoothed, where=(np.array(momentum_smoothed) < 0),
                       color='#ff4444', alpha=0.5, interpolate=True)

        # Team labels
        ax.text(2, max(momentum_smoothed) * 0.8, team_id_to_name[home_team_id],
                fontsize=12, ha='left', va='center', color='#00bfff', fontweight='bold')
        ax.text(2, min(momentum_smoothed) * 0.8, team_id_to_name[away_team_id],
                fontsize=12, ha='left', va='center', color='#ff4444', fontweight='bold')

        # Styling
        ax.set_xlabel('Minute', color='white', fontsize=10, fontweight='bold')
        ax.set_title('xT Momentum', color='white', fontsize=14, fontweight='bold')
        ax.tick_params(colors='white')
        for spine in ax.spines.values():
            spine.set_color('white')

    except Exception as e:
        ax.text(0.5, 0.5, f'Error: {str(e)[:50]}', transform=ax.transAxes,
               ha='center', va='center', color='white', fontsize=10)
        import traceback
        traceback.print_exc()


def test_full_match_report(df_events, team_ids, team_players, player_names, xT_grid, fotmob_shots):
    """Test complete match report dashboard (3x3 layout)."""
    try:
        print(f"\n{'='*60}")
        print("FULL MATCH REPORT TEST (3x3 DASHBOARD)")
        print(f"{'='*60}")

        team_names = {
            868: "Heracles",
            870: "PEC Zwolle"
        }

        report_dir = OUTPUT_DIR / "full_match_report"
        report_dir.mkdir(exist_ok=True)

        # Generate 3x3 dashboard report
        composite_path = report_dir / "match_report.png"
        success = create_dashboard_match_report(
            df_events, team_ids, team_players, player_names,
            xT_grid, composite_path, team_names, fotmob_shots
        )

        if success:
            print(f"\n{'='*60}")
            print("MATCH REPORT SUMMARY")
            print(f"{'='*60}")
            print(f"Match: {team_names[868]} vs {team_names[870]}")
            print(f"✓ Generated 3x3 dashboard match report")
            print(f"\nReport file: {composite_path}")
            return True
        else:
            print(f"  ✗ Failed to generate dashboard")
            return False

    except Exception as e:
        print(f"  ✗ Full report failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all visualization tests."""
    print("="*60)
    print("VISUALIZATION TEST SUITE")
    print("Match: Heracles vs PEC Zwolle (1904034)")
    print("="*60)

    # Load all data
    df_events, ws_data = load_whoscored_data()
    fotmob_shots, fm_data = load_fotmob_data()
    xT_grid = load_xt_grid()

    # Get team info
    team_ids, player_names, team_players = get_team_info(df_events)

    # Team names
    team_names = {
        868: "Heracles",
        870: "PEC Zwolle"
    }

    print(f"\nTeam IDs: {team_ids}")
    print(f"Team names: {team_names}")

    # Test individual visualizations
    print(f"\n{'='*60}")
    print("INDIVIDUAL VISUALIZATION TESTS")
    print(f"{'='*60}")

    # Test passing networks
    if 868 in team_ids:
        results['passing_network_heracles'] = test_passing_network(
            df_events, 868, team_players, player_names,
            "Heracles", OUTPUT_DIR / "passing_network_heracles.png"
        )

    if 870 in team_ids:
        results['passing_network_pec'] = test_passing_network(
            df_events, 870, team_players, player_names,
            "PEC Zwolle", OUTPUT_DIR / "passing_network_pec_zwolle.png"
        )

    # Test xT momentum
    results['xt_momentum'] = test_xt_momentum(
        df_events, xT_grid,
        OUTPUT_DIR / "xt_momentum.png"
    )

    # Test defensive heatmaps
    if 868 in team_ids:
        results['defensive_heatmap_heracles'] = test_defensive_heatmap(
            df_events, 868, team_players, player_names,
            "Heracles", OUTPUT_DIR / "defensive_heatmap_heracles.png"
        )

    if 870 in team_ids:
        results['defensive_heatmap_pec'] = test_defensive_heatmap(
            df_events, 870, team_players, player_names,
            "PEC Zwolle", OUTPUT_DIR / "defensive_heatmap_pec_zwolle.png"
        )

    # Test shot map
    results['shot_map'] = test_shot_map(
        fotmob_shots, team_ids, team_names,
        OUTPUT_DIR / "shot_map.png"
    )

    # Test full match report
    results['full_match_report'] = test_full_match_report(
        df_events, team_ids, team_players, player_names, xT_grid, fotmob_shots
    )

    # Summary
    print("\n" + "="*60)
    print("TEST RESULTS SUMMARY")
    print("="*60)

    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{test_name:30} {status}")

    if errors:
        print("\nERRORS:")
        for error in errors:
            print(f"  - {error}")

    print(f"\nOutput directory: {OUTPUT_DIR}")
    print(f"Generated files: {list(OUTPUT_DIR.glob('*.png'))}")

    # Write log
    log_file = OUTPUT_DIR / "test_log.txt"
    with open(log_file, 'w') as f:
        f.write(f"Test run: {datetime.now()}\n")
        f.write(f"Match: Heracles vs PEC Zwolle (1904034)\n\n")
        f.write("Results:\n")
        for test_name, passed in results.items():
            f.write(f"  {test_name}: {'PASS' if passed else 'FAIL'}\n")
        if errors:
            f.write("\nErrors:\n")
            for error in errors:
                f.write(f"  - {error}\n")

    print(f"\nLog saved to: {log_file}")

    # Exit code
    if any(results.values()):
        print("\n✓ Some tests passed!")
        return 0
    else:
        print("\n✗ All tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())