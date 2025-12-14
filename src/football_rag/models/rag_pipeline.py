"""Smart RAG pipeline for Football Analysis.
Implements 2-step retrieval: Search Match -> Validate -> Fill Prompt.
"""

import logging
import os
from typing import Dict, Any, Optional, List
import chromadb
from pathlib import Path

# Imports
from football_rag.models.generate import generate_with_llm
from football_rag.prompts_loader import load_prompt
from football_rag.data.schemas import MatchContext, TacticalMetrics 

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FootballRAGPipeline:
    def __init__(
        self,
        provider: str = "ollama",
        api_key: Optional[str] = None,
        chroma_path: str = "data/chroma", 
        prompt_version: str = "v3.5_balanced"
    ):
        """Initialize pipeline with direct ChromaDB access."""
        self.provider = provider
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY") 
        
        db_path = Path(chroma_path).resolve()
        self.client = chromadb.PersistentClient(path=str(db_path))
        self.collection = self.client.get_collection("eredivisie_matches_2025")
        
        self.prompts = load_prompt(prompt_version)
        
        # known_teams from your provided list
        self.known_teams = [
            "Feyenoord", "PSV Eindhoven", "Ajax", "AZ Alkmaar", "FC Groningen", 
            "NEC Nijmegen", "FC Twente", "Fortuna Sittard", "FC Utrecht", 
            "Go Ahead Eagles", "Sparta Rotterdam", "SC Heerenveen", "FC Volendam", 
            "Telstar", "NAC Breda", "PEC Zwolle", "Excelsior", "Heracles"
        ]
        
        logger.info(f"🚀 Football RAG Ready | Provider: {provider}")

    def run(self, user_query: str) -> Dict[str, Any]:
        """End-to-end execution with Pydantic Validation."""
        logger.info(f"🔎 Processing: '{user_query}'")

        # Step 1: Identify Match (Now with Metadata Filtering)
        match_context = self._identify_match(user_query)
        if not match_context:
            return {"error": "Could not identify match. Please mention team names."}
        
        match_name = f"{match_context.home_team} vs {match_context.away_team}"

        # Step 2: Fetch Metrics
        metrics_model = self._fetch_tactical_metrics(match_context.match_id)
        if not metrics_model:
            return {"error": f"Found match {match_name} but missing tactical metrics."}

        # Step 3: Map to Prompt
        prompt_variables = metrics_model.to_prompt_variables(match_context)

        logger.info(f"📊 DATA INTEGRITY CHECK for {match_name}:")
        logger.info(f"   • Score: {prompt_variables['home_score']}-{prompt_variables['away_score']}")
        logger.info(f"   • xG: {prompt_variables['home_xg']} vs {prompt_variables['away_xg']}")

        # Step 4: Generate
        formatted_prompt = self.prompts["user_template"].format(**prompt_variables)
        
        logger.info(f"🤖 Generating commentary...")
        
        response = generate_with_llm(
            prompt=formatted_prompt,
            provider=self.provider,
            api_key=self.api_key,
            system_prompt=self.prompts["system"],
            temperature=0.3
        )

        return {
            "match_id": match_context.match_id,
            "match_name": match_name,
            "commentary": response,
            "metrics_used": prompt_variables
        }

    def _identify_match(self, query: str) -> Optional[MatchContext]:
        """Find match using Hybrid Search (Metadata Filter + Semantic)."""
        
        # 1. Extract Teams from Query
        query_lower = query.lower()
        found_teams = []
        
        for team in self.known_teams:
            # Check full name (e.g. "PEC Zwolle")
            if team.lower() in query_lower:
                found_teams.append(team)
                continue
                
            # Check common short names (e.g. "PSV", "PEC")
            short_name = team.split()[0] 
            if len(short_name) > 3 and short_name.lower() in query_lower:
                 found_teams.append(team)

        # 2. Build Metadata Filter
        where_clause = {"chunk_type": "summary"} # Default: search all summaries
        
        if len(found_teams) > 0:
            # If we found teams, force Chroma to only look at matches involving them
            # Logic: (chunk_type == summary) AND (home_team IN found OR away_team IN found)
            
            team_filters = []
            for team in found_teams:
                team_filters.append({"home_team": team})
                team_filters.append({"away_team": team})
            
            where_clause = {
                "$and": [
                    {"chunk_type": "summary"},
                    {"$or": team_filters}
                ]
            }
            logger.info(f"🎯 Applied Filter: Finding matches involving {found_teams}")

        # 3. Query
        results = self.collection.query(
            query_texts=[query],
            n_results=1,
            where=where_clause 
        )

        if not results['ids'] or not results['ids'][0]:
            return None

        meta = results['metadatas'][0][0]
        return MatchContext(**meta)

    def _fetch_tactical_metrics(self, match_id: str) -> Optional[TacticalMetrics]:
        """Fetch metrics and return validated TacticalMetrics model."""
        target_id = f"{match_id}_tactical_metrics"
        
        result = self.collection.get(
            ids=[target_id],
            include=["metadatas"]
        )

        if not result['metadatas']:
            logger.warning(f"⚠️ Metrics chunk not found for {target_id}")
            return None

        raw_data = result['metadatas'][0]
        return TacticalMetrics(**raw_data)

if __name__ == "__main__":
    pipeline = FootballRAGPipeline(provider="anthropic")
    print("\n--- TEST RUN (WITH FILTER) ---")
    result = pipeline.run("Analyze the Heracles vs PEC Zwolle match")
    print(result.get("match_name", "Error"))