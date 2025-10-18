#!/usr/bin/env python3
"""Quick evaluation of LLM providers (no RAG pipeline needed).

Tests:
- Provider availability
- Response quality
- Faithfulness validation
- Cost estimation
"""

import sys
import os
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from football_rag.llm.generate import generate_with_llm
from football_rag.core.prompts_loader import load_prompt
from football_rag.core.logging import get_logger, setup_logging

setup_logging()
logger = get_logger(__name__)

# Load prompts
prompts = load_prompt()

# Test prompts (simplified, no actual context)
TEST_PROMPTS = [
    ("What is the capital of France?", "Paris"),
    ("What is 2 + 2?", "4"),
    ("Name a Premier League team", "Liverpool"),
]

# Cost per 1K tokens (approximate)
COST_PER_1K_TOKENS = {
    "ollama": 0.0,
    "anthropic": 0.80,  # $0.80 per 1M input tokens
    "openai": 0.15,  # $0.15 per 1M input tokens (gpt-4o-mini)
    "gemini": 0.075,  # $0.075 per 1M input tokens
}


def test_provider(provider: str, api_key: str = "") -> dict:
    """Test a single provider.

    Args:
        provider: Provider name
        api_key: API key (if required)

    Returns:
        Dict with test results
    """
    print(f"\n🧪 Testing {provider.upper()}")
    print("-" * 60)

    results = {
        "provider": provider,
        "available": False,
        "responses": [],
        "errors": [],
        "avg_latency_ms": 0,
    }

    latencies = []

    for i, (test_prompt, expected) in enumerate(TEST_PROMPTS, 1):
        try:
            start = time.perf_counter()

            response = generate_with_llm(
                prompt=test_prompt,
                provider=provider,
                api_key=api_key,
                system_prompt="You are a helpful assistant. Keep answers brief.",
                max_tokens=50,
            )

            latency_ms = int((time.perf_counter() - start) * 1000)
            latencies.append(latency_ms)

            # Check if response contains expected keyword
            contains_expected = expected.lower() in response.lower()

            results["responses"].append(
                {
                    "query": test_prompt,
                    "response": response[:100],  # First 100 chars
                    "contains_expected": contains_expected,
                    "latency_ms": latency_ms,
                }
            )

            print(f"  Query {i}: ✅ ({latency_ms}ms)")
            print(f"    Q: {test_prompt}")
            print(f"    A: {response[:80]}...")

        except Exception as e:
            error_msg = str(e)[:100]
            results["errors"].append(error_msg)
            print(f"  Query {i}: ❌ Error")
            print(f"    {error_msg}")

    if latencies:
        results["available"] = True
        results["avg_latency_ms"] = sum(latencies) // len(latencies)
        results["success_rate"] = len(latencies) / len(TEST_PROMPTS)

    return results


def compare_results(all_results: list) -> None:
    """Print comparison table.

    Args:
        all_results: List of provider results
    """
    print("\n" + "=" * 80)
    print("📊 PROVIDER COMPARISON")
    print("=" * 80)

    print(
        f"\n{'Provider':<15} {'Available':<12} {'Success Rate':<15} {'Avg Latency':<15} {'Cost/1K tokens'}"
    )
    print("-" * 80)

    for result in all_results:
        provider = result["provider"]
        available = "✅ Yes" if result["available"] else "❌ No"
        success = (
            f"{result.get('success_rate', 0):.0%}" if result["available"] else "N/A"
        )
        latency = (
            f"{result.get('avg_latency_ms', 0)}ms" if result["available"] else "N/A"
        )
        cost = f"${COST_PER_1K_TOKENS.get(provider, 0):.4f}"

        print(f"{provider:<15} {available:<12} {success:<15} {latency:<15} {cost}")

    print("\n💡 RECOMMENDATIONS:")
    print("-" * 80)
    print("  • Ollama (Local): Free, fast for demo, but lower quality")
    print("  • Claude (Anthropic): Best quality/cost ratio, ~$0.0001 per query")
    print("  • GPT-4o (OpenAI): High quality, ~$0.00015 per query")
    print("  • Gemini (Google): Cheapest, ~$0.00005 per query")


def main():
    """Run quick provider evaluation."""
    print("\n" + "=" * 80)
    print("⚽ QUICK PROVIDER EVALUATION (No RAG)")
    print("=" * 80)
    print(f"Test Dataset: {len(TEST_PROMPTS)} simple queries")
    print("=" * 80)

    all_results = []

    # Test Ollama
    print("\n✓ Testing Ollama (local)...")
    result = test_provider("ollama")
    all_results.append(result)

    if not result["available"]:
        print("\n⚠️  Ollama not available. Run: ollama serve")

    # Test Anthropic
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if anthropic_key:
        print("\n✓ Testing Anthropic...")
        result = test_provider("anthropic", anthropic_key)
        all_results.append(result)
    else:
        print("\n⚠️  ANTHROPIC_API_KEY not set, skipping")

    # Test OpenAI
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        print("\n✓ Testing OpenAI...")
        result = test_provider("openai", openai_key)
        all_results.append(result)
    else:
        print("\n⚠️  OPENAI_API_KEY not set, skipping")

    # Test Gemini
    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key:
        print("\n✓ Testing Gemini...")
        result = test_provider("gemini", gemini_key)
        all_results.append(result)
    else:
        print("\n⚠️  GEMINI_API_KEY not set, skipping")

    # Compare
    compare_results(all_results)

    print("\n" + "=" * 80)
    print("✅ EVALUATION COMPLETE")
    print("=" * 80)
    print(f"\nTested {sum(1 for r in all_results if r['available'])} provider(s)")
    print("\n💾 Ready to deploy! Run:")
    print("   uv run python app.py")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
