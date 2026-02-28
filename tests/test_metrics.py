"""Unit tests for football_rag.analytics.metrics.

All tests use in-memory DataFrames — no DB, no network, no lakehouse.duckdb.

Marker: @pytest.mark.unit (included in default CI run)
Marker: @pytest.mark.local_data (requires lakehouse.duckdb, skipped in CI)

Run:
    uv run pytest tests/test_metrics.py -v -m unit
"""

import pytest
import pandas as pd
from football_rag.analytics.metrics import (
    calculate_compactness,
    calculate_field_tilt,
    calculate_median_position,
    calculate_pass_accuracy,
    calculate_ppda,
    classify_metrics,
    count_high_press,
    count_progressive_passes,
)

# ---------------------------------------------------------------------------
# Fixtures — synthetic events with known geometry
# ---------------------------------------------------------------------------

HOME_ID = 1
AWAY_ID = 2


def _event(
    team_id: int,
    event_type: str,
    x: float,
    y: float,
    end_x: float = None,
    end_y: float = None,
    outcome: str = "Successful",
    is_touch: bool = False,
) -> dict:
    return {
        "team_id": team_id,
        "type_display_name": event_type,
        "outcome_type_display_name": outcome,
        "x": x,
        "y": y,
        "end_x": end_x if end_x is not None else x,
        "end_y": end_y if end_y is not None else y,
        "is_touch": is_touch,
    }


