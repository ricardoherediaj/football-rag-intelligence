"""Orchestrator: single entry point for all user queries.

Routes intent → RAG pipeline (text) or viz tools (chart), returns unified response dict.
"""

import logging
from typing import Dict, Any

from football_rag.router import classify_intent
from football_rag.models.rag_pipeline import FootballRAGPipeline
from football_rag import viz_tools

logger = logging.getLogger(__name__)


def query(user_query: str, provider: str = "anthropic") -> Dict[str, Any]:
    """Process a user query end-to-end.

    Args:
        user_query: Natural language query (e.g. "Analyze Ajax vs PSV" or
                    "Show shot map for Heracles vs PEC Zwolle")
        provider: LLM provider for text queries ('anthropic', 'openai', 'gemini', 'ollama')

    Returns:
        Dict with one of:
        - {"match_id", "match_name", "commentary", "metrics_used"} for text queries
        - {"match_id", "match_name", "chart_path"} for viz queries
        - {"error": str} on failure
    """
    intent = classify_intent(user_query)
    pipeline = FootballRAGPipeline(provider=provider)

    # Text / semantic path
    if intent["tool"] is None:
        return pipeline.run(user_query)

    # Viz path — identify match first, then render
    match_ctx = pipeline._identify_match(user_query)
    if not match_ctx:
        return {"error": "Could not identify match for visualization. Please mention team names."}

    tool = intent["tool"]
    viz_type = intent["viz_type"]
    match_name = f"{match_ctx.home_team} vs {match_ctx.away_team}"

    logger.info(f"Viz request: tool={tool}, viz_type={viz_type}, match={match_name}")

    try:
        if tool == "generate_dashboard":
            chart_path = viz_tools.generate_dashboard(
                match_ctx.match_id, match_ctx.home_team, match_ctx.away_team
            )
        elif tool == "generate_team_viz":
            team_name = _extract_team(user_query, match_ctx)
            chart_path = viz_tools.generate_team_viz(match_ctx.match_id, team_name, viz_type)
        elif tool == "generate_match_viz":
            chart_path = viz_tools.generate_match_viz(match_ctx.match_id, viz_type)
        else:
            return {"error": f"Unknown viz tool: {tool}"}
    except FileNotFoundError as e:
        return {"error": f"Match data not found locally: {e}"}

    return {
        "match_id": match_ctx.match_id,
        "match_name": match_name,
        "chart_path": chart_path,
    }


def _extract_team(query: str, match_ctx) -> str:
    """Return the most likely team name from the query, defaulting to home team."""
    query_lower = query.lower()
    if match_ctx.away_team.lower() in query_lower:
        return match_ctx.away_team
    return match_ctx.home_team
