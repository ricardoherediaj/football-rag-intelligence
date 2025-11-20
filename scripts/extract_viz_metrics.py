"""Extract tactical metrics from match visualizations for evaluation dataset.

Focuses on 4 key areas:
1. Passing network (hub player, progressive passes, verticality)
2. Defensive actions (high press, PPDA)
3. Shot map (already in Fotmob data, just organize)
4. Tactical positioning (defense/forward lines)

Author: Football Analytics Team
"""

import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Any


def extract_passing_metrics(events: List[Dict], team_id: int) -> Dict[str, Any]:
    """Extract passing network metrics for a team.

    Args:
        events: List of match events from WhoScored
        team_id: Team identifier

    Returns:
        Dictionary with passing metrics
    """
    # Filter successful passes for this team
    passes = [
        e for e in events
        if e.get('team_id') == team_id
        and e.get('type_display_name') == 'Pass'
        and e.get('outcome_type_display_name') == 'Successful'
    ]

    if not passes:
        return {
            "hub_player_id": None,
            "hub_pass_count": 0,
            "progressive_passes": 0,
            "verticality_pct": 0,
            "total_passes": 0
        }

    # 1. Find hub player (most passes)
    player_passes = {}
    for p in passes:
        player_id = p['player_id']
        player_passes[player_id] = player_passes.get(player_id, 0) + 1

    hub_player_id, hub_pass_count = max(player_passes.items(), key=lambda x: x[1])

    # 2. Count progressive passes (forward movement > 10 yards)
    progressive = [
        p for p in passes
        if (p.get('end_x', 0) - p.get('x', 0)) > 10
    ]

    # 3. Calculate verticality (how direct the passing is)
    # Verticality = 100% means perfectly vertical (forward), 0% means perfectly horizontal
    angles = []
    for p in passes:
        dx = p.get('end_x', 0) - p.get('x', 0)
        dy = p.get('end_y', 0) - p.get('y', 0)
        if dx != 0 or dy != 0:
            angle_rad = np.arctan2(abs(dy), dx)  # 0 = horizontal, π/2 = vertical
            angle_deg = np.degrees(angle_rad)
            angles.append(angle_deg)

    median_angle = np.median(angles) if angles else 45
    verticality_pct = round((1 - median_angle / 90) * 100, 1)

    return {
        "hub_player_id": int(hub_player_id),
        "hub_pass_count": int(hub_pass_count),
        "progressive_passes": len(progressive),
        "verticality_pct": verticality_pct,
        "total_passes": len(passes)
    }


def extract_defensive_metrics(events: List[Dict], team_id: int, opponent_id: int) -> Dict[str, Any]:
    """Extract defensive action metrics for a team.

    Args:
        events: List of match events
        team_id: Team identifier
        opponent_id: Opponent team identifier

    Returns:
        Dictionary with defensive metrics
    """
    # Defensive action types
    defensive_types = ['Tackle', 'Interception', 'Clearance', 'BallRecovery', 'Aerial']

    # Filter defensive actions
    defensive_actions = [
        e for e in events
        if e.get('team_id') == team_id
        and e.get('type_display_name') in defensive_types
    ]

    if not defensive_actions:
        return {
            "total_defensive_actions": 0,
            "high_press_events": 0,
            "ppda": 0
        }

    # High press = defensive actions in final third (x > 70 in attacking direction)
    # Note: WhoScored uses 0-100 for x coordinate
    high_press = [
        e for e in defensive_actions
        if e.get('x', 0) > 70
    ]

    # PPDA = Passes Allowed Per Defensive Action
    # Lower PPDA = more aggressive pressing
    opponent_passes = [
        e for e in events
        if e.get('team_id') == opponent_id
        and e.get('type_display_name') == 'Pass'
    ]

    ppda = round(len(opponent_passes) / len(defensive_actions), 2) if defensive_actions else 0

    return {
        "total_defensive_actions": len(defensive_actions),
        "high_press_events": len(high_press),
        "ppda": ppda
    }


