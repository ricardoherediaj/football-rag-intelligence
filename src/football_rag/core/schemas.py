"""
Pydantic models for API boundaries and structured outputs.
Why: contract-first design; enforce shape even in a POC.
"""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=512)
    top_k: Optional[int] = Field(default=None, ge=1, le=10)


class SourceNode(BaseModel):
    text: str
    score: float
    metadata: Dict[str, str]


class FaithfulnessResult(BaseModel):
    faithful: bool
    hallucinated_numbers: List[float] = []
    valid_numbers: List[float] = []
    faithfulness_score: float = Field(ge=0.0, le=1.0)


class Answer(BaseModel):
    answer: str
    sources: List[SourceNode]
    faithfulness: Optional[FaithfulnessResult] = None
    prompt_version: str
    prompt_checksum: str
    model_name: str
    duration_ms: int
    cache_hit: bool


class ChartSpec(BaseModel):
    chart_type: str
    match_id: Optional[str] = None
    team: Optional[str] = None
