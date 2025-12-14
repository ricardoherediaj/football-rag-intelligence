"""
Data Contract for Football RAG.
Defines the 'Golden Schema' for match data processing.
"""
from typing import Optional
from pydantic import BaseModel, Field, validator

class TeamMatchStats(BaseModel):
    """Strict schema for a single team's performance metrics in one match."""
    team_name: str
    team_id: int
    
    # --- Passing & Progression ---
    progressive_passes: int = Field(..., description="Passes moving ball ≥9.11m towards goal")
    total_passes: int
    pass_accuracy: float = Field(..., ge=0, le=100, description="Completion percentage")
    verticality: float = Field(..., description="Percentage of forward movement in passing")
    
    # --- Defensive Pressure ---
    ppda: float = Field(..., description="Passes Per Defensive Action")
    high_press_events: int = Field(..., description="Defensive actions in opp. final third")
    defensive_actions: int
    tackles: int
    interceptions: int
    
    # --- Attacking ---
    shots: int
    shots_on_target: int
    xg: float = Field(..., description="Expected Goals")
    
    # --- Positioning ---
    median_position: float = Field(..., description="Average x-coordinate of touches")
    defense_line: float = Field(..., description="Average height of defensive actions")
    forward_line: float = Field(..., description="Average height of attacking actions")
    compactness: float = Field(..., description="Distance between def and fwd lines (normalized)")
    
    # --- Match Context / Physical ---
    possession: float = Field(..., ge=0, le=100)
    field_tilt: float = Field(..., description="Share of final third possession")
    clearances: int
    aerials_won: int
    fouls: int

class MatchMetadata(BaseModel):
    """Immutable identity data for the match."""
    match_id: str = Field(..., description="WhoScored Match ID")
    fotmob_id: str
    match_date: str
    season: str = "2025-2026"
    league: str = "eredivisie"
    
    # Data Quality Flags
    has_tracking_data: bool = True
    has_fotmob_xg: bool = True

class MatchProfile(BaseModel):
    """
    The Golden Record. 
    This object represents a fully processed, validated match ready for RAG.
    """
    metadata: MatchMetadata
    
    # Core Results
    home_score: int
    away_score: int
    
    # Team Data (Nested for clean structure)
    home_team: TeamMatchStats
    away_team: TeamMatchStats
    
    @validator('home_score')
    def validate_score_integrity(cls, v, values):
        """Sanity check: Score shouldn't be negative."""
        if v < 0:
            raise ValueError("Score cannot be negative")
        return v

    def get_summary_text(self) -> str:
        """Helper to generate consistent summary text for RAG."""
        return (
            f"{self.home_team.team_name} vs {self.away_team.team_name} "
            f"({self.home_score}-{self.away_score}) on {self.metadata.match_date[:10]}. "
            f"Possession: {self.home_team.possession}% vs {self.away_team.possession}%. "
            f"xG: {self.home_team.xg} vs {self.away_team.xg}."
        )

    def get_metrics_text(self) -> str:
        """Helper to generate the dense metrics chunk for LLM."""
        return (
            f"Tactical Metrics for {self.home_team.team_name} (Home) vs {self.away_team.team_name} (Away):\n"
            f"Shots: {self.home_team.shots} vs {self.away_team.shots}\n"
            f"xG: {self.home_team.xg} vs {self.away_team.xg}\n"
            f"Progressive Passes: {self.home_team.progressive_passes} vs {self.away_team.progressive_passes}\n"
            f"PPDA: {self.home_team.ppda} vs {self.away_team.ppda}\n"
            f"High Press Events: {self.home_team.high_press_events} vs {self.away_team.high_press_events}\n"
            f"Defensive Line: {self.home_team.defense_line}m vs {self.away_team.defense_line}m\n"
            f"Field Tilt: {self.home_team.field_tilt}% vs {self.away_team.field_tilt}%"
        )