def extract_positional_metrics(events: List[Dict], team_id: int) -> Dict[str, Any]:
    """Extract tactical positioning metrics (defense/forward lines).

    Args:
        events: List of match events
        team_id: Team identifier

    Returns:
        Dictionary with positional metrics
    """
    # Get all touches for this team to calculate average positions
    team_events = [
        e for e in events
        if e.get('team_id') == team_id and e.get('is_touch', False)
    ]

    if not team_events:
        return {
            "team_median_position": 0,
            "defense_line_avg": 0,
            "forward_line_avg": 0
        }

    # Team median position
    x_positions = [e.get('x', 0) for e in team_events]
    team_median = round(np.median(x_positions), 1)

    # Note: Without player position data in events, we estimate based on x positions
    # Defense line = 25th percentile of x positions
    # Forward line = 75th percentile of x positions
    defense_line = round(np.percentile(x_positions, 25), 1)
    forward_line = round(np.percentile(x_positions, 75), 1)

    return {
        "team_median_position": team_median,
        "defense_line_avg": defense_line,
        "forward_line_avg": forward_line
    }


def extract_shot_metrics_from_fotmob(fotmob_data: Dict, home_team_id: int, away_team_id: int) -> Dict[str, Any]:
    """Extract shot metrics from Fotmob data.

    Args:
        fotmob_data: Fotmob match data with shots
        home_team_id: Home team identifier
        away_team_id: Away team identifier

    Returns:
        Dictionary with shot metrics for both teams
    """
    shots = fotmob_data.get('shots', [])

    if not shots:
        return {
            "home_shots": 0,
            "away_shots": 0,
            "home_xg": 0.0,
            "away_xg": 0.0,
            "home_shots_on_target": 0,
            "away_shots_on_target": 0
        }

    # Split shots by team
    home_shots = [s for s in shots if s.get('teamId') == home_team_id]
    away_shots = [s for s in shots if s.get('teamId') == away_team_id]

    # Calculate xG totals
    home_xg = sum(s.get('expectedGoals', 0) for s in home_shots)
    away_xg = sum(s.get('expectedGoals', 0) for s in away_shots)

    # Count shots on target
    home_on_target = sum(1 for s in home_shots if s.get('isOnTarget', False))
    away_on_target = sum(1 for s in away_shots if s.get('isOnTarget', False))

    return {
        "home_shots": len(home_shots),
        "away_shots": len(away_shots),
        "home_xg": round(home_xg, 2),
        "away_xg": round(away_xg, 2),
        "home_xg_per_shot": round(home_xg / len(home_shots), 3) if home_shots else 0,
        "away_xg_per_shot": round(away_xg / len(away_shots), 3) if away_shots else 0,
        "home_shots_on_target": home_on_target,
        "away_shots_on_target": away_on_target,
        "home_shot_accuracy": round(home_on_target / len(home_shots) * 100, 1) if home_shots else 0,
        "away_shot_accuracy": round(away_on_target / len(away_shots) * 100, 1) if away_shots else 0
    }


