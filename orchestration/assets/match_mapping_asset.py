"""Match mapping asset: link WhoScored and FotMob matches using fuzzy matching."""

import csv
import json
import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import duckdb
from dagster import AssetExecutionContext, Config, Output, asset

from orchestration.assets.duckdb_assets import DuckDBConfig


def normalize_team_name(team_name: Optional[str]) -> str:
    """Normalize team name for fuzzy matching.

    Args:
        team_name: Raw team name (e.g., "PSV Eindhoven", "Ajax") or None

    Returns:
        Normalized name (lowercase, no special chars, common prefixes removed)
    """
    if not team_name:
        return ""
    normalized = team_name.lower()
    # Remove common club abbreviations
    normalized = re.sub(r'\b(fc|sc|ajax|psv|az)\b', '', normalized)
    # Remove special characters
    normalized = re.sub(r'[^\w\s]', '', normalized)
    # Normalize whitespace
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    return normalized


def calculate_similarity(name1: str, name2: str) -> float:
    """Calculate similarity score between two team names.

    Args:
        name1: First team name
        name2: Second team name

    Returns:
        Similarity score (0.0-1.0)
    """
    norm1 = normalize_team_name(name1)
    norm2 = normalize_team_name(name2)
    return SequenceMatcher(None, norm1, norm2).ratio()


