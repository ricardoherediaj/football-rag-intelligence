"""Pydantic schemas for data validation and contracts."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class MatchEvent(BaseModel):
    """Schema for football match events."""
    
    match_id: str = Field(..., description="Unique match identifier")
    event_id: str = Field(..., description="Unique event identifier")
    event_type: str = Field(..., description="Type of event (shot, pass, etc.)")
    timestamp: datetime = Field(..., description="When event occurred")
    minute: int = Field(..., description="Match minute")
    
    player_id: Optional[str] = Field(None, description="Player involved")
    player_name: Optional[str] = Field(None, description="Player name")
    team_id: str = Field(..., description="Team identifier")
    team_name: str = Field(..., description="Team name")
    
    x_coordinate: Optional[float] = Field(None, description="X coordinate (0-100)")
    y_coordinate: Optional[float] = Field(None, description="Y coordinate (0-100)")
    
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional event data")
    
    class Config:
        json_schema_extra = {
            "example": {
                "match_id": "match_123456",
                "event_id": "event_789",
                "event_type": "shot",
                "timestamp": "2024-01-01T15:30:00Z",
                "minute": 23,
                "player_id": "player_123",
                "player_name": "Steven Bergwijn",
                "team_id": "ajax",
                "team_name": "Ajax",
                "x_coordinate": 85.5,
                "y_coordinate": 45.2,
                "metadata": {"shot_outcome": "goal", "xG": 0.45}
            }
        }


class Match(BaseModel):
    """Schema for match data."""
    
    match_id: str = Field(..., description="Unique match identifier")
    home_team: str = Field(..., description="Home team name")
    away_team: str = Field(..., description="Away team name")
    home_score: int = Field(..., description="Home team score")
    away_score: int = Field(..., description="Away team score")
    
    competition: str = Field(..., description="Competition name")
    season: str = Field(..., description="Season identifier")
    match_date: datetime = Field(..., description="Match date")
    
    events: List[MatchEvent] = Field(default_factory=list, description="Match events")
    
    class Config:
        json_schema_extra = {
            "example": {
                "match_id": "match_123456",
                "home_team": "Ajax",
                "away_team": "PSV",
                "home_score": 2,
                "away_score": 1,
                "competition": "Eredivisie",
                "season": "2024-25",
                "match_date": "2024-01-01T15:00:00Z"
            }
        }


class PlayerStats(BaseModel):
    """Schema for aggregated player statistics."""
    
    player_id: str = Field(..., description="Unique player identifier")
    player_name: str = Field(..., description="Player name")
    team: str = Field(..., description="Current team")
    position: str = Field(..., description="Playing position")
    
    # Performance metrics
    matches_played: int = Field(default=0, description="Matches played")
    goals: int = Field(default=0, description="Goals scored")
    assists: int = Field(default=0, description="Assists made")
    shots: int = Field(default=0, description="Total shots")
    shots_on_target: int = Field(default=0, description="Shots on target")
    pass_accuracy: float = Field(default=0.0, description="Pass accuracy percentage")
    
    # Advanced metrics
    xg: float = Field(default=0.0, description="Expected goals")
    xa: float = Field(default=0.0, description="Expected assists")
    
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional stats")


class RAGQuery(BaseModel):
    """Schema for RAG query requests."""
    
    question: str = Field(..., description="User's question")
    context_filter: Optional[Dict[str, Any]] = Field(
        None, 
        description="Filters for context retrieval"
    )
    max_context_items: int = Field(default=5, description="Max context items to retrieve")
    
    class Config:
        json_schema_extra = {
            "example": {
                "question": "How did Steven Bergwijn perform against top 6 teams?",
                "context_filter": {"player_name": "Steven Bergwijn", "team_tier": "top6"},
                "max_context_items": 10
            }
        }


class RAGResponse(BaseModel):
    """Schema for RAG query responses."""
    
    answer: str = Field(..., description="Generated answer")
    context_used: List[str] = Field(..., description="Context snippets used")
    confidence_score: float = Field(..., description="Response confidence (0-1)")
    
    # Metadata
    query_time_ms: float = Field(..., description="Query processing time")
    model_used: str = Field(..., description="LLM model used")
    context_sources: List[str] = Field(default_factory=list, description="Data sources")
    
    class Config:
        json_schema_extra = {
            "example": {
                "answer": "Steven Bergwijn scored 3 goals in 8 matches against top 6 teams...",
                "context_used": ["Match data from Ajax vs PSV...", "Player stats..."],
                "confidence_score": 0.85,
                "query_time_ms": 1250.5,
                "model_used": "llama3.2:1b",
                "context_sources": ["whoscored", "fotmob"]
            }
        }