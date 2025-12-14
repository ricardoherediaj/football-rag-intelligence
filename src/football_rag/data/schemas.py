"""Pydantic models for data validation and transformation."""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class MatchContext(BaseModel):
    """Data from Chunk 1 (Summary)."""
    match_id: str
    home_team: str
    away_team: str
    home_score: int = 0
    away_score: int = 0
    match_date: str = "N/A"

class TacticalMetrics(BaseModel):
    """Data from Chunk 2 (Metrics). Keys match ChromaDB exactly."""
    
    # Passing
    home_progressive_passes: int = 0
    away_progressive_passes: int = 0
    home_total_passes: int = 0
    away_total_passes: int = 0
    
    # Pressure
    home_ppda: float = 0.0
    away_ppda: float = 0.0
    home_high_press: int = 0
    away_high_press: int = 0
    
    # Attacking
    home_shots: int = 0
    away_shots: int = 0
    home_xg: float = 0.0
    away_xg: float = 0.0
    
    # Positioning (Matches keys found in your diagnostic script)
    home_position: float = 0.0
    away_position: float = 0.0
    home_defense_line: float = 0.0
    away_defense_line: float = 0.0
    
    # Allow extra fields (like 'chunk_type') so validation doesn't fail
    class Config:
        extra = "ignore" 

    def to_prompt_variables(self, context: MatchContext) -> Dict[str, Any]:
        """Transform DB data into the exact keys required by V3.5 Prompt."""
        return {
            # --- CONTEXT ---
            "home_team": context.home_team,
            "away_team": context.away_team,
            "match_date": context.match_date,
            "home_score": context.home_score,
            "away_score": context.away_score,
            
            # --- METRICS (Renaming & Rounding) ---
            "home_pp": self.home_progressive_passes,
            "away_pp": self.away_progressive_passes,
            "home_total": self.home_total_passes,
            "away_total": self.away_total_passes,
            
            "home_ppda": round(self.home_ppda, 2),
            "away_ppda": round(self.away_ppda, 2),
            "home_press": self.home_high_press,
            "away_press": self.away_high_press,
            
            "home_shots": self.home_shots,
            "away_shots": self.away_shots,
            "home_xg": round(self.home_xg, 2),
            "away_xg": round(self.away_xg, 2),
            
            # Mapping DB keys to Prompt keys
            "home_pos": round(self.home_position, 1),
            "away_pos": round(self.away_position, 1),
            "home_def": round(self.home_defense_line, 1),
            "away_def": round(self.away_defense_line, 1),
        }