"""
Simple Router Test.
Does the LLM know when to call a function?
"""
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT / "src"))

from football_rag.models.rag_pipeline import FootballRAGPipeline
from football_rag.models.generate import generate_with_llm
from football_rag import viz_tools  # <--- simple wrapper

pipeline = FootballRAGPipeline(provider="anthropic")

TOOLS = [{
    "name": "generate_dashboard",
    "description": "Generates a tactical visual report (passing network, dashboard).",
    "parameters": {"match_id": "str"}
}]

def get_intent(query):
    prompt = f"""
    User Query: "{query}"
    Available Tools: {json.dumps(TOOLS)}
    
    If the user wants a visualization/image/chart/dashboard, respond with the tool name.
    If they want text analysis, respond with "None".
    Output ONLY the string.
    """
    resp = generate_with_llm(prompt, provider="anthropic", api_key=pipeline.api_key, temperature=0)
    return resp.strip().replace('"', '')

def run_test(query):
    print(f"\nUser: '{query}'")
    
    # 1. RAG finds match
    ctx = pipeline._identify_match(query)
    if not ctx:
        print("   ❌ Match not found")
        return

    # 2. Router
    intent = get_intent(query)
    print(f"   🧠 Intent: {intent}")
    
    if intent == "generate_dashboard":
        # 3. Execution
        path = viz_tools.generate_dashboard(ctx.match_id, ctx.home_team, ctx.away_team)
        print(f"   🖼️  Image generated: {path}")

# Run
run_test("I want a visual report for Heracles vs PEC")
run_test("Analyze the pressing stats for Heracles vs PEC")