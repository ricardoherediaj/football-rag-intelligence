"""Query router for Football RAG Intelligence.

Routes user queries to either:
1. Text analysis (LLM generation)
2. Visualizations (keyword-based, $0 cost)
"""

from typing import Dict, Optional


def classify_intent(query: str) -> Dict[str, Optional[str]]:
    """Classify user intent from query.

    Priority:
    1. Questions (What/How/Why) → Text analysis
    2. Explicit viz commands (Show/Display) → Visualization
    3. Default → Text analysis

    Args:
        query: User's natural language query

    Returns:
        Dict with 'tool' and 'viz_type' keys
        - tool: None (text), 'generate_dashboard', 'generate_team_viz', 'generate_match_viz'
        - viz_type: None or specific viz type (e.g., 'shot_map')
    """
    q = query.lower()

    # Priority 1: Analysis questions
    is_question = any(
        q.startswith(word)
        for word in ['what', 'how', 'why', 'explain', 'analyze', 'describe']
    )

    if is_question:
        return {'tool': None, 'viz_type': None}

    # Priority 2: Dashboard (highest viz priority)
    if any(word in q for word in ['dashboard', 'full report', 'complete', 'everything', 'all viz', '3x3']):
        return {'tool': 'generate_dashboard', 'viz_type': None}

    # Priority 3: Explicit viz commands
    has_viz_command = any(cmd in q for cmd in ['show', 'display', 'generate', 'create'])

    if has_viz_command:
        # Team visualizations
        if any(word in q for word in ['passing', 'network', 'pass map']):
            return {'tool': 'generate_team_viz', 'viz_type': 'passing_network'}

        if any(word in q for word in ['defensive', 'defense', 'heatmap']):
            return {'tool': 'generate_team_viz', 'viz_type': 'defensive_heatmap'}

        if any(word in q for word in ['progressive', 'forward pass']):
            return {'tool': 'generate_team_viz', 'viz_type': 'progressive_passes'}

        # Match visualizations
        if any(word in q for word in ['shot', 'shots', 'shooting']):
            return {'tool': 'generate_match_viz', 'viz_type': 'shot_map'}

        if any(word in q for word in ['momentum', 'xt', 'threat', 'flow']):
            return {'tool': 'generate_match_viz', 'viz_type': 'xt_momentum'}

        if any(word in q for word in ['stats', 'statistics', 'comparison', 'compare']):
            return {'tool': 'generate_match_viz', 'viz_type': 'match_stats'}

    # Default: text analysis
    return {'tool': None, 'viz_type': None}
