"""Tactical interpretation rules extracted from visualizers.py.

These thresholds are derived from reverse-engineering our own visualization code.
No external sources needed - these are OUR definitions based on what we see in plots.

Author: Football RAG Team
Created: October 4, 2025
"""

from typing import Dict, Any


def interpret_verticality(verticality: float) -> str:
    """Interpret passing verticality based on passing network visualization.

    Formula (from visualizers.py line 134-135):
        verticality = (1 - median_angle/90) * 100

    Visual thresholds:
        >50%: Mostly vertical/diagonal lines pointing forward
        35-50%: Mix of diagonal and some horizontal connections
        <35%: Predominantly horizontal/sideways lines

    Args:
        verticality: Verticality percentage (0-100)

    Returns:
        Tactical interpretation string
    """
    if verticality > 50:
        return "direct vertical passing - quick transitions to attack"
    elif verticality > 35:
        return "balanced build-up with vertical intent"
    else:
        return "patient possession-based build-up"


def interpret_defensive_line(defense_line: float) -> str:
    """Interpret defensive line position based on heatmap visualization.

    Formula (from visualizers.py line 138-139):
        defense_line = center_backs['x_avg'].median()

    Visual thresholds (StatsBomb pitch: 0-120m):
        >55m: Line clearly in opponent half
        48-55m: Around midfield area
        <48m: Own half

    Args:
        defense_line: Defensive line position in meters (0-120)

    Returns:
        Tactical interpretation string
    """
    if defense_line > 55:
        return "high defensive line - aggressive pressing"
    elif defense_line > 48:
        return "mid-block positioning"
    else:
        return "deep defensive block - reactive approach"


def interpret_shot_quality(xg_per_shot: float) -> str:
    """Interpret shot quality based on shot map visualization.

    Visual thresholds (from dot sizes in shot map):
        >0.15: Mostly large dots (high xG), clustered in box
        0.10-0.15: Mix of dot sizes
        <0.10: Mostly small dots (speculative), outside box

    Args:
        xg_per_shot: Expected goals per shot ratio

    Returns:
        Tactical interpretation string
    """
    if xg_per_shot > 0.15:
        return "creating high-quality chances from dangerous positions"
    elif xg_per_shot > 0.10:
        return "generating decent opportunities"
    else:
        return "low-quality attempts - mostly from distance"


def interpret_possession(possession_pct: float) -> str:
    """Interpret possession dominance based on match stats visualization.

    Visual thresholds (from bidirectional bars):
        >60%: Bar extends >60% toward one side
        45-60%: Bar slightly favors one side
        <45%: Bar heavily toward opponent

    Args:
        possession_pct: Possession percentage (0-100)

    Returns:
        Tactical interpretation string
    """
    if possession_pct > 60:
        return "dominated possession"
    elif possession_pct > 45:
        return "controlled possession"
    else:
        return "limited possession"


def interpret_compactness(compactness: float) -> str:
    """Interpret team compactness based on formation shape visualization.

    Formula (from visualizers.py line 142-147):
        compactness = (1 - ((forward_line - defense_line) / 120)) * 100

    Visual thresholds (from shaded area width):
        >65%: Narrow shaded area (tight formation)
        50-65%: Moderate shading
        <50%: Wide shaded area (gaps exploitable)

    Args:
        compactness: Compactness percentage (0-100)

    Returns:
        Tactical interpretation string
    """
    if compactness > 65:
        return "highly compact defensive structure"
    elif compactness > 50:
        return "balanced team shape"
    else:
        return "stretched formation - gaps exploitable"


def interpret_field_tilt(field_tilt: float) -> str:
    """Interpret field tilt (territorial control) based on touch locations.

    Args:
        field_tilt: Percentage of touches in attacking third (0-100)

    Returns:
        Tactical interpretation string
    """
    if field_tilt > 40:
        return "high territorial control in attacking third"
    elif field_tilt > 30:
        return "balanced territorial distribution"
    else:
        return "limited attacking third presence"


def generate_tactical_summary(stats: Dict[str, Any]) -> str:
    """Generate complete tactical summary from stats.

    Args:
        stats: Dictionary with tactical metrics:
            - verticality: float
            - defense_line: float (optional)
            - xg_per_shot: float
            - possession: float
            - compactness: float (optional)
            - field_tilt: float (optional)

    Returns:
        Tactical summary string combining all interpretations
    """
    interpretations = []

    # Core metrics (always present)
    if 'verticality' in stats:
        style = interpret_verticality(stats['verticality'])
        interpretations.append(f"Used {style}")

    if 'xg_per_shot' in stats:
        quality = interpret_shot_quality(stats['xg_per_shot'])
        interpretations.append(f"{quality}")

    if 'possession' in stats:
        poss = interpret_possession(stats['possession'])
        interpretations.append(f"{poss}")

    # Optional metrics
    if 'defense_line' in stats:
        defense = interpret_defensive_line(stats['defense_line'])
        interpretations.append(f"with {defense}")

    if 'compactness' in stats:
        compact = interpret_compactness(stats['compactness'])
        interpretations.append(f"maintaining {compact}")

    # Combine with proper punctuation
    if len(interpretations) == 0:
        return "No tactical data available"

    summary = interpretations[0]
    if len(interpretations) > 1:
        summary += ", " + ", ".join(interpretations[1:])

    return summary + "."


def validate_thresholds_match_viz(stats: Dict[str, Any]) -> Dict[str, bool]:
    """Validate that interpretations would match visual appearance.

    This is a helper for testing - ensures our thresholds align with
    what we would see in the actual visualizations.

    Args:
        stats: Dictionary with tactical metrics

    Returns:
        Dictionary of validation checks (all should be True)
    """
    checks = {}

    # Verticality check
    if 'verticality' in stats:
        vert = stats['verticality']
        interpretation = interpret_verticality(vert)

        # Check interpretation matches expected visual
        if vert > 50:
            checks['verticality_visual'] = 'direct' in interpretation
        elif vert > 35:
            checks['verticality_visual'] = 'balanced' in interpretation
        else:
            checks['verticality_visual'] = 'possession' in interpretation

    # Defensive line check
    if 'defense_line' in stats:
        def_line = stats['defense_line']
        interpretation = interpret_defensive_line(def_line)

        if def_line > 55:
            checks['defense_visual'] = 'high' in interpretation or 'aggressive' in interpretation
        elif def_line > 48:
            checks['defense_visual'] = 'mid' in interpretation
        else:
            checks['defense_visual'] = 'deep' in interpretation

    # Shot quality check
    if 'xg_per_shot' in stats:
        xg = stats['xg_per_shot']
        interpretation = interpret_shot_quality(xg)

        if xg > 0.15:
            checks['shot_quality_visual'] = 'high-quality' in interpretation
        elif xg > 0.10:
            checks['shot_quality_visual'] = 'decent' in interpretation
        else:
            checks['shot_quality_visual'] = 'low-quality' in interpretation

    return checks
