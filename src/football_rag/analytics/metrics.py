"""Calculate tactical metrics from match events.

Simple functions extracted from visualizers.py.
"""

import pandas as pd
import numpy as np


def calculate_all_metrics(
    events_df: pd.DataFrame, fotmob_shots: list, home_team_id: int, away_team_id: int
) -> dict:
    """Calculate all tactical metrics for both teams.

    Returns dict with 38 metrics (19 per team).
    """
    # Passing & Progression (8 metrics)
    home_pp = count_progressive_passes(events_df, home_team_id)
    away_pp = count_progressive_passes(events_df, away_team_id)

    home_total = len(
        events_df[
            (events_df["team_id"] == home_team_id)
            & (events_df["type_display_name"] == "Pass")
        ]
    )
    away_total = len(
        events_df[
            (events_df["team_id"] == away_team_id)
            & (events_df["type_display_name"] == "Pass")
        ]
    )

    home_acc = calculate_pass_accuracy(events_df, home_team_id)
    away_acc = calculate_pass_accuracy(events_df, away_team_id)

    home_vert = calculate_verticality(events_df, home_team_id)
    away_vert = calculate_verticality(events_df, away_team_id)

    # Defensive Pressure (8 metrics)
    home_ppda = calculate_ppda(events_df, home_team_id, away_team_id)
    away_ppda = calculate_ppda(events_df, away_team_id, home_team_id)

    home_press = count_high_press(events_df, home_team_id)
    away_press = count_high_press(events_df, away_team_id)

    home_def_actions = count_defensive_actions(events_df, home_team_id)
    away_def_actions = count_defensive_actions(events_df, away_team_id)

    home_tackles = count_successful_tackles(events_df, home_team_id)
    away_tackles = count_successful_tackles(events_df, away_team_id)

    home_intercepts = count_interceptions(events_df, home_team_id)
    away_intercepts = count_interceptions(events_df, away_team_id)

    # Attacking (6 metrics)
    home_shots = len(
        events_df[
            (events_df["team_id"] == home_team_id)
            & events_df["type_display_name"].isin(
                ["SavedShot", "MissedShots", "ShotOnPost", "Goal"]
            )
        ]
    )
    away_shots = len(
        events_df[
            (events_df["team_id"] == away_team_id)
            & events_df["type_display_name"].isin(
                ["SavedShot", "MissedShots", "ShotOnPost", "Goal"]
            )
        ]
    )

    # xG from Fotmob (need team mapping)
    home_xg = sum(
        s.get("expectedGoals", 0) for s in fotmob_shots if s.get("is_home", False)
    )
    away_xg = sum(
        s.get("expectedGoals", 0) for s in fotmob_shots if not s.get("is_home", False)
    )

    home_sot = len(
        events_df[
            (events_df["team_id"] == home_team_id)
            & events_df["type_display_name"].isin(["SavedShot", "Goal"])
        ]
    )
    away_sot = len(
        events_df[
            (events_df["team_id"] == away_team_id)
            & events_df["type_display_name"].isin(["SavedShot", "Goal"])
        ]
    )

    # Team Positioning (8 metrics)
    home_pos = calculate_median_position(events_df, home_team_id)
    away_pos = calculate_median_position(events_df, away_team_id)

    home_def_line = calculate_defense_line(events_df, home_team_id)
    away_def_line = calculate_defense_line(events_df, away_team_id)

    home_fwd_line = calculate_forward_line(events_df, home_team_id)
    away_fwd_line = calculate_forward_line(events_df, away_team_id)

    home_compact = calculate_compactness(home_def_line, home_fwd_line)
    away_compact = calculate_compactness(away_def_line, away_fwd_line)

    # Match Context (8 metrics)
    total_passes = home_total + away_total
    home_poss = round((home_total / total_passes) * 100, 2) if total_passes else 50.0
    away_poss = round((away_total / total_passes) * 100, 2) if total_passes else 50.0

    home_tilt, away_tilt = calculate_field_tilt(events_df, home_team_id, away_team_id)

    home_clears = len(
        events_df[
            (events_df["team_id"] == home_team_id)
            & (events_df["type_display_name"] == "Clearance")
        ]
    )
    away_clears = len(
        events_df[
            (events_df["team_id"] == away_team_id)
            & (events_df["type_display_name"] == "Clearance")
        ]
    )

    home_aerials = count_successful_aerials(events_df, home_team_id)
    away_aerials = count_successful_aerials(events_df, away_team_id)

    home_fouls = len(
        events_df[
            (events_df["team_id"] == home_team_id)
            & (events_df["type_display_name"] == "Foul")
        ]
    )
    away_fouls = len(
        events_df[
            (events_df["team_id"] == away_team_id)
            & (events_df["type_display_name"] == "Foul")
        ]
    )

    home_goals = len(
        events_df[
            (events_df["team_id"] == home_team_id)
            & (events_df["type_display_name"] == "Goal")
        ]
    )
    away_goals = len(
        events_df[
            (events_df["team_id"] == away_team_id)
            & (events_df["type_display_name"] == "Goal")
        ]
    )

    return {
        # Passing & Progression
        "home_progressive_passes": home_pp,
        "away_progressive_passes": away_pp,
        "home_total_passes": home_total,
        "away_total_passes": away_total,
        "home_pass_accuracy": home_acc,
        "away_pass_accuracy": away_acc,
        "home_verticality": home_vert,
        "away_verticality": away_vert,
        # Defensive Pressure
        "home_ppda": home_ppda,
        "away_ppda": away_ppda,
        "home_high_press": home_press,
        "away_high_press": away_press,
        "home_defensive_actions": home_def_actions,
        "away_defensive_actions": away_def_actions,
        "home_tackles": home_tackles,
        "away_tackles": away_tackles,
        "home_interceptions": home_intercepts,
        "away_interceptions": away_intercepts,
        # Attacking
        "home_shots": home_shots,
        "away_shots": away_shots,
        "home_xg": round(home_xg, 2),
        "away_xg": round(away_xg, 2),
        "home_shots_on_target": home_sot,
        "away_shots_on_target": away_sot,
        "home_goals": home_goals,
        "away_goals": away_goals,
        # Positioning
        "home_position": home_pos,
        "away_position": away_pos,
        "home_defense_line": home_def_line,
        "away_defense_line": away_def_line,
        "home_forward_line": home_fwd_line,
        "away_forward_line": away_fwd_line,
        "home_compactness": home_compact,
        "away_compactness": away_compact,
        # Match Context
        "home_possession": home_poss,
        "away_possession": away_poss,
        "home_field_tilt": home_tilt,
        "away_field_tilt": away_tilt,
        "home_clearances": home_clears,
        "away_clearances": away_clears,
        "home_aerials_won": home_aerials,
        "away_aerials_won": away_aerials,
        "home_fouls": home_fouls,
        "away_fouls": away_fouls,
    }


