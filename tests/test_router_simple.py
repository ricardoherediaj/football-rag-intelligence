"""Simple Router Test - Keyword-based routing (no 2nd LLM call needed).

Works with ANY API key (Claude, OpenAI, Gemini) with minimal cost.
Routing is FREE (keyword matching), users only pay for RAG queries.
"""
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT / "src"))

from football_rag.models.rag_pipeline import FootballRAGPipeline
from football_rag import viz_tools

pipeline = FootballRAGPipeline(provider="anthropic")


def keyword_match(query: str) -> dict:
    """Fast keyword matching - no LLM needed, works for 90%+ of queries."""
    q = query.lower()

    # Dashboard detection
    if any(word in q for word in ['dashboard', 'full report', 'complete', 'everything', 'all viz', '3x3']):
        return {'tool': 'generate_dashboard', 'viz_type': None}

    # Team viz detection
    if any(word in q for word in ['passing', 'network', 'pass map']):
        return {'tool': 'generate_team_viz', 'viz_type': 'passing_network'}

    if any(word in q for word in ['defensive', 'defense', 'heatmap', 'pressing']):
        return {'tool': 'generate_team_viz', 'viz_type': 'defensive_heatmap'}

    if any(word in q for word in ['progressive', 'forward pass']):
        return {'tool': 'generate_team_viz', 'viz_type': 'progressive_passes'}

    # Match viz detection
    if any(word in q for word in ['shot', 'shots', 'shooting']):
        return {'tool': 'generate_match_viz', 'viz_type': 'shot_map'}

    if any(word in q for word in ['momentum', 'xt', 'threat', 'flow']):
        return {'tool': 'generate_match_viz', 'viz_type': 'xt_momentum'}

    if any(word in q for word in ['stats', 'statistics', 'comparison', 'compare']):
        return {'tool': 'generate_match_viz', 'viz_type': 'match_stats'}

    # No visualization keywords found - fallback to text
    return {'tool': None, 'viz_type': None}


def run_test(query):
    """Test query → keyword routing → execution (NO LLM calls for routing!)."""
    print(f"\n{'='*60}")
    print(f"Query: '{query}'")
    print(f"{'='*60}")

    # 1. RAG identifies match
    ctx = pipeline._identify_match(query)
    if not ctx:
        print("❌ Match not found")
        return

    print(f"✅ Match found: {ctx.match_id} ({ctx.home_team} vs {ctx.away_team})")

    # 2. Keyword-based routing (FREE - no LLM call!)
    intent = keyword_match(query)
    print(f"🎯 Routing (keyword): tool={intent['tool']}, viz_type={intent['viz_type']}")

    # 3. Execute based on intent
    if intent['tool'] == 'generate_dashboard':
        path = viz_tools.generate_dashboard(ctx.match_id, ctx.home_team, ctx.away_team)
        print(f"🖼️  Dashboard generated: {path}")

    elif intent['tool'] == 'generate_team_viz':
        # Determine team from query
        team_name = ctx.home_team if ctx.home_team.lower() in query.lower() else ctx.away_team
        path = viz_tools.generate_team_viz(ctx.match_id, team_name, intent['viz_type'])
        print(f"🖼️  {intent['viz_type']} for {team_name}: {path}")

    elif intent['tool'] == 'generate_match_viz':
        path = viz_tools.generate_match_viz(ctx.match_id, intent['viz_type'])
        print(f"🖼️  {intent['viz_type']} generated: {path}")

    elif intent['tool'] is None:
        print("📝 No visualization detected - would return text RAG response")
        print("    (Fallback: User's LLM API key used only for actual question answering)")

    else:
        print(f"⚠️  Unknown intent: {intent}")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("ROUTER TEST: Keyword-Based Routing")
    print("Cost: $0 for routing (FREE keyword matching)")
    print("User API key: Only used for RAG question answering")
    print("="*60)

    # Test dashboard
    run_test("Show me the full match report dashboard for Heracles vs PEC Zwolle")

    # Test team viz - passing network
    run_test("Show me Heracles passing network for Heracles vs PEC Zwolle")

    # Test team viz - defensive
    run_test("Show me the defensive heatmap for PEC Zwolle in Heracles vs PEC")

    # Test team viz - progressive
    run_test("Show progressive passes for Heracles")

    # Test match viz - shot map
    run_test("Show me the shot map for Heracles vs PEC Zwolle")

    # Test match viz - momentum
    run_test("Show me the xT momentum for Heracles vs PEC Zwolle")

    # Test match viz - stats
    run_test("Show me match stats for Heracles vs PEC")

    # Test text query (no viz)
    run_test("Analyze the pressing stats for Heracles vs PEC")

    # Test edge case
    run_test("What was the strategy in Heracles vs PEC?")

    print("\n" + "="*60)
    print("✅ ROUTER TESTS COMPLETE")
    print("="*60)
    print("\nCost Analysis:")
    print("  - Routing: $0.00 (keyword matching)")
    print("  - Match identification: 1 ChromaDB query (free)")
    print("  - Visualization generation: matplotlib (free)")
    print("  - Total user cost per viz request: ~$0.00")
    print("\nUser's API key only charged for:")
    print("  - Text question answering (RAG queries)")
    print("  - NOT for visualization routing")
    print("="*60 + "\n")
