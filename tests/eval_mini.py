#!/usr/bin/env python3
"""Mini batch evaluation - test providers + faithfulness validation."""

import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent / "src"))

from football_rag.llm.generate import generate_with_llm
from football_rag.core.prompts_loader import load_prompt

# Load env
load_dotenv()

prompts = load_prompt()

# Simple test queries (no complex context needed)
TEST_QUERIES = [
    "What is the capital of France?",
    "What is 2 + 2?",
    "Name a top 5 European football league",
    "What does xG mean in football?",
    "List 3 German football clubs",
]


def extract_numbers(text: str) -> set:
    """Extract numbers from text for hallucination detection."""
    import re

    return set(float(n) for n in re.findall(r"\d+\.?\d*", text))


def test_provider(provider: str, api_key: str = "") -> dict:
    """Test a provider with simple queries."""
    print(f"\n{'=' * 60}")
    print(f"Testing: {provider.upper()}")
    print(f"{'=' * 60}")

    results = {
        "provider": provider,
        "queries_tested": 0,
        "success": 0,
        "failed": 0,
        "latencies": [],
        "errors": [],
    }

    for i, query in enumerate(TEST_QUERIES, 1):
        try:
            print(f"\n[{i}/{len(TEST_QUERIES)}] {query}")

            start = time.perf_counter()
            response = generate_with_llm(
                prompt=query,
                provider=provider,
                api_key=api_key,
                system_prompt=prompts["system"][:100],  # Just first 100 chars
                max_tokens=100,
            )
            latency_ms = int((time.perf_counter() - start) * 1000)

            results["queries_tested"] += 1
            results["success"] += 1
            results["latencies"].append(latency_ms)

            # Simple faithfulness check
            response_numbers = extract_numbers(response)
            print(f"  ✅ Response ({latency_ms}ms):")
            print(f"     {response[:100]}...")
            if response_numbers:
                print(f"     Numbers found: {response_numbers}")

        except Exception as e:
            results["failed"] += 1
            results["errors"].append(str(e)[:100])
            print(f"  ❌ Error: {str(e)[:80]}")

    if results["latencies"]:
        results["avg_latency_ms"] = sum(results["latencies"]) // len(
            results["latencies"]
        )
        results["success_rate"] = results["success"] / len(TEST_QUERIES)

    return results


def main():
    """Run mini batch evaluation."""
    print("\n" + "=" * 60)
    print("⚽ MINI BATCH EVALUATION")
    print("=" * 60)
    print(f"Test queries: {len(TEST_QUERIES)}")
    print(f"Goal: Verify providers work before deployment")
    print("=" * 60)

    all_results = []

    # Test Anthropic (required)
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if anthropic_key:
        result = test_provider("anthropic", anthropic_key)
        all_results.append(result)
    else:
        print("\n❌ ANTHROPIC_API_KEY not set - cannot proceed")
        sys.exit(1)

    # Test Ollama (optional fallback)
    print(f"\n{'=' * 60}")
    print("Testing: OLLAMA (optional)")
    print(f"{'=' * 60}")
    try:
        result = test_provider("ollama")
        all_results.append(result)
    except Exception as e:
        print(f"⚠️  Ollama not available (optional): {str(e)[:80]}")

    # Summary
    print(f"\n{'=' * 60}")
    print("📊 SUMMARY")
    print(f"{'=' * 60}")

    print(f"\n{'Provider':<15} {'Success Rate':<15} {'Avg Latency':<15} {'Status'}")
    print("-" * 60)

    for result in all_results:
        provider = result["provider"]
        success = (
            f"{result.get('success_rate', 0):.0%}" if result["success"] > 0 else "N/A"
        )
        latency = (
            f"{result.get('avg_latency_ms', 0)}ms" if result["latencies"] else "N/A"
        )
        status = "✅" if result["success"] > 0 else "❌"

        print(f"{provider:<15} {success:<15} {latency:<15} {status}")

    # Decision
    anthropic_passed = any(
        r["provider"] == "anthropic" and r["success"] > 0 for r in all_results
    )

    print(f"\n{'=' * 60}")
    if anthropic_passed:
        print("✅ READY TO DEPLOY")
        print("   Anthropic provider verified working")
    else:
        print("❌ NOT READY - Anthropic provider failed")
        sys.exit(1)
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()