def count_progressive_passes(df: pd.DataFrame, team_id: int) -> int:
    """Count progressive passes (moves ball ≥9.11m toward goal)."""
    team_passes = df[
        (df["team_id"] == team_id) & (df["type_display_name"] == "Pass")
    ].copy()

    if len(team_passes) == 0:
        return 0

    # Calculate distance to goal before and after pass.
    # WhoScored coordinate system: 0-100 × 0-100 (goal at x=100, y=50).
    # Threshold scaled from UEFA 9.11m × (100/105) ≈ 8.68 WhoScored units.
    team_passes["dist_before"] = np.sqrt(
        (100 - team_passes["x"]) ** 2 + (50 - team_passes["y"]) ** 2
    )
    team_passes["dist_after"] = np.sqrt(
        (100 - team_passes["end_x"]) ** 2 + (50 - team_passes["end_y"]) ** 2
    )
    team_passes["progression"] = team_passes["dist_before"] - team_passes["dist_after"]

    return len(team_passes[team_passes["progression"] >= 8.68])


def calculate_pass_accuracy(df: pd.DataFrame, team_id: int) -> float:
    """Calculate pass completion percentage."""
    team_passes = df[(df["team_id"] == team_id) & (df["type_display_name"] == "Pass")]

    if len(team_passes) == 0:
        return 0.0

    successful = len(
        team_passes[team_passes["outcome_type_display_name"] == "Successful"]
    )
    return round((successful / len(team_passes)) * 100, 2)


def calculate_verticality(df: pd.DataFrame, team_id: int) -> float:
    """Calculate pass verticality percentage (from visualizers.py)."""
    team_passes = df[
        (df["team_id"] == team_id) & (df["type_display_name"] == "Pass")
    ].copy()

    if len(team_passes) == 0:
        return 0.0

    # Calculate pass angle
    team_passes["dx"] = team_passes["end_x"] - team_passes["x"]
    team_passes["dy"] = team_passes["end_y"] - team_passes["y"]
    team_passes["angle"] = np.abs(
        np.arctan2(team_passes["dy"], team_passes["dx"]) * 180 / np.pi
    )

    valid_passes = team_passes[
        (team_passes["angle"] >= 0) & (team_passes["angle"] <= 90)
    ]

    if len(valid_passes) == 0:
        return 0.0

    median_angle = valid_passes["angle"].median()
    return round((1 - median_angle / 90) * 100, 2)


