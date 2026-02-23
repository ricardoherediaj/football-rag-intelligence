"""Visualization tools bridging RAG pipeline and plotting library.

Simple, focused functions following CLAUDE.md principles:
- No classes (just functions)
- Shared data loading logic (_load_all_match_data)
- 3 public functions (dashboard, team viz, match viz)
"""
import duckdb
import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path
from football_rag import visualizers


PROJECT_ROOT = Path(__file__).parent.parent.parent
XTG_GRID_PATH = PROJECT_ROOT / "data" / "raw" / "xT_grid.csv"
OUTPUT_DIR = PROJECT_ROOT / "data" / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _load_all_match_data(match_id: str) -> dict:
    """Load all data needed for visualizations from MotherDuck.

    Replaces local JSON reads with MotherDuck queries so the app runs
    stateless (no raw data files required at runtime).

    Returns dict with: df_events, fotmob_shots, xT_grid, team_ids,
                       team_players, player_names, team_names_dict
    """
    db = duckdb.connect("md:football_rag")

    df_events = db.execute(
        """
        SELECT *, event_row_id AS id
        FROM football_rag.main_main.silver_events
        WHERE match_id = ?
        """,
        [str(match_id)],
    ).df()

    if df_events.empty:
        db.close()
        raise FileNotFoundError(f"Match data not found in silver_events: {match_id}")

    shots_rows = db.execute(
        """
        SELECT s.*
        FROM football_rag.main.silver_fotmob_shots s
        JOIN football_rag.main.match_mapping m ON s.match_id = m.fotmob_match_id
        WHERE m.whoscored_match_id = ?
        """,
        [str(match_id)],
    ).fetchall()
    shots_cols = [d[0] for d in db.description]

    # Get real team names from match_mapping
    mapping_row = db.execute(
        """
        SELECT whoscored_team_id_1, whoscored_team_id_2, home_team, away_team
        FROM football_rag.main.match_mapping
        WHERE whoscored_match_id = ?
        """,
        [str(match_id)],
    ).fetchone()
    db.close()

    xT_grid = pd.read_csv(XTG_GRID_PATH, header=None).values

    team_ids = [int(t) for t in df_events["team_id"].dropna().unique().tolist()]

    player_names = {
        int(pid): f"Player {int(pid)}"
        for pid in df_events["player_id"].dropna().unique()
    }

    team_players = {
        team_id: [
            {
                "playerId": pid,
                "name": f"Player {pid}",
                "shirtNo": idx + 1,
                "position": "Unknown",
                "isFirstEleven": idx < 11,
            }
            for idx, pid in enumerate(
                df_events[df_events["team_id"] == team_id]["player_id"]
                .dropna()
                .unique()[:20]
                .tolist()
            )
        ]
        for team_id in team_ids
    }

    # Use real team names from match_mapping when available
    if mapping_row:
        tid1, tid2, home_name, away_name = mapping_row
        team_names_dict = {int(tid1): home_name, int(tid2): away_name}
    else:
        team_names_dict = {tid: f"Team {tid}" for tid in team_ids}

    fotmob_shots = []
    if shots_rows:
        shots_df = pd.DataFrame(shots_rows, columns=shots_cols)
        # Rename snake_case DB columns to camelCase expected by visualizers.py
        shots_df = shots_df.rename(columns={
            "event_type": "eventType",
            "player_name": "playerName",
            "shot_type": "shotType",
            "is_on_target": "isOnTarget",
        })
        shots_df["is_big_chance"] = False
        shots_df["is_own_goal"] = shots_df.get("is_own_goal", False)
        fotmob_shots = shots_df.to_dict("records")

    return {
        "df_events": df_events,
        "fotmob_shots": fotmob_shots,
        "xT_grid": xT_grid,
        "team_ids": team_ids,
        "team_players": team_players,
        "player_names": player_names,
        "team_names_dict": team_names_dict,
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
            shots_df_tmp = pd.DataFrame(data['fotmob_shots'])
            fotmob_ids = shots_df_tmp['team_id'].unique().tolist()
            home_fotmob_id = fotmob_ids[0] if len(fotmob_ids) > 0 else None
            away_fotmob_id = fotmob_ids[1] if len(fotmob_ids) > 1 else None
            visualizers.plot_shot_map_on_axis(
                ax, data['fotmob_shots'],
                home_fotmob_id=home_fotmob_id, away_fotmob_id=away_fotmob_id,
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
