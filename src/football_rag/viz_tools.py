"""Visualization tools bridging RAG pipeline and plotting library.

Simple, focused functions following CLAUDE.md principles:
- No classes (just functions)
- Shared data loading logic (_load_all_match_data)
- 3 public functions (dashboard, team viz, match viz)
"""
import json
import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path
from football_rag import visualizers


PROJECT_ROOT = Path(__file__).parent.parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"
OUTPUT_DIR = PROJECT_ROOT / "data" / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _load_all_match_data(match_id: str):
    """Load all data needed for visualizations.

    Returns dict with: df_events, fotmob_shots, xT_grid, team_ids,
                       team_players, player_names, team_names_dict
    """
    ws_path = RAW_DIR / "whoscored_matches" / "eredivisie" / "2025-2026" / f"match_{match_id}.json"
    if not ws_path.exists():
        raise FileNotFoundError(f"Match data not found: {match_id}")

    with open(ws_path) as f:
        ws_data = json.load(f)

    df_events = pd.DataFrame(ws_data['events'])
    xT_grid = pd.read_csv(RAW_DIR / "xT_grid.csv", header=None).values

    team_ids = list(df_events['team_id'].unique())

    player_names = {}
    for _, event in df_events.iterrows():
        if 'player_id' in event and pd.notna(event['player_id']):
            player_names[event['player_id']] = f"Player {event['player_id']}"

    team_players = {
        team_id: [
            {
                'playerId': pid,
                'name': f"Player {pid}",
                'shirtNo': idx + 1,
                'position': 'Unknown',
                'isFirstEleven': idx < 11
            }
            for idx, pid in enumerate(df_events[df_events['team_id'] == team_id]['player_id'].unique()[:20])
        ]
        for team_id in team_ids
    }

    team_names_dict = {tid: f"Team {tid}" for tid in team_ids}

    match_mapping_file = PROJECT_ROOT / "data" / "match_mapping.json"
    fotmob_match_id = None
    if match_mapping_file.exists():
        with open(match_mapping_file) as f:
            mappings = json.load(f)
        mapping = mappings.get(str(match_id))
        if mapping:
            fotmob_match_id = mapping.get('fotmob_id')

    fotmob_bulk = RAW_DIR / "eredivisie_2025_2026_fotmob.json"
    fotmob_shots = []
    if fotmob_bulk.exists() and fotmob_match_id:
        with open(fotmob_bulk) as f:
            all_matches = json.load(f)
        for match in all_matches:
            if match.get('match_id') == fotmob_match_id:
                shots = match.get('shots', [])
                shots_df = pd.DataFrame(shots)
                if len(shots_df) > 0:
                    if 'teamId' in shots_df.columns:
                        shots_df = shots_df.rename(columns={'teamId': 'team_id'})
                    shots_df['is_big_chance'] = False
                    shots_df['is_own_goal'] = shots_df.get('isOwnGoal', False)
                    fotmob_shots = shots_df.to_dict('records')
                break

    return {
        'df_events': df_events,
        'fotmob_shots': fotmob_shots,
        'xT_grid': xT_grid,
        'team_ids': team_ids,
        'team_players': team_players,
        'player_names': player_names,
        'team_names_dict': team_names_dict
    }


def generate_dashboard(match_id: str, home_name: str = None, away_name: str = None) -> str:
    """Generate full 3x3 tactical match report dashboard.

    Args:
        match_id: WhoScored match ID
        home_name: Optional home team name (defaults to "Team {id}")
        away_name: Optional away team name (defaults to "Team {id}")

    Returns:
        Path to saved dashboard image
    """
    data = _load_all_match_data(match_id)

    team_names = {
        data['team_ids'][0]: home_name or data['team_names_dict'][data['team_ids'][0]],
        data['team_ids'][1]: away_name or data['team_names_dict'][data['team_ids'][1]]
    }

    save_path = OUTPUT_DIR / f"dashboard_{match_id}.png"

    visualizers.create_dashboard_match_report(
        data['df_events'],
        data['team_ids'],
        data['team_players'],
        data['player_names'],
        data['xT_grid'],
        save_path,
        team_names,
        data['fotmob_shots']
    )

    return str(save_path)


