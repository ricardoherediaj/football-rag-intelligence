"""CLI test harness for the Phase 2 RAG engine.

Usage:
    uv run python scripts/test_rag.py "Analyze the Heracles vs PEC Zwolle match"
    uv run python scripts/test_rag.py "Show shot map for Ajax vs PSV"
    uv run python scripts/test_rag.py "Show dashboard for Feyenoord vs Ajax"
"""

import sys
import logging
from pathlib import Path

# Ensure project root is on the path when running as a script
sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from football_rag.orchestrator import query

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: uv run python scripts/test_rag.py \"<query>\"")
        sys.exit(1)

    user_query = sys.argv[1]
    print(f"\nQuery: {user_query}\n{'─' * 60}")

    result = query(user_query)

    if "error" in result:
        print(f"Error: {result['error']}")
        sys.exit(1)

    print(f"Match: {result.get('match_name', 'N/A')}")

    if "commentary" in result:
        print(f"\n{result['commentary']}")
    elif "chart_path" in result:
        print(f"\nChart saved: {result['chart_path']}")


if __name__ == "__main__":
    main()