def calculate_ppda(
    df: pd.DataFrame, defending_team_id: int, attacking_team_id: int
) -> float:
    """Calculate PPDA (Passes Per Defensive Action)."""
    # Attacking team passes in their attacking 60% of field
    attacking_passes = df[
        (df["team_id"] == attacking_team_id)
        & (df["type_display_name"] == "Pass")
        & (df["x"] >= 40)  # In opponent's 60%
    ]

    # Defending team defensive actions in their defensive 60%
    defensive_actions = df[
        (df["team_id"] == defending_team_id)
        & (df["type_display_name"].isin(["Tackle", "Interception", "Foul"]))
        & (df["x"] <= 60)  # In own 60%
    ]

    if len(defensive_actions) == 0:
        return 0.0

    return round(len(attacking_passes) / len(defensive_actions), 2)


def count_high_press(df: pd.DataFrame, team_id: int) -> int:
    """Count high press events (defensive actions in opponent's final third)."""
    return len(
        df[
            (df["team_id"] == team_id)
            & (df["type_display_name"].isin(["Tackle", "Interception", "Foul"]))
            & (df["x"] >= 70)  # Final third
        ]
    )


def count_defensive_actions(df: pd.DataFrame, team_id: int) -> int:
    """Count total defensive actions."""
    return len(
        df[
            (df["team_id"] == team_id)
            & (
                df["type_display_name"].isin(
                    ["Tackle", "Interception", "Foul", "Clearance", "Aerial"]
                )
            )
        ]
    )


def count_successful_tackles(df: pd.DataFrame, team_id: int) -> int:
    """Count successful tackles."""
    tackles = df[(df["team_id"] == team_id) & (df["type_display_name"] == "Tackle")]
    return len(tackles[tackles["outcome_type_display_name"] == "Successful"])


def count_interceptions(df: pd.DataFrame, team_id: int) -> int:
    """Count interceptions."""
    return len(
        df[(df["team_id"] == team_id) & (df["type_display_name"] == "Interception")]
    )


def count_successful_aerials(df: pd.DataFrame, team_id: int) -> int:
    """Count successful aerial duels."""
    aerials = df[(df["team_id"] == team_id) & (df["type_display_name"] == "Aerial")]
    return len(aerials[aerials["outcome_type_display_name"] == "Successful"])


def calculate_median_position(df: pd.DataFrame, team_id: int) -> float:
    """Calculate team median position (x-coordinate)."""
    team_touches = df[(df["team_id"] == team_id) & df["is_touch"]]

    if len(team_touches) == 0:
        return 0.0

    return round(team_touches["x"].median(), 2)


def calculate_defense_line(df: pd.DataFrame, team_id: int) -> float:
    """Calculate defensive line position (approximation from defensive actions)."""
    defensive_actions = df[
        (df["team_id"] == team_id)
        & (df["type_display_name"].isin(["Tackle", "Interception", "Clearance"]))
    ]

    if len(defensive_actions) == 0:
        return 30.0  # Default

    # Take 25th percentile (defensive line is where most defensive actions happen)
    return round(defensive_actions["x"].quantile(0.25), 2)


def calculate_forward_line(df: pd.DataFrame, team_id: int) -> float:
    """Calculate forward line position (approximation from attacking actions)."""
    attacking_actions = df[
        (df["team_id"] == team_id)
        & (df["type_display_name"].isin(["Pass", "Shot", "Dribble"]))
        & (df["x"] >= 50)  # Opponent half
    ]

    if len(attacking_actions) == 0:
        return 70.0  # Default

    # Take 75th percentile (attacking line)
    return round(attacking_actions["x"].quantile(0.75), 2)


def calculate_compactness(defense_line: float, forward_line: float) -> float:
    """Calculate team compactness percentage."""
    if forward_line <= defense_line:
        return 100.0

    # WhoScored field length is 100 units (not StatsBomb's 120).
    return round((1 - ((forward_line - defense_line) / 100)) * 100, 2)