def extract_match_metrics(match_id: str, whoscored_path: Path, fotmob_path: Path = None) -> Dict[str, Any]:
    """Extract all tactical metrics for a match.

    Args:
        match_id: Match identifier (e.g., "1904034")
        whoscored_path: Path to WhoScored match JSON file
        fotmob_path: Optional path to Fotmob data

    Returns:
        Dictionary with all extracted metrics
    """
    # Load WhoScored data
    with open(whoscored_path) as f:
        ws_data = json.load(f)

    events = ws_data.get('events', [])

    # Get team IDs (first event's team and opponent)
    team_ids = set(e['team_id'] for e in events if 'team_id' in e)
    if len(team_ids) != 2:
        raise ValueError(f"Expected 2 teams, found {len(team_ids)}")

    team_ids = sorted(list(team_ids))
    home_team_id, away_team_id = team_ids[0], team_ids[1]

    # Extract metrics for both teams
    metrics = {
        "match_id": match_id,
        "home_team_id": home_team_id,
        "away_team_id": away_team_id,
        "home_passing": extract_passing_metrics(events, home_team_id),
        "away_passing": extract_passing_metrics(events, away_team_id),
        "home_defensive": extract_defensive_metrics(events, home_team_id, away_team_id),
        "away_defensive": extract_defensive_metrics(events, away_team_id, home_team_id),
        "home_positioning": extract_positional_metrics(events, home_team_id),
        "away_positioning": extract_positional_metrics(events, away_team_id)
    }

    return metrics


def extract_metrics_for_evaluation_matches(
    eval_matches_path: Path,
    whoscored_dir: Path,
    fotmob_path: Path,
    mapping_path: Path,
    output_dir: Path
) -> None:
    """Extract metrics for all evaluation matches.

    Args:
        eval_matches_path: Path to evaluation_matches.json
        whoscored_dir: Directory containing WhoScored match files
        fotmob_path: Path to Fotmob JSON file with all matches
        mapping_path: Path to match mapping JSON file
        output_dir: Directory to save extracted metrics
    """
    # Load evaluation matches
    with open(eval_matches_path) as f:
        eval_matches = json.load(f)

    # Load Fotmob data
    with open(fotmob_path) as f:
        fotmob_matches = json.load(f)

    # Load match mapping
    with open(mapping_path) as f:
        match_mapping = json.load(f)

    # Create index of Fotmob matches by match_id
    fotmob_index = {str(m['match_id']): m for m in fotmob_matches}

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Extract metrics for each match
    results = {}
    for match in eval_matches:
        match_id = match['whoscored_id']

        # Find WhoScored file
        ws_file = whoscored_dir / f"match_{match_id}.json"

        if not ws_file.exists():
            print(f"⚠️  WhoScored file not found for match {match_id}")
            continue

        print(f"📊 Extracting metrics for match {match_id}...")

        try:
            metrics = extract_match_metrics(match_id, ws_file)

            # Add Fotmob shot metrics if available
            if match_id in fotmob_index:
                fotmob_match = fotmob_index[match_id]
                shot_metrics = extract_shot_metrics_from_fotmob(
                    fotmob_match,
                    metrics['home_team_id'],
                    metrics['away_team_id']
                )
                metrics['shot_metrics'] = shot_metrics
                print(f"   ✅ Added xG data: Home {shot_metrics['home_xg']} | Away {shot_metrics['away_xg']}")
            else:
                print(f"   ⚠️  Fotmob data not found for match {match_id}")

            results[match_id] = metrics

            # Save individual match metrics
            output_file = output_dir / f"match_{match_id}_metrics.json"
            with open(output_file, 'w') as f:
                json.dump(metrics, f, indent=2)

            print(f"   ✅ Saved to {output_file.name}")

        except Exception as e:
            print(f"   ❌ Error: {e}")
            continue

    # Save combined metrics
    combined_file = output_dir / "all_metrics.json"
    with open(combined_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n✅ Extracted metrics for {len(results)} matches")
    print(f"📁 Saved to: {output_dir}")


if __name__ == "__main__":
    # Paths
    base_dir = Path(__file__).parent.parent
    eval_matches = base_dir / "data" / "evaluation_matches.json"
    whoscored_dir = base_dir / "data" / "raw" / "whoscored_matches" / "eredivisie" / "2025-2026"
    fotmob_file = base_dir / "data" / "raw" / "eredivisie_2025_2026_fotmob.json"
    output_dir = base_dir / "data" / "viz_metrics"

    # Run extraction
    extract_metrics_for_evaluation_matches(eval_matches, whoscored_dir, fotmob_file, output_dir)