def generate_team_viz(match_id: str, team_name: str, viz_type: str) -> str:
    """Generate team-specific visualization.

    Args:
        match_id: WhoScored match ID
        team_name: Team name to visualize
        viz_type: One of: passing_network, defensive_heatmap, progressive_passes

    Returns:
        Path to saved visualization
    """
    data = _load_all_match_data(match_id)

    team_id = None
    for tid in data['team_ids']:
        if team_name.lower() in data['team_names_dict'][tid].lower():
            team_id = tid
            break

    if team_id is None:
        team_id = data['team_ids'][0]

    save_path = OUTPUT_DIR / f"{viz_type}_{team_name.replace(' ', '_')}_{match_id}.png"

    if viz_type == "passing_network":
        passes_df = visualizers.prepare_enhanced_passes(data['df_events'])
        avg_locs = visualizers.get_enhanced_positions(
            passes_df, team_id, data['team_players'][team_id], data['player_names']
        )
        combinations = visualizers.get_pass_combinations(passes_df, team_id)
        metrics = visualizers.calculate_team_metrics(passes_df, avg_locs, team_id)

        fig, ax = plt.subplots(figsize=(12, 10), facecolor='#0e1117')
        visualizers.plot_enhanced_network(
            ax, passes_df, avg_locs, combinations, metrics,
            team_name, color='#43A1D5', is_home=True, bg_color='#0e1117'
        )
        plt.savefig(save_path, dpi=150, facecolor='#0e1117', bbox_inches='tight')
        plt.close()

    elif viz_type == "defensive_heatmap":
        defensive_actions = visualizers.filter_defensive_actions(data['df_events'])
        team_positions = visualizers.calculate_player_defensive_positions(
            defensive_actions, team_id, data['team_players'][team_id]
        )
        team_actions = defensive_actions[defensive_actions['team_id'] == team_id]

        fig, ax = plt.subplots(figsize=(12, 10), facecolor='#0e1117')
        visualizers.defensive_block(
            ax, team_positions, team_actions, team_name, '#43A1D5', is_away_team=False
        )
        plt.savefig(save_path, dpi=150, facecolor='#0e1117', bbox_inches='tight')
        plt.close()

    elif viz_type == "progressive_passes":
        data['df_events']['prog_pass'] = (
            (105 - data['df_events']['x'])**2 + (34 - data['df_events']['y'])**2
        )**0.5 - (
            (105 - data['df_events']['end_x'])**2 + (34 - data['df_events']['end_y'])**2
        )**0.5

        fig, ax = plt.subplots(figsize=(12, 10), facecolor='#0e1117')
        visualizers.draw_progressive_pass_map(
            ax, data['df_events'], team_id, team_name, '#43A1D5', is_away_team=False
        )
        plt.savefig(save_path, dpi=150, facecolor='#0e1117', bbox_inches='tight')
        plt.close()

    else:
        raise ValueError(f"Unknown viz_type: {viz_type}")

    return str(save_path)


def generate_match_viz(match_id: str, viz_type: str) -> str:
    """Generate match-level visualization (both teams).

    Args:
        match_id: WhoScored match ID
        viz_type: One of: shot_map, xt_momentum, match_stats

    Returns:
        Path to saved visualization
    """
    data = _load_all_match_data(match_id)

    save_path = OUTPUT_DIR / f"{viz_type}_{match_id}.png"
    team_id_to_name = data['team_names_dict']

    if viz_type == "shot_map":
        fig, ax = plt.subplots(figsize=(12, 10), facecolor='#0e1117')
        ax.set_facecolor('#0e1117')

        if len(data['fotmob_shots']) > 0:
            visualizers.plot_shot_map_on_axis(
                ax, data['fotmob_shots'],
                home_fotmob_id=9791, away_fotmob_id=6413,
                home_team_name=team_id_to_name[data['team_ids'][0]],
                away_team_name=team_id_to_name[data['team_ids'][1]]
            )
        else:
            ax.text(0.5, 0.5, 'No shot data available',
                   transform=ax.transAxes, ha='center', va='center',
                   color='white', fontsize=14)
            ax.axis('off')

        plt.savefig(save_path, dpi=150, facecolor='#0e1117', bbox_inches='tight')
        plt.close()

    elif viz_type == "xt_momentum":
        fig = visualizers.plot_xt_momentum(
            data['df_events'], data['xT_grid'], team_id_to_name,
            data['team_ids'][0], data['team_ids'][1], bg_color='#0e1117'
        )
        plt.savefig(save_path, dpi=150, facecolor='#0e1117', bbox_inches='tight')
        plt.close()

    elif viz_type == "match_stats":
        stats = visualizers.calculate_match_stats(
            data['df_events'], data['team_ids'][0], data['team_ids'][1]
        )

        fig, ax = plt.subplots(figsize=(10, 10), facecolor='#0e1117')
        visualizers.plot_match_stats_on_axis(
            ax, stats,
            team_id_to_name[data['team_ids'][0]],
            team_id_to_name[data['team_ids'][1]]
        )
        plt.savefig(save_path, dpi=150, facecolor='#0e1117', bbox_inches='tight')
        plt.close()

    else:
        raise ValueError(f"Unknown viz_type: {viz_type}")

    return str(save_path)