@pytest.fixture
def events() -> pd.DataFrame:
    """Events with deterministic geometry for exact assertions.

    Home passes (7 successful, 3 unsuccessful = 70% accuracy, 2 progressive):
      Progressive must have progression = dist_before - dist_after >= 8.68
      Pass A: (50,50)→(90,50): dist_before=50, dist_after=10, prog=40 ✓
      Pass B: (30,50)→(80,50): dist_before=70, dist_after=20, prog=50 ✓
      Non-prog: (92,50)→(91,50): dist_before=8, dist_after=9, prog=-1 ✗
      Non-prog: (92,48)→(92,47): sideways near goal, prog≈0.02 ✗
      Non-prog: (95,50)→(94,50): prog=1 < 8.68 ✗
      Non-prog: (96,50)→(95,50): prog=1 < 8.68 ✗
      Non-prog: (97,50)→(96,50): prog=1 < 8.68 ✗

    PPDA: 6 away passes at x>=40 / 3 home def actions at x<=60 = 2.0
    High press: 3 home actions at x>=70 (Tackle@75, Interception@80, Foul@70)
    """
    rows = [
        # --- Home passes (7 successful, 3 unsuccessful = 70% accuracy) ---
        # Progressive pass A: (50,50) → (90,50). prog=40 ≥ 8.68 ✓
        _event(HOME_ID, "Pass", 50, 50, 90, 50, "Successful"),
        # Progressive pass B: (30,50) → (80,50). prog=50 ≥ 8.68 ✓
        _event(HOME_ID, "Pass", 30, 50, 80, 50, "Successful"),
        # Non-progressive: tiny backward step near goal
        _event(HOME_ID, "Pass", 92, 50, 91, 50, "Successful"),  # prog=-1
        _event(HOME_ID, "Pass", 92, 48, 92, 47, "Successful"),  # prog≈0
        _event(HOME_ID, "Pass", 95, 50, 94, 50, "Successful"),  # prog=1 < 8.68
        _event(HOME_ID, "Pass", 96, 50, 95, 50, "Successful"),  # prog=1 < 8.68
        _event(HOME_ID, "Pass", 97, 50, 96, 50, "Successful"),  # prog=1 < 8.68
        # 3 unsuccessful home passes — backward passes so they're NOT progressive
        _event(HOME_ID, "Pass", 70, 50, 50, 50, "Unsuccessful"),  # prog=-20 ✗
        _event(HOME_ID, "Pass", 80, 40, 60, 40, "Unsuccessful"),  # prog<0 ✗
        _event(HOME_ID, "Pass", 50, 30, 30, 30, "Unsuccessful"),  # prog<0 ✗
        # --- Away passes (6 at x>=40 for PPDA zone, 2 at x<40 outside zone) ---
        _event(AWAY_ID, "Pass", 45, 50, 55, 50, "Successful"),
        _event(AWAY_ID, "Pass", 50, 50, 60, 50, "Successful"),
        _event(AWAY_ID, "Pass", 55, 50, 65, 50, "Successful"),
        _event(AWAY_ID, "Pass", 60, 50, 70, 50, "Successful"),
        _event(AWAY_ID, "Pass", 65, 50, 75, 50, "Successful"),
        _event(AWAY_ID, "Pass", 70, 50, 80, 50, "Successful"),
        # Outside PPDA zone (x < 40) — NOT counted for PPDA numerator
        _event(AWAY_ID, "Pass", 35, 50, 45, 50, "Successful"),
        _event(AWAY_ID, "Pass", 20, 50, 30, 50, "Successful"),
        # --- Home defensive actions (PPDA denominator: at x<=60) ---
        _event(HOME_ID, "Tackle", 30, 50, outcome="Successful"),  # in zone ✓
        _event(HOME_ID, "Interception", 40, 50),  # in zone ✓
        _event(HOME_ID, "Foul", 50, 50),  # in zone ✓
        # High press: home actions at x>=70
        _event(HOME_ID, "Tackle", 75, 50, outcome="Successful"),  # high press ✓
        _event(HOME_ID, "Interception", 80, 50),  # high press ✓
        _event(HOME_ID, "Foul", 70, 50),  # high press (boundary) ✓
        # Action at x=69 — NOT in high press zone
        _event(HOME_ID, "Tackle", 69, 50, outcome="Successful"),
        # --- Shots ---
        _event(HOME_ID, "SavedShot", 90, 50),  # on target
        _event(HOME_ID, "Goal", 92, 48),  # on target
        _event(HOME_ID, "ShotOnPost", 91, 50),  # NOT on target (ShotOnPost excluded)
        _event(AWAY_ID, "MissedShots", 85, 50),  # away shot
        # --- Touches (is_touch=True) for field tilt / median position ---
        # Use type "Dribble" so they don't pollute pass counts
        _event(HOME_ID, "Dribble", 72, 50, is_touch=True),  # x>=70: tilt zone ✓
        _event(HOME_ID, "Dribble", 75, 50, is_touch=True),  # x>=70: tilt zone ✓
        _event(HOME_ID, "Dribble", 65, 50, is_touch=True),  # x<70: NOT in tilt zone
        _event(AWAY_ID, "Dribble", 71, 50, is_touch=True),  # away touch in tilt zone ✓
        _event(HOME_ID, "Dribble", 50, 50, is_touch=True),  # median position reference
    ]
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Progressive passes — coordinate system (Bug A fix)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_progressive_passes_uses_whoscored_coords(events):
    """Discriminator pass: progressive only on WhoScored (100,50) goal, not (105,34)."""
    # Add a pass from (80,1) → (80,49):
    # NEW coords: before=sqrt(400+2401)≈52.9, after=sqrt(400+1)≈20.02, prog=32.9 ✓
    # OLD coords: before=sqrt(625+1089)≈41.4, after=sqrt(625+441)≈32.7, prog=8.7 < 9.11 ✗
    discriminator = pd.DataFrame([_event(HOME_ID, "Pass", 80, 1, 80, 49, "Successful")])
    combined = pd.concat([events, discriminator], ignore_index=True)
    result = count_progressive_passes(combined, HOME_ID)
    # Fixture has 2 progressive + discriminator = 3
    assert result == 3


@pytest.mark.unit
def test_progressive_passes_count(events):
    """Exactly 2 progressive home passes in base fixture."""
    assert count_progressive_passes(events, HOME_ID) == 2


@pytest.mark.unit
def test_progressive_passes_threshold_boundary():
    """Pass with progression just below 8.68 is NOT counted."""
    # dist_before=10.0, dist_after=1.33, prog=8.67 < 8.68 → not counted
    df = pd.DataFrame([_event(HOME_ID, "Pass", 90, 50, 98.67, 50, "Successful")])
    assert count_progressive_passes(df, HOME_ID) == 0


# ---------------------------------------------------------------------------
# Pass accuracy
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_pass_accuracy_exact(events):
    """7 successful / 10 total home passes = 70.0%."""
    assert calculate_pass_accuracy(events, HOME_ID) == 70.0


@pytest.mark.unit
def test_pass_accuracy_empty():
    df = pd.DataFrame(
        columns=[
            "team_id",
            "type_display_name",
            "outcome_type_display_name",
            "x",
            "y",
            "end_x",
            "end_y",
            "is_touch",
        ]
    )
    assert calculate_pass_accuracy(df, HOME_ID) == 0.0


