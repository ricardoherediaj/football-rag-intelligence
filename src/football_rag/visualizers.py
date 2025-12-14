"""Core visualization functions for football analytics dashboard.

This module contains the main plotting functions extracted from match_dashboard_template.ipynb.
Functions are organized by visualization type: passing networks, defensive actions, shot maps,
xT momentum, and match statistics.

Author: Football Analytics Team
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patheffects as patheffects
from matplotlib.colors import LinearSegmentedColormap, to_rgba
from mplsoccer import Pitch
from scipy.ndimage import gaussian_filter1d


# =============================================================================
# PASSING NETWORK FUNCTIONS
# =============================================================================

def prepare_enhanced_passes(df_events: pd.DataFrame) -> pd.DataFrame:
    """Prepare pass data with enhanced metrics.
    
    Args:
        df_events: DataFrame containing match events
        
    Returns:
        DataFrame with enhanced pass data including angles and receivers
    """
    # Filter successful passes
    passes = df_events[
        (df_events['type_display_name'] == 'Pass') & 
        (df_events['outcome_type_display_name'] == 'Successful')
    ].copy()
    
    # Calculate pass angles
    passes['pass_angle'] = np.degrees(np.arctan2(
        passes['end_y'] - passes['y'], 
        passes['end_x'] - passes['x']
    ))
    passes['pass_angle_abs'] = np.abs(passes['pass_angle'])
    
    # Add receiver
    passes['receiver'] = passes['player_id'].shift(-1)
    
    return passes


def get_pass_combinations(passes_df: pd.DataFrame, team_id: int) -> pd.DataFrame:
    """Calculate bidirectional pass combinations between players.
    
    Args:
        passes_df: DataFrame containing pass data
        team_id: Team identifier
        
    Returns:
        DataFrame with pass combinations and counts
    """
    team_passes = passes_df[passes_df['team_id'] == team_id].copy()
    
    # Create bidirectional pairs
    team_passes['pos_min'] = team_passes[['player_id', 'receiver']].min(axis=1)
    team_passes['pos_max'] = team_passes[['player_id', 'receiver']].max(axis=1)
    
    # Count passes between pairs
    pass_combinations = team_passes.groupby(['pos_min', 'pos_max']).size().reset_index(name='pass_count')
    
    return pass_combinations


def get_enhanced_positions(passes_df: pd.DataFrame, team_id: int, 
                          team_players: list, player_names_dict: dict) -> pd.DataFrame:
    """Get average player positions with enhanced player information.
    
    Args:
        passes_df: DataFrame containing pass data
        team_id: Team identifier
        team_players: List of team player dictionaries
        player_names_dict: Dictionary mapping player IDs to names
        
    Returns:
        DataFrame with average positions and player info
    """
    team_passes = passes_df[passes_df['team_id'] == team_id]
    
    # Calculate average positions
    avg_locs = team_passes.groupby('player_id').agg({
        'x': 'median', 
        'y': 'median', 
        'player_id': 'count'
    })
    avg_locs.columns = ['x_avg', 'y_avg', 'pass_count']
    
    # Create player info
    player_info = {}
    for player in team_players:
        player_id = player['playerId']
        player_name = player_names_dict.get(str(player_id), player['name'])
        player_info[player_id] = {
            'name': player_name,
            'shirtNo': player['shirtNo'],
            'position': player['position'],
            'isFirstEleven': player.get('isFirstEleven', False)
        }
    
    # Join with player info
    player_df = pd.DataFrame.from_dict(player_info, orient='index')
    avg_locs = avg_locs.join(player_df)
    
    return avg_locs


def calculate_team_metrics(passes_df: pd.DataFrame, avg_locs: pd.DataFrame, team_id: int) -> dict:
    """Calculate tactical metrics for a team.
    
    Args:
        passes_df: DataFrame containing pass data
        avg_locs: DataFrame with average player positions
        team_id: Team identifier
        
    Returns:
        Dictionary containing tactical metrics
    """
    team_passes = passes_df[passes_df['team_id'] == team_id]
    
    # Verticality
    valid_passes = team_passes[
        (team_passes['pass_angle_abs'] >= 0) & 
        (team_passes['pass_angle_abs'] <= 90)
    ]
    median_angle = valid_passes['pass_angle_abs'].median()
    verticality = round((1 - median_angle/90) * 100, 2)
    
    # Defense line (center backs)
    center_backs = avg_locs[avg_locs['position'] == 'DC']
    defense_line = center_backs['x_avg'].median() if len(center_backs) > 0 else 30
    
    # Forward line (forwards and attacking mids)
    attackers = avg_locs[avg_locs['position'].isin(['FW', 'AMC'])]
    forward_line = attackers['x_avg'].mean() if len(attackers) > 0 else 90
    
    # Team median position
    team_median = avg_locs['x_avg'].median()
    
    return {
        'verticality': verticality,
        'defense_line': defense_line,
        'forward_line': forward_line,
        'team_median': team_median
    }


def plot_enhanced_network(ax, passes_df: pd.DataFrame, avg_locs: pd.DataFrame, 
                         pass_combinations: pd.DataFrame, team_metrics: dict,
                         team_name: str, color: str = 'blue', is_home: bool = True, 
                         bg_color: str = '#0C0D0E'):
    """Plot enhanced passing network with The Athletic styling.
    
    Args:
        ax: Matplotlib axis object
        passes_df: DataFrame containing pass data
        avg_locs: DataFrame with average player positions
        pass_combinations: DataFrame with pass combinations
        team_metrics: Dictionary with tactical metrics
        team_name: Name of the team
        color: Team color for visualization
        is_home: Whether this is the home team
        bg_color: Background color
    """
    # Setup pitch with dark theme
    pitch = Pitch(pitch_type='statsbomb', line_color='white', pitch_color=bg_color, linewidth=1)
    pitch.draw(ax=ax)
    ax.set_xlim(0, 120)
    ax.set_ylim(0, 80)
    ax.set_facecolor(bg_color)
    
    # Transform coordinates for away team
    if not is_home:
        avg_locs = avg_locs.copy()
        avg_locs['x_avg'] = 120 - avg_locs['x_avg']
        avg_locs['y_avg'] = 80 - avg_locs['y_avg']
    
    # Add player info to combinations
    combinations = pass_combinations.merge(
        avg_locs[['x_avg', 'y_avg', 'name']], 
        left_on='pos_min', right_index=True
    ).merge(
        avg_locs[['x_avg', 'y_avg', 'name']], 
        left_on='pos_max', right_index=True, 
        suffixes=['', '_end']
    )
    
    # Pass lines with enhanced styling
    max_passes = combinations['pass_count'].max()
    combinations['line_width'] = (combinations['pass_count'] / max_passes) * 15
    combinations['alpha'] = 0.3 + (combinations['pass_count'] / max_passes) * 0.6
    
    # Draw pass lines
    for _, row in combinations.iterrows():
        pitch.lines(row['x_avg'], row['y_avg'], row['x_avg_end'], row['y_avg_end'],
                   lw=row['line_width'], color=color, alpha=row['alpha'], ax=ax, zorder=1)
    
    # Tactical lines
    defense_line = team_metrics['defense_line']
    forward_line = team_metrics['forward_line']
    team_median = team_metrics['team_median']
    
    if not is_home:
        defense_line = 120 - defense_line
        forward_line = 120 - forward_line
        team_median = 120 - team_median
    
    # Draw tactical lines
    ax.axvline(x=defense_line, color='lightgray', linestyle='dotted', alpha=0.6, linewidth=2, zorder=2)
    ax.axvline(x=forward_line, color='lightgray', linestyle='dotted', alpha=0.6, linewidth=2, zorder=2)
    ax.axvline(x=team_median, color='lightgray', linestyle='--', alpha=0.8, linewidth=2, zorder=2)
    
    # Highlight middle zone
    min_line = min(defense_line, forward_line)
    max_line = max(defense_line, forward_line)
    ymid = [0, 0, 80, 80]
    xmid = [min_line, max_line, max_line, min_line]
    ax.fill(xmid, ymid, color, alpha=0.1, zorder=0)
    
    # Player nodes
    for player_id, row in avg_locs.iterrows():
        marker = 'o' if row['isFirstEleven'] else 's'
        pitch.scatter(row['x_avg'], row['y_avg'], s=1200, marker=marker,
                     color='white', edgecolors=color, linewidth=3, ax=ax, zorder=3)
        
        # Jersey numbers
        ax.text(row['x_avg'], row['y_avg'], str(row['shirtNo']),
                ha='center', va='center', fontsize=14, color=color, weight='bold',
                path_effects=[patheffects.withStroke(linewidth=3, foreground='white')],
                zorder=4, clip_on=False)
    
    # Text positioning based on team
    if is_home:
        ax.text(115, 75, "○ = starter\n□ = substitute", 
                fontsize=11, ha='right', va='top', color='white',
                bbox=dict(boxstyle="round,pad=0.3", facecolor=bg_color, edgecolor='white', alpha=0.8))
        ax.text(10, -8, f"Verticality: {team_metrics['verticality']}%", 
                fontsize=12, ha='left', color='white', weight='bold')
        ax.text(70, -8, f"Median: {team_metrics['team_median']:.1f}m", 
                fontsize=12, ha='left', color='white', weight='bold')
    else:
        ax.text(5, 75, "○ = starter\n□ = substitute", 
                fontsize=11, ha='left', va='top', color='white',
                bbox=dict(boxstyle="round,pad=0.3", facecolor=bg_color, edgecolor='white', alpha=0.8))
        ax.text(110, -8, f"Verticality: {team_metrics['verticality']}%", 
                fontsize=12, ha='right', color='white', weight='bold')
        ax.text(50, -8, f"Median: {team_metrics['team_median']:.1f}m", 
                fontsize=12, ha='right', color='white', weight='bold')
    
    ax.set_title(f"{team_name} - Passing Network", fontsize=14, color='white')


# =============================================================================
# DEFENSIVE ACTIONS FUNCTIONS
# =============================================================================

def calculate_player_defensive_positions(defensive_actions: pd.DataFrame, 
                                       team_id: int, 
                                       team_players: list) -> dict:
    """Calculate average defensive positions and action counts for each player.
    
    Args:
        defensive_actions: DataFrame containing defensive action events
        team_id: Team identifier
        team_players: List of team player dictionaries
        
    Returns:
        Dictionary with player defensive statistics
    """
    # Filter actions for this team
    team_actions = defensive_actions[defensive_actions['team_id'] == team_id]
    
    if len(team_actions) == 0:
        return {}
    
    # Create player info lookup
    def create_player_info(player):
        return {
            'name': player['name'],
            'position': player['position'],
            'shirt_no': player['shirtNo'],
            'is_starter': player.get('isFirstEleven', False)
        }
    
    player_info = {p['playerId']: create_player_info(p) for p in team_players}
    
    # Calculate player statistics
    player_stats = (
        team_actions.groupby('player_id')
        .agg({
            'x_sb': 'median',
            'y_sb': 'median',
            'id': 'count'
        })
        .round(2)
        .rename(columns={'id': 'action_count'})
    )
    
    # Combine with player info
    positions = {}
    for player_id, stats in player_stats.iterrows():
        if player_id in player_info:
            positions[player_id] = {
                'x': stats['x_sb'],
                'y': stats['y_sb'],
                'action_count': stats['action_count'],
                'name': player_info[player_id]['name'],
                'position': player_info[player_id]['position'],
                'shirt_no': player_info[player_id]['shirt_no'],
                'is_starter': player_info[player_id]['is_starter']
            }
    
    return positions


# =============================================================================
# SHOT MAP FUNCTIONS
# =============================================================================

def plot_shot_map_with_stats(shots_merged: pd.DataFrame, home_stats: list, away_stats: list, 
                           home_id: int, away_id: int, home_name: str, away_name: str, 
                           home_color: str, away_color: str, bg_color: str = '#0C0D0E'):
    """Plot shot map with stats bar using match data.
    
    Args:
        shots_merged: DataFrame containing shot data
        home_stats: List of home team statistics
        away_stats: List of away team statistics
        home_id: Home team identifier
        away_id: Away team identifier
        home_name: Home team name
        away_name: Away team name
        home_color: Home team color
        away_color: Away team color
        bg_color: Background color
        
    Returns:
        Tuple of (figure, axis)
    """
    fig, ax = plt.subplots(figsize=(10, 10), facecolor=bg_color)
    pitch = Pitch(pitch_type='uefa', pitch_color=bg_color, line_color='white', linewidth=2, corner_arcs=True)
    pitch.draw(ax=ax)
    ax.set_ylim(-0.5, 68.5)
    ax.set_xlim(-0.5, 105.5)
    
    # Split shots by team
    home_shots = shots_merged[shots_merged['teamId'] == home_id]
    away_shots = shots_merged[shots_merged['teamId'] == away_id]
    
    # Helper function to plot shots with correct positioning
    def plot_shots(df, color, is_home_team=True, marker='o', s=200, edgecolor=None, fill=True, hatch=None, zorder=2):
        if len(df) > 0:
            face_color = color if fill else 'none'
            edge_color = edgecolor if edgecolor else color
            
            # Transform coordinates based on team
            if is_home_team:
                x_coords = 105 - df['x']
                y_coords = 68 - df['y']
            else:
                x_coords = df['x']
                y_coords = df['y']
                
            ax.scatter(x_coords, y_coords, s=s, c=face_color, marker=marker, 
                      edgecolors=edge_color, zorder=zorder, hatch=hatch, linewidth=1.5)
    
    # Plot different shot types for both teams
    # Goals
    home_goals = home_shots[(home_shots['eventType'] == 'Goal') & (~home_shots['is_own_goal'])]
    plot_shots(home_goals, 'none', is_home_team=True, marker='o', s=350, edgecolor='green', zorder=3)
    
    away_goals = away_shots[(away_shots['eventType'] == 'Goal') & (~away_shots['is_own_goal'])]
    plot_shots(away_goals, 'none', is_home_team=False, marker='o', s=350, edgecolor='green', zorder=3)
    
    # Regular shots and other shot types...
    # (Additional shot plotting logic would continue here)
    
    # Stats bar
    stats_labels = ["Goals", "xG", "xGOT", "Shots", "On Target", "BigChance", "BigC.Miss", "xG/Shot", "Avg.Dist"]
    y_positions = [62 - i * 7 for i in range(len(stats_labels))]
    
    # Team names
    ax.text(0, 70, f"{home_name}\n<- Shots", color=home_color, size=22, ha='left', fontweight='bold')
    ax.text(105, 70, f"{away_name}\nShots ->", color=away_color, size=22, ha='right', fontweight='bold')
    
    ax.axis('off')
    
    return fig, ax


# =============================================================================
# xT MOMENTUM FUNCTIONS
# =============================================================================

def plot_xt_momentum(df_events: pd.DataFrame, xT_grid: np.ndarray, team_id_to_name: dict,
                    home_team_id: int, away_team_id: int, window_size: int = 4,
                    decay_rate: float = 0.25, sigma: float = 1.0,
                    home_color: str = '#43A1D5', away_color: str = '#FF4C4C',
                    bg_color: str = '#0C0D0E', line_color: str = 'white',
                    figsize: tuple = (12, 6)):
    """Plot match momentum using xT (Expected Threat).
    
    Args:
        df_events: DataFrame containing match events
        xT_grid: NumPy array with xT values for pitch zones
        team_id_to_name: Dictionary mapping team IDs to names
        home_team_id: Home team identifier
        away_team_id: Away team identifier
        window_size: Rolling window size for momentum calculation
        decay_rate: Decay rate for weighted momentum
        sigma: Gaussian filter sigma for smoothing
        home_color: Home team color
        away_color: Away team color
        bg_color: Background color
        line_color: Line color
        figsize: Figure size tuple
        
    Returns:
        Matplotlib figure object
    """
    # Scale coordinates if needed
    df = df_events.copy()
    df['x'] = df['x'] * 1.2
    df['y'] = df['y'] * 0.8
    df['end_x'] = df['end_x'] * 1.2
    df['end_y'] = df['end_y'] * 0.8

    n_rows, n_cols = xT_grid.shape

    # Filter for successful passes and carries
    mask = (
        df['type_display_name'].isin(['Pass', 'Carry']) &
        (df['outcome_type_display_name'] == 'Successful')
    )
    df_xT = df[mask].copy()

    # Bin start/end locations to xT grid
    def get_bin(val, max_val, n_bins):
        val = max(0, min(val, max_val))
        bin_idx = int(val / max_val * n_bins)
        return min(bin_idx, n_bins - 1)

    df_xT['start_x_bin'] = df_xT['x'].apply(lambda x: get_bin(x, 120, n_cols))
    df_xT['start_y_bin'] = df_xT['y'].apply(lambda y: get_bin(y, 80, n_rows))
    df_xT['end_x_bin'] = df_xT['end_x'].apply(lambda x: get_bin(x, 120, n_cols))
    df_xT['end_y_bin'] = df_xT['end_y'].apply(lambda y: get_bin(y, 80, n_rows))

    # Calculate xT for each action
    df_xT['start_zone_value'] = df_xT.apply(lambda row: xT_grid[row['start_y_bin'], row['start_x_bin']], axis=1)
    df_xT['end_zone_value'] = df_xT.apply(lambda row: xT_grid[row['end_y_bin'], row['end_x_bin']], axis=1)
    df_xT['xT'] = df_xT['end_zone_value'] - df_xT['start_zone_value']

    # Clip xT values
    df_xT['xT_clipped'] = np.clip(df_xT['xT'], 0, 0.1)

    # Map team_id to team name
    df_xT['team'] = df_xT['team_id'].map(team_id_to_name)

    # Calculate momentum
    max_xT_per_minute = df_xT.groupby(['team', 'minute'])['xT_clipped'].max().reset_index()
    minutes = sorted(max_xT_per_minute['minute'].unique())
    teams = [team_id_to_name[home_team_id], team_id_to_name[away_team_id]]
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

    momentum_df = pd.DataFrame({
        'minute': minutes,
        'momentum': momentum
    })

    # Plotting
    fig, ax = plt.subplots(figsize=figsize)
    fig.set_facecolor(bg_color)
    ax.set_facecolor(bg_color)

    # Smoothing
    momentum_df['smoothed_momentum'] = gaussian_filter1d(momentum_df['momentum'], sigma=sigma)
    ax.plot(momentum_df['minute'], momentum_df['smoothed_momentum'], color=line_color, linewidth=2)

    ax.axhline(0, color=line_color, linestyle='--', linewidth=1, alpha=0.7)
    ax.fill_between(momentum_df['minute'], momentum_df['smoothed_momentum'], 
                   where=(momentum_df['smoothed_momentum'] > 0), color=home_color, alpha=0.5, interpolate=True)
    ax.fill_between(momentum_df['minute'], momentum_df['smoothed_momentum'], 
                   where=(momentum_df['smoothed_momentum'] < 0), color=away_color, alpha=0.5, interpolate=True)

    # Team names
    ax.text(2, 0.07, team_id_to_name[home_team_id], fontsize=16, ha='left', va='center', 
            color=home_color, fontweight='bold')
    ax.text(2, -0.07, team_id_to_name[away_team_id], fontsize=16, ha='left', va='center', 
            color=away_color, fontweight='bold')

    # Mark goals
    for team_id, y in [(home_team_id, 0.06), (away_team_id, -0.06)]:
        goals = df_events[
            (df_events['team_id'] == team_id) &
            (df_events['type_display_name'] == 'Goal')
        ]['minute']
        for minute in goals:
            ax.axvline(minute, color=line_color, linestyle=':', linewidth=1, alpha=0.5)
            ax.scatter(minute, y, color=line_color, s=80, zorder=10, alpha=0.8)
            ax.text(minute+0.2, y+0.01*(1 if y>0 else -1), 'Goal', fontsize=10, 
                   ha='left', va='center', color=line_color)

    # Aesthetics
    ax.set_xlabel('Minute', color=line_color, fontsize=15, fontweight='bold')
    ax.set_ylabel('Momentum', color=line_color, fontsize=15, fontweight='bold')
    ax.set_xticks([0,15,30,45,60,75,90])
    ax.tick_params(axis='x', colors=line_color)
    ax.tick_params(axis='y', left=False, right=False, labelleft=False)
    for spine in ['top', 'right', 'bottom', 'left']:
        ax.spines[spine].set_visible(False)
    ax.margins(x=0)
    ax.set_ylim(-0.08, 0.08)
    ax.set_title('xT Momentum', color=line_color, fontsize=20, fontweight='bold', pad=-5)
    plt.tight_layout()
    return fig


# =============================================================================
# MATCH STATISTICS FUNCTIONS
# =============================================================================

def calculate_match_stats(df: pd.DataFrame, hteam_id: int, ateam_id: int) -> dict:
    """Calculate match statistics from event data.
    
    Args:
        df: DataFrame containing match events
        hteam_id: Home team ID
        ateam_id: Away team ID
        
    Returns:
        Dictionary containing calculated statistics
    """
    stats = {}
    
    # Helper function to extract qualifiers
    def has_qualifier(event, qualifier_name):
        qualifiers = event.get('qualifiers', [])
        return any(
            q.get('type', {}).get('displayName') == qualifier_name 
            for q in qualifiers if isinstance(q, dict)
        )
    
    # Possession
    home_passes = df[(df['team_id'] == hteam_id) & (df['type_display_name'] == 'Pass')]
    away_passes = df[(df['team_id'] == ateam_id) & (df['type_display_name'] == 'Pass')]
    total_passes = len(home_passes) + len(away_passes)
    stats['Possession'] = {
        'home': round((len(home_passes) / total_passes) * 100, 2) if total_passes else 0,
        'away': round((len(away_passes) / total_passes) * 100, 2) if total_passes else 0
    }
    
    # Field Tilt
    home_touches = df[(df['team_id'] == hteam_id) & (df['is_touch'] == True) & (df['x'] >= 70)]
    away_touches = df[(df['team_id'] == ateam_id) & (df['is_touch'] == True) & (df['x'] >= 70)]
    total_touches = len(home_touches) + len(away_touches)
    stats['Field Tilt'] = {
        'home': round((len(home_touches) / total_touches) * 100, 2) if total_touches else 0,
        'away': round((len(away_touches) / total_touches) * 100, 2) if total_touches else 0
    }
    
    # Passes (Acc.)
    stats['Passes (Acc.)'] = {
        'home': len(home_passes[home_passes['outcome_type_display_name'] == 'Successful']),
        'away': len(away_passes[away_passes['outcome_type_display_name'] == 'Successful'])
    }

    # Shots
    home_shots = df[(df['team_id'] == hteam_id) & (df['type_display_name'].isin(['SavedShot', 'MissedShots', 'ShotOnPost', 'Goal']))]
    away_shots = df[(df['team_id'] == ateam_id) & (df['type_display_name'].isin(['SavedShot', 'MissedShots', 'ShotOnPost', 'Goal']))]
    stats['Shots'] = {
        'home': len(home_shots),
        'away': len(away_shots)
    }

    # Tackles
    home_tackles = df[(df['team_id'] == hteam_id) & (df['type_display_name'] == 'Tackle')]
    away_tackles = df[(df['team_id'] == ateam_id) & (df['type_display_name'] == 'Tackle')]
    stats['Tackles'] = {
        'home': len(home_tackles[home_tackles['outcome_type_display_name'] == 'Successful']),
        'away': len(away_tackles[away_tackles['outcome_type_display_name'] == 'Successful'])
    }

    # Interceptions
    home_intercepts = df[(df['team_id'] == hteam_id) & (df['type_display_name'] == 'Interception')]
    away_intercepts = df[(df['team_id'] == ateam_id) & (df['type_display_name'] == 'Interception')]
    stats['Interceptions'] = {
        'home': len(home_intercepts),
        'away': len(away_intercepts)
    }

    # Aerials
    home_aerials = df[(df['team_id'] == hteam_id) & (df['type_display_name'] == 'Aerial')]
    away_aerials = df[(df['team_id'] == ateam_id) & (df['type_display_name'] == 'Aerial')]
    stats['Aerials Won'] = {
        'home': len(home_aerials[home_aerials['outcome_type_display_name'] == 'Successful']),
        'away': len(away_aerials[away_aerials['outcome_type_display_name'] == 'Successful'])
    }

    # Clearances
    home_clears = df[(df['team_id'] == hteam_id) & (df['type_display_name'] == 'Clearance')]
    away_clears = df[(df['team_id'] == ateam_id) & (df['type_display_name'] == 'Clearance')]
    stats['Clearances'] = {
        'home': len(home_clears),
        'away': len(away_clears)
    }

    # Fouls
    home_fouls = df[(df['team_id'] == hteam_id) & (df['type_display_name'] == 'Foul')]
    away_fouls = df[(df['team_id'] == ateam_id) & (df['type_display_name'] == 'Foul')]
    stats['Fouls'] = {
        'home': len(home_fouls),
        'away': len(away_fouls)
    }

    return stats


def plot_match_stats_styled(stats: dict, home_team_name: str = "Home", away_team_name: str = "Away"):
    """Plot match statistics with dark aesthetic style.
    
    Args:
        stats: Dictionary containing match statistics
        home_team_name: Home team name
        away_team_name: Away team name
    """
    # Signature colors
    bg_color = '#0C0D0E'
    line_color = 'white'
    col1 = '#43A1D5'  # Home team blue
    col2 = '#FF4C4C'  # Away team red
    
    # Extract data from stats dictionary
    stat_names = list(stats.keys())
    home_values = [stats[stat]['home'] for stat in stat_names]
    away_values = [stats[stat]['away'] for stat in stat_names]
    
    # Calculate normalized values for bars
    normalized_home = []
    normalized_away = []
    
    for i, stat in enumerate(stat_names):
        home_val = home_values[i]
        away_val = away_values[i]
        total = home_val + away_val
        
        if total > 0:
            home_norm = -(home_val / total) * 50  # Negative for left side
            away_norm = (away_val / total) * 50   # Positive for right side
        else:
            home_norm = away_norm = 0
            
        normalized_home.append(home_norm)
        normalized_away.append(away_norm)
    
    # Create figure
    fig, ax = plt.subplots(figsize=(10, 10), facecolor=bg_color)
    
    # Draw pitch background
    pitch = Pitch(pitch_type='uefa', corner_arcs=True, pitch_color=bg_color, 
                  line_color=bg_color, linewidth=2)
    pitch.draw(ax=ax)
    ax.set_xlim(-0.5, 105.5)
    ax.set_ylim(-5, 68.5)
    
    # Path effects for text
    path_eff = [path_effects.Stroke(linewidth=1.5, foreground=line_color), 
                path_effects.Normal()]
    
    ax.text(52.5, 64.5, "Match Stats Comparison", ha='center', va='center', 
            color=line_color, fontsize=25, fontweight='bold', path_effects=path_eff)
    
    # Y positions for stats
    stats_y_positions = [58 - (i * 6) for i in range(len(stat_names))]
    
    # Draw bars
    start_x = 52.5
    ax.barh(stats_y_positions, normalized_home, height=4, color=col1, left=start_x)
    ax.barh(stats_y_positions, normalized_away, height=4, left=start_x, color=col2)
    
    # Clean up axis
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.tick_params(axis='both', which='both', bottom=False, top=False, 
                   left=False, right=False)
    ax.set_xticks([])
    ax.set_yticks([])
    
    # Add stat labels and values
    for i, (stat_name, y_pos) in enumerate(zip(stat_names, stats_y_positions)):
        ax.text(52.5, y_pos, stat_name, color=bg_color, fontsize=17, 
                ha='center', va='center', fontweight='bold', path_effects=path_eff)
        
        # Format values based on stat type
        home_val = home_values[i]
        away_val = away_values[i]
        
        if 'Possession' in stat_name or 'Field Tilt' in stat_name:
            home_text = f"{round(home_val)}%"
            away_text = f"{round(away_val)}%"
        else:
            home_text = f"{home_val}"
            away_text = f"{away_val}"
            
        # Home team values (left side)
        ax.text(0, y_pos, home_text, color=line_color, fontsize=20, 
                ha='right', va='center', fontweight='bold')
        # Away team values (right side)
        ax.text(105, y_pos, away_text, color=line_color, fontsize=20, 
                ha='left', va='center', fontweight='bold')
    
    plt.tight_layout()
    plt.show()

# ==================== DEFENSIVE ANALYSIS FUNCTIONS ====================

def filter_defensive_actions(df_events: pd.DataFrame) -> pd.DataFrame:
    """Filter events to get only defensive actions."""
    defensive_types = [
        'Tackle', 'Interception', 'BallRecovery', 'BlockedPass', 
        'Challenge', 'Clearance', 'Foul', 'Aerial'
    ]
    
    defensive_actions = df_events[
        df_events['type_display_name'].isin(defensive_types)
    ].copy()
    
    # Convert coordinates from WhoScored (0-100) to StatsBomb (0-120x0-80)
    defensive_actions['x_sb'] = defensive_actions['x'] * 1.2
    defensive_actions['y_sb'] = defensive_actions['y'] * 0.8
    
    return defensive_actions


def defensive_block(ax, team_positions: dict, team_actions: pd.DataFrame, 
                   team_name: str, team_color: str, is_away_team: bool = False):
    """Create defensive block visualization for one team."""
    from mplsoccer import Pitch
    from matplotlib.colors import LinearSegmentedColormap, to_rgba
    
    pitch = Pitch(
        pitch_type='statsbomb',
        pitch_color='#0C0D0E',
        line_color='white',
        linewidth=2,
        line_zorder=2,
        corner_arcs=True
    )
    pitch.draw(ax=ax)
    ax.set_facecolor('#0C0D0E')
    ax.set_xlim(-0.5, 120.5)
    ax.set_ylim(-0.5, 80.5)
    
    if len(team_positions) == 0 or len(team_actions) == 0:
        ax.set_title(f"{team_name}\nDefensive Action Heatmap", 
                    color='white', fontsize=20, fontweight='bold')
        return {}
    
    # Convert positions to DataFrame
    positions_df = pd.DataFrame.from_dict(team_positions, orient='index')
    
    # Variable marker size based on defensive actions
    MAX_MARKER_SIZE = 3500
    positions_df['marker_size'] = (
        positions_df['action_count'] / positions_df['action_count'].max() * MAX_MARKER_SIZE
    )
    
    # Create KDE heatmap
    color = np.array(to_rgba(team_color))
    flamingo_cmap = LinearSegmentedColormap.from_list(
        "Team colors", ['#0C0D0E', team_color], N=500
    )
    
    kde = pitch.kdeplot(
        team_actions['x_sb'], team_actions['y_sb'], 
        ax=ax, fill=True, levels=5000, thresh=0.02, cut=4, cmap=flamingo_cmap
    )
    
    # Plot player nodes
    for idx, row in positions_df.iterrows():
        marker = 'o' if row['is_starter'] else 's'
            
        pitch.scatter(
            row['x'], row['y'], 
            s=row['marker_size'] + 100,
            marker=marker, 
            color='#0C0D0E',
            edgecolor='white',
            linewidth=1,
            alpha=1, 
            zorder=3, 
            ax=ax
        )
    
    # Plot tiny scatter for defensive actions
    pitch.scatter(
        team_actions['x_sb'], team_actions['y_sb'],
        s=10, marker='x', color='yellow', alpha=0.2, ax=ax
    )
    
    # Add shirt numbers
    for idx, row in positions_df.iterrows():
        pitch.annotate(
            str(row['shirt_no']), 
            xy=(row['x'], row['y']),
            c='white', ha='center', va='center', size=14, ax=ax
        )
    
    # Calculate metrics
    dah = round(positions_df['x'].mean(), 2)
    dah_show = round((dah * 1.05), 2)
    
    # Defense line height (center backs)
    center_backs = positions_df[positions_df['position'] == 'DC']
    def_line_h = round(center_backs['x'].median(), 2) if len(center_backs) > 0 else dah
    
    # Forward line height (top 2 advanced players)
    starters = positions_df[positions_df['is_starter'] == True]
    if len(starters) >= 2:
        forwards = starters.nlargest(2, 'x')
        fwd_line_h = round(forwards['x'].mean(), 2)
    else:
        fwd_line_h = dah
    
    # Calculate compactness
    compactness = round((1 - ((fwd_line_h - def_line_h) / 120)) * 100, 2)
    
    # Add vertical lines
    ax.axvline(x=dah, color='gray', linestyle='--', alpha=0.75, linewidth=2)
    ax.axvline(x=def_line_h, color='gray', linestyle='dotted', alpha=0.5, linewidth=2)
    ax.axvline(x=fwd_line_h, color='gray', linestyle='dotted', alpha=0.5, linewidth=2)
    
    # Invert axes for away team
    if is_away_team:
        ax.invert_xaxis()
        ax.invert_yaxis()
        ax.text(dah-1, 78, f"{dah_show}m", fontsize=15, color='white', ha='left', va='center')
        ax.text(120, 78, f'Compact:{compactness}%', fontsize=15, color='white', ha='left', va='center')
        ax.text(2, 2, "circle = starter\nbox = sub", color='gray', size=12, ha='right', va='top')
    else:
        ax.text(dah-1, -3, f"{dah_show}m", fontsize=15, color='white', ha='right', va='center')
        ax.text(120, -3, f'Compact:{compactness}%', fontsize=15, color='white', ha='right', va='center')
        ax.text(2, 78, "circle = starter\nbox = sub", color='gray', size=12, ha='left', va='top')
    
    ax.set_title(f"{team_name}\nDefensive Action Heatmap", 
                color='white', fontsize=20, fontweight='bold')
    
    return {
        'Team_Name': team_name,
        'Average_Defensive_Action_Height': dah,
        'Forward_Line_Pressing_Height': fwd_line_h,
        'Compactness': compactness
    }


def draw_progressive_pass_map(ax, df_events, team_id, team_name, team_color, is_away_team=False):
    """Draw progressive pass map with defensive block aesthetic."""
    from mplsoccer import Pitch
    
    # Filter progressive passes
    dfpro = df_events[
        (df_events['team_id'] == team_id) & 
        (df_events['type_display_name'] == 'Pass') &
        (df_events['outcome_type_display_name'] == 'Successful') &
        (~df_events['qualifiers'].astype(str).str.contains('CornerTaken|Freekick', na=False)) & 
        (df_events['x'] >= 35) &
        (df_events['prog_pass'] >= 9.11)
    ].copy()
    
    # Create pitch
    pitch = Pitch(
        pitch_type='statsbomb',
        pitch_color='#0C0D0E',
        line_color='white',
        linewidth=2,
        line_zorder=2,
        corner_arcs=True
    )
    pitch.draw(ax=ax)
    ax.set_facecolor('#0C0D0E')
    ax.set_xlim(-0.5, 120.5)
    ax.set_ylim(-0.5, 80.5)
    
    # Invert axes for away team
    if is_away_team:
        ax.invert_xaxis()
        ax.invert_yaxis()
    
    pro_count = len(dfpro)
    
    if pro_count > 0:
        # Calculate zone statistics (StatsBomb coordinates: 0-80 width)
        left_pro = len(dfpro[dfpro['y'] >= 53.33])
        mid_pro = len(dfpro[(dfpro['y'] >= 26.67) & (dfpro['y'] < 53.33)])
        right_pro = len(dfpro[dfpro['y'] < 26.67])
        
        left_percentage = round((left_pro/pro_count)*100) if pro_count > 0 else 0
        mid_percentage = round((mid_pro/pro_count)*100) if pro_count > 0 else 0
        right_percentage = round((right_pro/pro_count)*100) if pro_count > 0 else 0
        
        # Add zone dividing lines
        ax.hlines(26.67, xmin=0, xmax=120, colors='white', linestyle='dashed', alpha=0.35)
        ax.hlines(53.33, xmin=0, xmax=120, colors='white', linestyle='dashed', alpha=0.35)
        
        # Text styling
        bbox_props = dict(boxstyle="round,pad=0.3", edgecolor="None", facecolor='#0C0D0E', alpha=0.75)
        
        # Position text annotations
        ax.text(8, 13.335, f'{right_pro}\n({right_percentage}%)', color=team_color, fontsize=24, 
               va='center', ha='center', bbox=bbox_props, weight='bold')
        ax.text(8, 40, f'{mid_pro}\n({mid_percentage}%)', color=team_color, fontsize=24, 
               va='center', ha='center', bbox=bbox_props, weight='bold')
        ax.text(8, 66.67, f'{left_pro}\n({left_percentage}%)', color=team_color, fontsize=24, 
               va='center', ha='center', bbox=bbox_props, weight='bold')
        
        # Plot progressive passes with comet effect
        pitch.lines(dfpro['x'], dfpro['y'], dfpro['end_x'], dfpro['end_y'], 
                   lw=3.5, comet=True, color=team_color, ax=ax, alpha=0.5)
        
        # Add end points
        pitch.scatter(dfpro['end_x'], dfpro['end_y'], s=35, edgecolor=team_color, 
                     linewidth=1, facecolor='#0C0D0E', zorder=2, ax=ax)
    
    counttext = f"{pro_count} Progressive Passes"
    ax.set_title(f"{team_name}\n{counttext}", color='white', fontsize=25, fontweight='bold')
    
    return {
        'Team_Name': team_name,
        'Total_Progressive_Passes': pro_count
    }
