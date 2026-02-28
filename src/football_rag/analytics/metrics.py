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

    # Calculate distance to goal before and after pass
    team_passes["dist_before"] = np.sqrt(
        (105 - team_passes["x"]) ** 2 + (34 - team_passes["y"]) ** 2
    )
    team_passes["dist_after"] = np.sqrt(
        (105 - team_passes["end_x"]) ** 2 + (34 - team_passes["end_y"]) ** 2
    )
    team_passes["progression"] = team_passes["dist_before"] - team_passes["dist_after"]

    return len(team_passes[team_passes["progression"] >= 9.11])


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

    return round((1 - ((forward_line - defense_line) / 120)) * 100, 2)


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

    Converts numerical metrics into English descriptive labels before passing to the LLM.
    The LLM receives labels only — never raw numbers. This produces football language,
    not data recitation.

    Args:
        metrics: Dict of raw metric values (output of calculate_all_metrics or
                 to_prompt_variables from TacticalMetrics).

    Returns:
        Flat dict of string labels suitable for prompt template interpolation.
    """

    def _press_style(ppda: float) -> str:
        if ppda < 3.5:
            return "high_press_intensity"
        if ppda <= 5.5:
            return "mid_block_press"
        return "low_block"

    def _high_press_label(count: float) -> str:
        if count > 5:
            return "sustained_high_press"
        if count >= 2:
            return "occasional_high_press"
        return "no_high_press"

    def _goal_efficiency(xg: float, score: int) -> str:
        if xg <= 0:
            return "no_clear_chances"
        if xg > score * 2:
            return "major_wastefulness"
        if xg > score * 1.3:
            return "slight_underperformance"
        if score > xg * 1.5:
            return "clinical_finishing"
        return "normal_conversion"

    def _shot_volume(shots: float) -> str:
        if shots > 20:
            return "high_shot_volume"
        if shots >= 12:
            return "normal_volume"
        return "limited_chances"

    def _shot_quality(xg: float, shots: float) -> str:
        if shots == 0:
            return "no_shots"
        xg_per_shot = xg / shots
        if xg_per_shot > 0.15:
            return "high_quality_chances"
        if xg_per_shot >= 0.08:
            return "average_quality"
        return "low_quality_shots"

    def _field_position(pos: float) -> str:
        if pos > 55:
            return "very_advanced"
        if pos >= 45:
            return "balanced"
        return "deep_positioning"

    def _defensive_line(def_line: float) -> str:
        if def_line > 15:
            return "high_line"
        if def_line >= 10:
            return "mid_line"
        return "deep_block"

    def _possession_style(poss: float) -> str:
        if poss > 58:
            return "possession_dominance"
        if poss >= 45:
            return "balanced_possession"
        return "direct_play"

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

    # Press dominance: which team pressed more intensely
    ppda_diff = home_ppda - away_ppda  # negative = home pressed harder
    if abs(ppda_diff) > 1.5:
        press_dominance = (
            "home_press_dominance" if ppda_diff < 0 else "away_press_dominance"
        )
    else:
        press_dominance = "balanced_press"

    # Progression advantage
    pp_diff = home_pp - away_pp
    if abs(pp_diff) > 20:
        progression_advantage = "home" if pp_diff > 0 else "away"
    else:
        progression_advantage = "balanced"

    # Result fairness: did xG support the outcome?
    if home_score > away_score:
        winner_xg, loser_xg = home_xg, away_xg
    elif away_score > home_score:
        winner_xg, loser_xg = away_xg, home_xg
    else:
        winner_xg, loser_xg = None, None

    if winner_xg is None:
        result_fairness = "draw_fair"
    elif winner_xg >= loser_xg:
        result_fairness = "deserved_result"
    elif loser_xg > winner_xg * 1.5:
        result_fairness = "surprise_result"
    else:
        result_fairness = "marginal_result"

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
        "home_possession_style": _possession_style(home_poss),
        "result_fairness": result_fairness,
        "progression_advantage": progression_advantage,
        "press_dominance": press_dominance,
    }