def calculate_field_tilt(
    df: pd.DataFrame, home_team_id: int, away_team_id: int
) -> tuple[float, float]:
    """Calculate field tilt (attacking third possession)."""
    home_touches = df[
        (df["team_id"] == home_team_id) & df["is_touch"] & (df["x"] >= 70)
    ]
    away_touches = df[
        (df["team_id"] == away_team_id) & df["is_touch"] & (df["x"] >= 70)
    ]

    total = len(home_touches) + len(away_touches)

    if total == 0:
        return 50.0, 50.0

    home_tilt = round((len(home_touches) / total) * 100, 2)
    away_tilt = round((len(away_touches) / total) * 100, 2)

    return home_tilt, away_tilt


def classify_metrics(metrics: dict) -> dict:
    """Translate raw metric values into qualitative football labels (Wordalisation).

    Converts numerical metrics into descriptive labels that describe *what the team
    did* in context — not catch-all terms. Labels follow the PMDS principle: describe
    Position, Moment, Direction, Speed of team actions rather than vague adjectives.

    Thresholds calibrated from Eredivisie 2024-25 real distributions (p25/p75).

    Args:
        metrics: Dict of raw metric values (output of calculate_all_metrics or
                 to_prompt_variables from TacticalMetrics).

    Returns:
        Flat dict of string labels suitable for prompt template interpolation.
    """

    # --- Pressing & defensive approach (PPDA: lower = more aggressive) ---
    # Eredivisie: p25=6.0, p50=7.4, p75=9.2
    def _press_style(ppda: float) -> str:
        if ppda <= 6.0:
            return "pressed_aggressively_allowing_few_passes"
        if ppda <= 9.2:
            return "moderate_press_in_mid_block"
        return "sat_deep_with_minimal_pressing"

    # High press actions in final third: p25=5, p50=6, p75=8
    def _high_press_label(count: float) -> str:
        if count >= 8:
            return "pressed_frequently_in_opponent_third"
        if count >= 5:
            return "occasional_pressing_triggers_high_up"
        return "rarely_engaged_in_opponent_third"

    # --- Attacking output ---
    def _goal_efficiency(xg: float, score: int) -> str:
        if xg <= 0:
            return "created_no_clear_chances"
        if xg > score * 2:
            return "wasted_chances_repeatedly"
        if xg > score * 1.3:
            return "slightly_wasteful_in_front_of_goal"
        if score > xg * 1.5:
            return "clinical_finishing_from_limited_chances"
        return "converted_at_expected_rate"

    # Shots: p25=12, p50=16, p75=20
    def _shot_volume(shots: float) -> str:
        if shots >= 20:
            return "generated_high_shot_volume"
        if shots >= 12:
            return "created_regular_attempts"
        return "struggled_to_create_shooting_opportunities"

    def _shot_quality(xg: float, shots: float) -> str:
        if shots == 0:
            return "no_shots_attempted"
        xg_per_shot = xg / shots
        if xg_per_shot > 0.15:
            return "found_high_quality_chances_close_to_goal"
        if xg_per_shot >= 0.08:
            return "mixed_shot_quality"
        return "forced_shots_from_difficult_positions"

    # --- Territorial & positional shape ---
    # Median position: p25=43.6, p50=47.4, p75=54.0
    def _field_position(pos: float) -> str:
        if pos >= 54.0:
            return "operated_high_up_the_pitch"
        if pos >= 43.6:
            return "held_a_central_position_on_the_pitch"
        return "sat_deep_in_own_half"

    # Defense line (p25 of def actions): p25=9.4, p50=11.1, p75=13.5
    def _defensive_line(def_line: float) -> str:
        if def_line >= 13.5:
            return "defended_with_a_high_line"
        if def_line >= 9.4:
            return "held_a_mid_block_defensive_shape"
        return "dropped_into_a_deep_block"

    # Compactness: p25=33.0, p50=35.8, p75=38.0
    def _compactness(compact: float) -> str:
        if compact >= 38.0:
            return "stretched_shape_between_lines"
        if compact >= 33.0:
            return "compact_defensive_block"
        return "very_narrow_distances_between_lines"

    # Field tilt (final third touches): p25=46.5, p50=57.7, p75=67.9
    def _field_tilt(tilt: float) -> str:
        if tilt >= 67.9:
            return "dominated_the_opponent_final_third"
        if tilt >= 46.5:
            return "shared_territorial_presence"
        return "penned_back_in_own_half"

    # Possession: data-driven
    def _possession_style(poss: float) -> str:
        if poss >= 58:
            return "controlled_possession_extensively"
        if poss >= 45:
            return "shared_possession"
        return "conceded_the_ball_played_without_it"

    # Extract values — supports both full keys (calculate_all_metrics)
    # and short keys (TacticalMetrics.to_prompt_variables)
    home_ppda = metrics.get("home_ppda", 5.0)
    away_ppda = metrics.get("away_ppda", 5.0)
    home_high_press = metrics.get("home_high_press", metrics.get("home_press", 0))
    away_high_press = metrics.get("away_high_press", metrics.get("away_press", 0))
    home_xg = metrics.get("home_xg", 0.0)
    away_xg = metrics.get("away_xg", 0.0)
    home_score = int(metrics.get("home_score", 0))
    away_score = int(metrics.get("away_score", 0))
    home_shots = metrics.get("home_shots", 0)
    away_shots = metrics.get("away_shots", 0)
    home_pos = metrics.get("home_position", metrics.get("home_pos", 50.0))
    away_pos = metrics.get("away_position", metrics.get("away_pos", 50.0))
    home_def = metrics.get("home_defense_line", metrics.get("home_def", 12.0))
    away_def = metrics.get("away_defense_line", metrics.get("away_def", 12.0))
    home_poss = metrics.get("home_possession", 50.0)
    home_pp = metrics.get("home_progressive_passes", metrics.get("home_pp", 0))
    away_pp = metrics.get("away_progressive_passes", metrics.get("away_pp", 0))
    home_compact = metrics.get("home_compactness", metrics.get("home_compact", 36.0))
    away_compact = metrics.get("away_compactness", metrics.get("away_compact", 36.0))
    home_tilt = metrics.get("home_field_tilt", metrics.get("home_tilt", 50.0))
    away_tilt = metrics.get("away_field_tilt", metrics.get("away_tilt", 50.0))

    # Press dominance: which team pressed more intensely
    ppda_diff = home_ppda - away_ppda  # negative = home pressed harder
    if abs(ppda_diff) > 2.0:
        press_dominance = (
            "home_pressed_harder_than_opponent"
            if ppda_diff < 0
            else "away_pressed_harder_than_opponent"
        )
    else:
        press_dominance = "similar_pressing_intensity"

    # Progression advantage: percentage-based (>15% relative difference)
    avg_pp = (home_pp + away_pp) / 2 if (home_pp + away_pp) > 0 else 1
    pp_diff_pct = abs(home_pp - away_pp) / avg_pp
    if pp_diff_pct > 0.15:
        progression_advantage = (
            "home_progressed_the_ball_more_effectively"
            if home_pp > away_pp
            else "away_progressed_the_ball_more_effectively"
        )
    else:
        progression_advantage = "similar_ball_progression"

    # Result fairness: did xG support the outcome?
    if home_score > away_score:
        winner_xg, loser_xg = home_xg, away_xg
    elif away_score > home_score:
        winner_xg, loser_xg = away_xg, home_xg
    else:
        winner_xg, loser_xg = None, None

    if winner_xg is None:
        result_fairness = "draw_reflected_the_balance_of_play"
    elif winner_xg >= loser_xg:
        result_fairness = "result_supported_by_chances_created"
    elif loser_xg > winner_xg * 1.5:
        result_fairness = "result_against_the_run_of_play"
    else:
        result_fairness = "tight_margins_decided_the_outcome"

    return {
        "home_press_style": _press_style(home_ppda),
        "away_press_style": _press_style(away_ppda),
        "home_high_press_label": _high_press_label(home_high_press),
        "away_high_press_label": _high_press_label(away_high_press),
        "home_goal_efficiency": _goal_efficiency(home_xg, home_score),
        "away_goal_efficiency": _goal_efficiency(away_xg, away_score),
        "home_shot_quality": _shot_quality(home_xg, home_shots),
        "away_shot_quality": _shot_quality(away_xg, away_shots),
        "home_shot_volume": _shot_volume(home_shots),
        "away_shot_volume": _shot_volume(away_shots),
        "home_field_position": _field_position(home_pos),
        "away_field_position": _field_position(away_pos),
        "home_defensive_line": _defensive_line(home_def),
        "away_defensive_line": _defensive_line(away_def),
        "home_compactness": _compactness(home_compact),
        "away_compactness": _compactness(away_compact),
        "home_territorial_dominance": _field_tilt(home_tilt),
        "away_territorial_dominance": _field_tilt(away_tilt),
        "home_possession_style": _possession_style(home_poss),
        "result_fairness": result_fairness,
        "progression_advantage": progression_advantage,
        "press_dominance": press_dominance,
    }
