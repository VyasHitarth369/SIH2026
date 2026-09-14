from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict


class UniversityMatchItem(BaseModel):
    """Represents a ranked university match from challenge_university_matches."""

    match_id: Optional[int] = None
    challenge_id: str
    university_id: str
    university_name: Optional[str] = None
    rank: int
    match_score: float
    match_reason: str
    status: str = "recommended"
    city: Optional[str] = None
    district: Optional[str] = None
    score_breakdown: Optional[Dict[str, float]] = None

    model_config = ConfigDict(extra="ignore")


class IndustryMatchItem(BaseModel):
    """Represents a ranked industry match from challenge_industry_matches."""

    match_id: Optional[int] = None
    challenge_id: str
    industry_id: str
    industry_name: Optional[str] = None
    rank: int
    match_score: float
    match_reason: str
    status: str = "recommended"
    city: Optional[str] = None
    district: Optional[str] = None
    domain: Optional[str] = None
    score_breakdown: Optional[Dict[str, float]] = None

    model_config = ConfigDict(extra="ignore")


class UniversityMatchListResponse(BaseModel):
    success: bool = True
    challenge_id: str
    total_matches: int
    data: List[UniversityMatchItem]


class IndustryMatchListResponse(BaseModel):
    success: bool = True
    challenge_id: str
    total_matches: int
    data: List[IndustryMatchItem]
