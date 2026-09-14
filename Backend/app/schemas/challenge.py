from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field


class ChallengeCreate(BaseModel):
    """Schema for citizen challenge submission."""

    title: str = Field(..., min_length=3, description="Brief descriptive problem title")
    description: str = Field(..., min_length=10, description="Detailed problem description")
    location: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    address: Optional[str] = None
    pincode: Optional[str] = None
    # Strictly impact_scope per CONCORDIA_BACKEND_CONTEXT.md. Never impact_score.
    impact_scope: Optional[str] = "Area Specific"
    photo: Optional[str] = None
    video: Optional[str] = None
    document: Optional[str] = None
    expected_solution: Optional[str] = None
    submitted_by: Optional[str] = None
    status: Optional[str] = "submitted"
    challenge_id: Optional[str] = None
    user_id: Optional[str] = None

    model_config = ConfigDict(extra="ignore")


class ChallengeResponse(BaseModel):
    """Schema for challenge details returned to clients."""

    challenge_id: str
    title: str
    description: str
    location: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    address: Optional[str] = None
    pincode: Optional[str] = None
    impact_scope: Optional[str] = None
    photo: Optional[str] = None
    video: Optional[str] = None
    document: Optional[str] = None
    expected_solution: Optional[str] = None
    submitted_by: Optional[str] = None
    status: Optional[str] = "submitted"
    user_id: Optional[str] = None
    created_at: Optional[str] = None
    ai_analysis: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(extra="ignore")