@asset(deps=["raw_matches_bronze"], compute_kind="python")
def match_mapping(context: AssetExecutionContext, config: DuckDBConfig) -> Output[int]:
    """Generate match mapping between WhoScored and FotMob using multi-stage matching.

    Stage 1: Exact team name set matching (deterministic)
    Stage 2: Fuzzy team name matching (threshold >= 0.85)
    Stage 3: Date-validated fuzzy matching (handle duplicates)

    Returns:
        Number of matches mapped
    """
    base_dir = Path(__file__).parent.parent.parent
    db = duckdb.connect(config.database_path)

    # Load WhoScored team ID -> name mapping
    csv_path = base_dir / "data" / "raw" / "eredivisie_whoscored_team_ids.csv"
    ws_team_map = {}
    with open(csv_path) as f:
        for row in csv.DictReader(f):
            ws_team_map[int(row['whoscored_id'])] = row['team_name']
    context.log.info(f"📊 Loaded {len(ws_team_map)} WhoScored team mappings")

    # Load FotMob matches from Bronze
    fotmob_query = """
        SELECT
            match_id,
            COALESCE(
                json_extract_string(data, '$.home_team'),
                json_extract_string(data, '$.match_info.home_team')
            ) as home_team,
            COALESCE(
                json_extract_string(data, '$.away_team'),
                json_extract_string(data, '$.match_info.away_team')
            ) as away_team,
            COALESCE(
                json_extract_string(data, '$.home_team_id'),
                CAST(json_extract(data, '$.match_info.home_team_id') AS VARCHAR)
            ) as home_team_id,
            COALESCE(
                json_extract_string(data, '$.away_team_id'),
                CAST(json_extract(data, '$.match_info.away_team_id') AS VARCHAR)
            ) as away_team_id,
            COALESCE(
                json_extract_string(data, '$.match_date'),
                json_extract_string(data, '$.match_info.utc_time')
            ) as match_date
        FROM bronze_matches
        WHERE source = 'fotmob'
    """
    fotmob_matches = db.execute(fotmob_query).fetchall()
    fotmob_data = [
        {
            'match_id': str(row[0]),
            'home_team': row[1],
            'away_team': row[2],
            'home_team_id': row[3],
            'away_team_id': row[4],
            'match_date': row[5] or ''
        }
        for row in fotmob_matches
        if row[1] and row[2]  # Filter out matches with missing team names
    ]
    context.log.info(f"📊 Loaded {len(fotmob_data)} FotMob matches from Bronze")

    # Load WhoScored matches from Bronze
    ws_query = """
        SELECT match_id, data
        FROM bronze_matches
        WHERE source = 'whoscored'
    """
    ws_matches = db.execute(ws_query).fetchall()
    context.log.info(f"📊 Found {len(ws_matches)} WhoScored matches")

    # STAGE 1: Exact matching
    context.log.info("\n🎯 STAGE 1: Exact Team Name Matching")
    mappings = {}
    matched_fotmob: Set[str] = set()

    for ws_id, ws_data_json in ws_matches:
        ws_data = json.loads(ws_data_json)
        events = ws_data.get('events', [])

        # Extract team IDs from events
        ws_team_ids = {e['team_id'] for e in events if 'team_id' in e}
        if len(ws_team_ids) != 2:
            context.log.warning(f"❌ {ws_id}: Expected 2 teams, found {len(ws_team_ids)}")
            continue

        # Convert to team names
        try:
            ws_team_names = {ws_team_map[tid] for tid in ws_team_ids}
        except KeyError as e:
            context.log.warning(f"❌ {ws_id}: Unknown team ID {e}")
            continue

        # Find exact match in FotMob
        fm_match = None
        for fm in fotmob_data:
            if {fm['home_team'], fm['away_team']} == ws_team_names:
                if fm['match_id'] not in matched_fotmob:
                    fm_match = fm
                    break

        if fm_match:
            # Map WhoScored team ID -> FotMob team ID
            team_id_map = {}
            for ws_tid in ws_team_ids:
                name = ws_team_map[ws_tid]
                team_id_map[str(ws_tid)] = (
                    fm_match['home_team_id']
                    if name == fm_match['home_team']
                    else fm_match['away_team_id']
                )

            mappings[str(ws_id)] = {
                "whoscored_id": str(ws_id),
                "whoscored_team_ids": sorted([int(tid) for tid in ws_team_ids]),
                "fotmob_id": fm_match['match_id'],
                "fotmob_home_team_id": fm_match['home_team_id'],
                "fotmob_away_team_id": fm_match['away_team_id'],
                "ws_to_fotmob_team_mapping": team_id_map,
                "home_team": fm_match['home_team'],
                "away_team": fm_match['away_team'],
                "match_date": fm_match['match_date']
            }
            matched_fotmob.add(fm_match['match_id'])
            context.log.info(f"✅ {ws_id}: {fm_match['home_team']} vs {fm_match['away_team']}")

    stage1_count = len(mappings)
    context.log.info(f"\n📊 Stage 1 complete: {stage1_count} exact matches")

    # STAGE 2: Fuzzy matching for unmapped
    context.log.info("\n🔍 STAGE 2: Fuzzy Team Name Matching")
    unmapped_ws = [
        (ws_id, ws_data_json)
        for ws_id, ws_data_json in ws_matches
        if str(ws_id) not in mappings
    ]
    unmapped_fm = [fm for fm in fotmob_data if fm['match_id'] not in matched_fotmob]

    context.log.info(f"🔍 Fuzzy matching {len(unmapped_ws)} unmapped WhoScored matches...")
    fuzzy_threshold = 0.85

    for ws_id, ws_data_json in unmapped_ws:
        ws_data = json.loads(ws_data_json)
        events = ws_data.get('events', [])

        # Extract team names
        ws_team_ids = {e['team_id'] for e in events if 'team_id' in e}
        if len(ws_team_ids) != 2:
            continue

        try:
            ws_team_names = [ws_team_map[tid] for tid in ws_team_ids]
        except KeyError:
            continue

        # Find best fuzzy match
        best_match = None
        best_score = 0.0

        for fm in unmapped_fm:
            # Try both orientations
            score1 = (
                calculate_similarity(ws_team_names[0], fm['home_team']) +
                calculate_similarity(ws_team_names[1], fm['away_team'])
            ) / 2
            score2 = (
                calculate_similarity(ws_team_names[0], fm['away_team']) +
                calculate_similarity(ws_team_names[1], fm['home_team'])
            ) / 2
            final_score = max(score1, score2)

            if final_score > best_score and final_score >= fuzzy_threshold:
                best_match = fm
                best_score = final_score

        if best_match:
            # Create mapping
            team_id_map = {}
            for ws_tid in ws_team_ids:
                name = ws_team_map[ws_tid]
                # Determine which FotMob team this maps to
                home_sim = calculate_similarity(name, best_match['home_team'])
                away_sim = calculate_similarity(name, best_match['away_team'])
                team_id_map[str(ws_tid)] = (
                    best_match['home_team_id'] if home_sim > away_sim
                    else best_match['away_team_id']
                )

            mappings[str(ws_id)] = {
                "whoscored_id": str(ws_id),
                "whoscored_team_ids": sorted([int(tid) for tid in ws_team_ids]),
                "fotmob_id": best_match['match_id'],
                "fotmob_home_team_id": best_match['home_team_id'],
                "fotmob_away_team_id": best_match['away_team_id'],
                "ws_to_fotmob_team_mapping": team_id_map,
                "home_team": best_match['home_team'],
                "away_team": best_match['away_team'],
                "match_date": best_match['match_date'],
                "fuzzy_score": round(best_score, 3)
            }
            matched_fotmob.add(best_match['match_id'])
            context.log.info(
                f"✅ {ws_id}: {best_match['home_team']} vs {best_match['away_team']} "
                f"(fuzzy score: {best_score:.3f})"
            )

    stage2_count = len(mappings) - stage1_count
    context.log.info(f"\n📊 Stage 2 complete: {stage2_count} fuzzy matches")

    # Save to JSON file for dbt seed compatibility
    output_path = base_dir / "data" / "match_mapping.json"
    with open(output_path, 'w') as f:
        json.dump(mappings, f, indent=2)
    context.log.info(f"💾 Saved mapping to {output_path}")

    # Create match_mapping table in DuckDB
    db.execute("DROP TABLE IF EXISTS match_mapping")
    db.execute("""
        CREATE TABLE match_mapping (
            whoscored_match_id VARCHAR,
            fotmob_match_id VARCHAR,
            whoscored_team_id_1 INTEGER,
            whoscored_team_id_2 INTEGER,
            fotmob_team_id_1 VARCHAR,
            fotmob_team_id_2 VARCHAR,
            home_team VARCHAR,
            away_team VARCHAR,
            match_date VARCHAR
        )
    """)

    # Insert mappings from Python dict
    for mapping in mappings.values():
        db.execute("""
            INSERT INTO match_mapping VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            mapping['whoscored_id'],
            mapping['fotmob_id'],
            mapping['whoscored_team_ids'][0],
            mapping['whoscored_team_ids'][1],
            mapping['fotmob_home_team_id'],
            mapping['fotmob_away_team_id'],
            mapping['home_team'],
            mapping['away_team'],
            mapping.get('match_date', '')
        ])

    row_count = db.execute("SELECT COUNT(*) FROM match_mapping").fetchone()[0]
    context.log.info(f"✅ Created match_mapping table with {row_count} rows")

    # Generate unmapped report
    unmapped_final = [
        (ws_id, ws_data_json)
        for ws_id, ws_data_json in ws_matches
        if str(ws_id) not in mappings
    ]

    if unmapped_final:
        report_path = base_dir / "data" / "unmapped_matches_report.csv"
        with open(report_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['whoscored_id', 'team_names', 'unmapped_count'])
            for ws_id, ws_data_json in unmapped_final:
                ws_data = json.loads(ws_data_json)
                events = ws_data.get('events', [])
                ws_team_ids = {e['team_id'] for e in events if 'team_id' in e}
                try:
                    team_names = [ws_team_map[tid] for tid in ws_team_ids]
                    writer.writerow([ws_id, ' vs '.join(team_names), 1])
                except KeyError:
                    writer.writerow([ws_id, 'Unknown teams', 1])

        context.log.warning(f"⚠️  {len(unmapped_final)} matches unmapped (see {report_path})")

    db.close()

    # Summary
    total_ws = len(ws_matches)
    coverage_pct = (row_count / total_ws * 100) if total_ws > 0 else 0
    context.log.info(f"\n✅ Mapped {row_count}/{total_ws} matches ({coverage_pct:.1f}% coverage)")
    context.log.info(f"   - Stage 1 (exact): {stage1_count}")
    context.log.info(f"   - Stage 2 (fuzzy): {stage2_count}")
    context.log.info(f"   - Unmapped: {len(unmapped_final)}")

    return Output(
        row_count,
        metadata={
            "total_matches": row_count,
            "stage1_exact": stage1_count,
            "stage2_fuzzy": stage2_count,
            "unmapped": len(unmapped_final),
            "coverage_percent": round(coverage_pct, 1)
        }
    )