# ---------------------------------------------------------------------------
# PPDA — zone filter (x>=40 numerator, x<=60 denominator)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_ppda_correct_ratio(events):
    """6 away passes at x>=40 / 3 home defensive actions at x<=60 = 2.0."""
    # Away passes at x>=40: rows 45,50,55,60,65,70 → 6
    # Home def actions at x<=60: Tackle@30, Interception@40, Foul@50 → 3
    result = calculate_ppda(events, HOME_ID, AWAY_ID)
    assert result == pytest.approx(2.0, rel=0.01)


@pytest.mark.unit
def test_ppda_zone_filter_excludes_out_of_zone_passes(events):
    """Away passes at x<40 must NOT count in PPDA numerator."""
    # Remove in-zone away passes, leave only x<40 passes
    out_of_zone = events[
        ~(
            (events["team_id"] == AWAY_ID)
            & (events["type_display_name"] == "Pass")
            & (events["x"] >= 40)
        )
    ]
    # Still has 3 home defensive actions in zone → denominator=3
    # But 0 away passes in zone → ratio=0
    result = calculate_ppda(out_of_zone, HOME_ID, AWAY_ID)
    assert result == 0.0


@pytest.mark.unit
def test_ppda_no_defensive_actions_returns_zero():
    df = pd.DataFrame([_event(AWAY_ID, "Pass", 55, 50, 65, 50)])
    assert calculate_ppda(df, HOME_ID, AWAY_ID) == 0.0


# ---------------------------------------------------------------------------
# High press — zone boundary at x>=70
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_high_press_count(events):
    """3 home actions at x>=70: Tackle@75, Interception@80, Foul@70 (boundary)."""
    assert count_high_press(events, HOME_ID) == 3


@pytest.mark.unit
def test_high_press_zone_boundary():
    """Action at x=69 NOT counted; x=70 IS counted."""
    df = pd.DataFrame(
        [
            _event(HOME_ID, "Tackle", 69, 50),
            _event(HOME_ID, "Tackle", 70, 50),
        ]
    )
    assert count_high_press(df, HOME_ID) == 1


# ---------------------------------------------------------------------------
# Field tilt — zone at x>=70 (Bug: old dbt used x>=50)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_field_tilt_sums_to_100(events):
    home_tilt, away_tilt = calculate_field_tilt(events, HOME_ID, AWAY_ID)
    assert abs(home_tilt + away_tilt - 100.0) < 0.01


@pytest.mark.unit
def test_field_tilt_zone_is_x70_not_x50(events):
    """Touch at x=65 must NOT count in field tilt (only x>=70 does)."""
    # In fixture: home has 2 touches at x>=70 (72, 75), away has 1 (71), plus x=65 excluded
    home_tilt, away_tilt = calculate_field_tilt(events, HOME_ID, AWAY_ID)
    # home=2, away=1 → home_tilt=66.67%
    assert home_tilt == pytest.approx(66.67, rel=0.01)
    assert away_tilt == pytest.approx(33.33, rel=0.01)


# ---------------------------------------------------------------------------
# Median position
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_median_position_uses_is_touch_flag(events):
    """calculate_median_position uses is_touch=True rows only."""
    # Home touches: x=72, 75, 65, 50 → median=68.5
    result = calculate_median_position(events, HOME_ID)
    assert result == pytest.approx(68.5, rel=0.01)


# ---------------------------------------------------------------------------
# Compactness divisor — Bug B fix (was 120, now 100)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_compactness_uses_100_divisor():
    """forward=80, defense=20 → (1-60/100)*100 = 40.0."""
    assert calculate_compactness(20.0, 80.0) == pytest.approx(40.0)


@pytest.mark.unit
def test_compactness_old_divisor_would_be_wrong():
    """Guard: old divisor 120 would give 50.0, not 40.0."""
    assert calculate_compactness(20.0, 80.0) != pytest.approx(50.0)


@pytest.mark.unit
def test_compactness_inverted_returns_100():
    """If forward_line <= defense_line, compactness = 100.0."""
    assert calculate_compactness(50.0, 30.0) == 100.0


# ---------------------------------------------------------------------------
# classify_metrics — all string output, label correctness
# ---------------------------------------------------------------------------

_BASE_METRICS = {
    "home_ppda": 3.2,
    "away_ppda": 5.8,
    "home_high_press": 6,
    "away_high_press": 1,
    "home_xg": 1.5,
    "away_xg": 0.4,
    "home_score": 2,
    "away_score": 0,
    "home_shots": 18,
    "away_shots": 8,
    "home_position": 57.0,
    "away_position": 43.0,
    "home_defense_line": 16.0,
    "away_defense_line": 9.0,
    "home_possession": 62.0,
    "home_progressive_passes": 35,
    "away_progressive_passes": 12,
    "home_compactness": 36.0,
    "away_compactness": 34.0,
    "home_field_tilt": 65.0,
    "away_field_tilt": 35.0,
}


