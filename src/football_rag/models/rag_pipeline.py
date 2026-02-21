"""Smart RAG pipeline for Football Analysis.
Implements 2-step retrieval: semantic search → metrics fetch → LLM generation.
Backed by DuckDB VSS (gold_match_embeddings) and Gold layer (gold_match_summaries).
"""

import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional, List

import duckdb
from sentence_transformers import SentenceTransformer

from football_rag.models.generate import generate_with_llm
from football_rag.prompts_loader import load_prompt
from football_rag.data.schemas import MatchContext, TacticalMetrics

logger = logging.getLogger(__name__)

# Column order returned by _fetch_tactical_metrics SQL — must match TacticalMetrics fields
_METRICS_COLS = [
    "home_progressive_passes", "away_progressive_passes",
    "home_total_passes", "away_total_passes",
    "home_ppda", "away_ppda",
    "home_high_press", "away_high_press",
    "home_shots", "away_shots",
    "home_xg", "away_xg",
    "home_position", "away_position",
    "home_defense_line", "away_defense_line",
]


class FootballRAGPipeline:
    def __init__(
        self,
        provider: str = "anthropic",
        api_key: Optional[str] = None,
        db_path: str = "data/lakehouse.duckdb",
        prompt_version: str = "v3.5_balanced",
    ):
        """Initialize pipeline with DuckDB VSS access."""
        self.provider = provider
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.db_path = Path(db_path).resolve()
        self.prompts = load_prompt(prompt_version)
        self._model = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")

        self.known_teams = [
            "Feyenoord", "PSV Eindhoven", "Ajax", "AZ Alkmaar", "FC Groningen",
            "NEC Nijmegen", "FC Twente", "Fortuna Sittard", "FC Utrecht",
            "Go Ahead Eagles", "Sparta Rotterdam", "SC Heerenveen", "FC Volendam",
            "Telstar", "NAC Breda", "PEC Zwolle", "Excelsior", "Heracles",
        ]

        logger.info(f"Football RAG Ready | Provider: {provider} | DB: {self.db_path}")

    def run(self, user_query: str) -> Dict[str, Any]:
        """End-to-end execution: identify match → fetch metrics → generate commentary."""
        logger.info(f"Processing: '{user_query}'")

        match_context = self._identify_match(user_query)
        if not match_context:
            return {"error": "Could not identify match. Please mention team names."}

        match_name = f"{match_context.home_team} vs {match_context.away_team}"

        metrics_model = self._fetch_tactical_metrics(match_context.match_id)
        if not metrics_model:
            return {"error": f"Found match {match_name} but missing tactical metrics."}

        prompt_variables = metrics_model.to_prompt_variables(match_context)

        logger.info(
            f"Data check for {match_name}: "
            f"score={prompt_variables['home_score']}-{prompt_variables['away_score']}, "
            f"xG={prompt_variables['home_xg']} vs {prompt_variables['away_xg']}"
        )

        formatted_prompt = self.prompts["user_template"].format(**prompt_variables)

        response = generate_with_llm(
            prompt=formatted_prompt,
            provider=self.provider,
            api_key=self.api_key,
            system_prompt=self.prompts["system"],
            temperature=0.3,
        )

        return {
            "match_id": match_context.match_id,
            "match_name": match_name,
            "commentary": response,
            "metrics_used": prompt_variables,
        }

    def _identify_match(self, query: str) -> Optional[MatchContext]:
        """Find the best matching match using DuckDB VSS (array_distance on embeddings).

        Strategy:
        1. Encode query with the same model used at embedding time
        2. Find top-5 semantically similar matches via HNSW index
        3. If team names are in the query, filter candidates to those teams
        4. Return the top result as MatchContext
        """
        query_emb = self._model.encode(query).tolist()
        team_filter = self._build_team_filter(query)

        db = duckdb.connect(str(self.db_path))
        db.execute("LOAD vss")

        sql = f"""
            SELECT s.match_id, s.home_team, s.away_team,
                   s.home_goals, s.away_goals, s.match_date
            FROM main_main.gold_match_summaries s
            JOIN (
                SELECT match_id
                FROM gold_match_embeddings
                ORDER BY array_distance(embedding, ?::FLOAT[768])
                LIMIT 5
            ) ranked USING (match_id)
            {team_filter}
            LIMIT 1
        """
        row = db.execute(sql, [query_emb]).fetchone()
        db.close()

        if not row:
            return None

        logger.info(f"Identified match: {row[1]} vs {row[2]} (id={row[0]})")
        return MatchContext(
            match_id=row[0],
            home_team=row[1],
            away_team=row[2],
            home_score=row[3],
            away_score=row[4],
            match_date=row[5],
        )

    def _fetch_tactical_metrics(self, match_id: str) -> Optional[TacticalMetrics]:
        """Fetch tactical metrics from gold_match_summaries for the given match."""
        db = duckdb.connect(str(self.db_path))
        row = db.execute(
            """
            SELECT
                home_progressive_passes, away_progressive_passes,
                home_total_passes,       away_total_passes,
                home_ppda,               away_ppda,
                home_high_press,         away_high_press,
                home_shots,              away_shots,
                home_total_xg        AS home_xg,
                away_total_xg        AS away_xg,
                home_median_position AS home_position,
                away_median_position AS away_position,
                home_defense_line,       away_defense_line
            FROM main_main.gold_match_summaries
            WHERE match_id = ?
            """,
            [match_id],
        ).fetchone()
        db.close()

        if not row:
            logger.warning(f"No metrics found for match_id={match_id}")
            return None

        return TacticalMetrics(**dict(zip(_METRICS_COLS, row)))

    def _build_team_filter(self, query: str) -> str:
        """Extract team names from query and return a SQL WHERE clause fragment.

        Returns empty string if no known teams found (no filtering applied).
        """
        query_lower = query.lower()
        found_teams: List[str] = []

        for team in self.known_teams:
            if team.lower() in query_lower:
                found_teams.append(team)
                continue
            short_name = team.split()[0]
            if len(short_name) > 3 and short_name.lower() in query_lower:
                found_teams.append(team)

        if not found_teams:
            return ""

        logger.info(f"Team filter applied: {found_teams}")
        if len(found_teams) >= 2:
            # Both teams mentioned — require both to appear in the match
            t0, t1 = found_teams[0], found_teams[1]
            condition = (
                f"(s.home_team = '{t0}' AND s.away_team = '{t1}') OR "
                f"(s.home_team = '{t1}' AND s.away_team = '{t0}')"
            )
        else:
            # Single team — any match involving that team
            t = found_teams[0]
            condition = f"s.home_team = '{t}' OR s.away_team = '{t}'"
        return f"WHERE ({condition})"


if __name__ == "__main__":
    pipeline = FootballRAGPipeline(provider="anthropic")
    result = pipeline.run("Analyze the Heracles vs PEC Zwolle match")
    print(result.get("commentary", result.get("error")))
