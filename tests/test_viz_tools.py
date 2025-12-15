#!/usr/bin/env python3
"""Test viz_tools functions to ensure visualizers integration works."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from football_rag import viz_tools


def test_dashboard():
    """Test full dashboard generation."""
    print("\n" + "="*60)
    print("TEST: generate_dashboard()")
    print("="*60)

    try:
        path = viz_tools.generate_dashboard(
            match_id="1904034",
            home_name="Heracles",
            away_name="PEC Zwolle"
        )
        print(f"✅ Dashboard saved: {path}")
        return True
    except Exception as e:
        print(f"❌ Dashboard failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_team_viz():
    """Test team-specific visualizations."""
    print("\n" + "="*60)
    print("TEST: generate_team_viz()")
    print("="*60)

    viz_types = ["passing_network", "defensive_heatmap", "progressive_passes"]
    results = []

    for viz_type in viz_types:
        try:
            path = viz_tools.generate_team_viz(
                match_id="1904034",
                team_name="Heracles",
                viz_type=viz_type
            )
            print(f"✅ {viz_type}: {path}")
            results.append(True)
        except Exception as e:
            print(f"❌ {viz_type} failed: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)

    return all(results)


def test_match_viz():
    """Test match-level visualizations."""
    print("\n" + "="*60)
    print("TEST: generate_match_viz()")
    print("="*60)

    viz_types = ["shot_map", "xt_momentum", "match_stats"]
    results = []

    for viz_type in viz_types:
        try:
            path = viz_tools.generate_match_viz(
                match_id="1904034",
                viz_type=viz_type
            )
            print(f"✅ {viz_type}: {path}")
            results.append(True)
        except Exception as e:
            print(f"❌ {viz_type} failed: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)

    return all(results)


if __name__ == "__main__":
    print("\n" + "="*60)
    print("VIZ_TOOLS INTEGRATION TEST")
    print("="*60)

    results = {
        'dashboard': test_dashboard(),
        'team_viz': test_team_viz(),
        'match_viz': test_match_viz()
    }

    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name}: {status}")

    all_passed = all(results.values())
    print("\n" + "="*60)
    if all_passed:
        print("✅ ALL TESTS PASSED")
    else:
        print("❌ SOME TESTS FAILED")
        sys.exit(1)
    print("="*60 + "\n")