@pytest.mark.unit
def test_classify_metrics_all_strings():
    """Every value returned by classify_metrics must be a str (no floats)."""
    result = classify_metrics(_BASE_METRICS)
    for k, v in result.items():
        assert isinstance(v, str), f"classify_metrics[{k}] is {type(v)}, expected str"


@pytest.mark.unit
def test_classify_metrics_ppda_labels():
    base = {**_BASE_METRICS}

    base["home_ppda"] = 3.0
    assert (
        classify_metrics(base)["home_press_style"]
        == "pressed_aggressively_allowing_few_passes"
    )

    base["home_ppda"] = 7.0
    assert classify_metrics(base)["home_press_style"] == "moderate_press_in_mid_block"

    base["home_ppda"] = 10.0
    assert (
        classify_metrics(base)["home_press_style"] == "sat_deep_with_minimal_pressing"
    )


@pytest.mark.unit
def test_classify_metrics_shot_volume():
    base = {**_BASE_METRICS}

    base["home_shots"] = 25
    assert classify_metrics(base)["home_shot_volume"] == "generated_high_shot_volume"

    base["home_shots"] = 15
    assert classify_metrics(base)["home_shot_volume"] == "created_regular_attempts"

    base["home_shots"] = 8
    assert (
        classify_metrics(base)["home_shot_volume"]
        == "struggled_to_create_shooting_opportunities"
    )


@pytest.mark.unit
def test_classify_metrics_accepts_short_keys():
    """Short keys (home_pp, home_press) from to_prompt_variables must work too."""
    short_metrics = {
        "home_ppda": 3.2,
        "away_ppda": 5.8,
        "home_press": 6,  # short key
        "away_press": 1,  # short key
        "home_xg": 1.5,
        "away_xg": 0.4,
        "home_score": 2,
        "away_score": 0,
        "home_shots": 18,
        "away_shots": 8,
        "home_pos": 57.0,  # short key
        "away_pos": 43.0,  # short key
        "home_def": 16.0,  # short key
        "away_def": 9.0,  # short key
        "home_possession": 62.0,
        "home_pp": 35,  # short key
        "away_pp": 12,  # short key
        "home_compact": 36.0,  # short key
        "away_compact": 34.0,  # short key
        "home_tilt": 65.0,  # short key
        "away_tilt": 35.0,  # short key
    }
    result = classify_metrics(short_metrics)
    for k, v in result.items():
        assert isinstance(v, str), f"classify_metrics[{k}] = {v!r} is not str"


# ---------------------------------------------------------------------------
# Range guard tests — require real lakehouse.duckdb (local_data marker)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def real_gold_summaries():
    """Load gold_match_summaries from local lakehouse.duckdb for range checks."""
    import duckdb

    db_path = "data/lakehouse.duckdb"
    try:
        con = duckdb.connect(db_path, read_only=True)
        con.execute("INSTALL vss; LOAD vss;")
        df = con.execute("SELECT * FROM gold_match_summaries").df()
        con.close()
        return df
    except Exception as e:
        pytest.skip(f"Cannot load lakehouse.duckdb: {e}")


@pytest.mark.local_data
def test_progressive_passes_range_post_fix(real_gold_summaries):
    """Post-fix: home_progressive_passes p50 should be 15-60, not 100+."""
    p50 = real_gold_summaries["home_progressive_passes"].quantile(0.5)
    assert p50 > 10, f"p50 progressive passes too low: {p50:.1f}"
    assert p50 < 80, (
        f"p50 progressive passes still inflated: {p50:.1f} (was ~154 pre-fix)"
    )


@pytest.mark.local_data
def test_ppda_plausible_range(real_gold_summaries):
    """PPDA should be 1.5–15 for all matches (industry standard range)."""
    col = real_gold_summaries["home_ppda"].dropna()
    assert col.between(1.5, 15).all(), (
        f"PPDA out of range: min={col.min():.2f}, max={col.max():.2f}"
    )


@pytest.mark.local_data
def test_high_press_plausible_range(real_gold_summaries):
    """High press count should be 0–30 per team per match."""
    col = real_gold_summaries["home_high_press"].dropna()
    assert col.between(0, 30).all(), (
        f"High press out of range: min={col.min()}, max={col.max()}"
    )
