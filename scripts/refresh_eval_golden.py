"""One-time script: replace hand-written viz_metrics in tactical_analysis_eval.json
with real values pulled from main_main.gold_match_summaries via DuckDB.

Run once:
    uv run python scripts/refresh_eval_golden.py
"""

import json
import duckdb
from pathlib import Path

EVAL_PATH = Path("data/eval_datasets/tactical_analysis_eval.json")
DB_PATH = Path("data/lakehouse.duckdb").resolve()

COLUMNS = [
    "match_id",
    "home_goals", "away_goals",
    "home_total_xg", "away_total_xg",
    "home_shots", "away_shots",
    "home_progressive_passes", "away_progressive_passes",
    "home_total_passes", "away_total_passes",
    "home_ppda", "away_ppda",
    "home_high_press", "away_high_press",
    "home_median_position", "away_median_position",
    "home_defense_line", "away_defense_line",
]


def fetch_metrics(match_ids: list[str]) -> dict[str, dict]:
    db = duckdb.connect(str(DB_PATH))
    placeholders = ",".join(f"'{m}'" for m in match_ids)
    rows = db.execute(f"""
        SELECT {', '.join(COLUMNS)}
        FROM main_main.gold_match_summaries
        WHERE match_id IN ({placeholders})
    """).fetchall()
    db.close()

    result = {}
    for row in rows:
        mid = row[0]
        result[mid] = {
            "home_score":               row[1],
            "away_score":               row[2],
            "home_xg":                  round(row[3], 3),
            "away_xg":                  round(row[4], 3),
            "home_shots":               row[5],
            "away_shots":               row[6],
            "home_progressive_passes":  row[7],
            "away_progressive_passes":  row[8],
            "home_total_passes":        row[9],
            "away_total_passes":        row[10],
            "home_ppda":                round(row[11], 2),
            "away_ppda":                round(row[12], 2),
            "home_high_press":          row[13],
            "away_high_press":          row[14],
            "home_position":            round(row[15], 2),
            "away_position":            round(row[16], 2),
            "home_defense_line":        round(row[17], 2),
            "away_defense_line":        round(row[18], 2),
        }
    return result


def main() -> None:
    data = json.loads(EVAL_PATH.read_text())
    match_ids = [c["match_id"] for c in data["test_cases"]]

    print(f"Fetching metrics for {len(match_ids)} matches from DuckDB...")
    metrics_by_id = fetch_metrics(match_ids)

    updated = 0
    for case in data["test_cases"]:
        mid = case["match_id"]
        if mid not in metrics_by_id:
            print(f"  WARNING: no data found for match_id={mid} ({case['test_id']})")
            continue
        case["viz_metrics"] = metrics_by_id[mid]
        updated += 1
        print(f"  {case['test_id']} ({mid}): score {metrics_by_id[mid]['home_score']}-{metrics_by_id[mid]['away_score']}, shots {metrics_by_id[mid]['home_shots']}/{metrics_by_id[mid]['away_shots']}")

    EVAL_PATH.write_text(json.dumps(data, indent=2))
    print(f"\nDone — {updated}/{len(match_ids)} cases updated in {EVAL_PATH}")


if __name__ == "__main__":
    main()
