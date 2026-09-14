"""feedback.py

Pydantic models for Phase 9: Feedback + Outcome + Impact Tracking.
Enforces 1-5 rating constraints, non-fabrication of outcomes, and structured
lifecycle status transitions.
"""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class FeedbackCreate(BaseModel):
    """Schema for submitting qualitative and quantitative feedback on a collaborative project."""
    challenge_id: Optional[str] = Field(
        None,
        description="Associated challenge ID. If provided, must strictly match the project's challenge.",
    )
    rating: int = Field(
        ...,
        ge=1,
        le=5,
        description="Satisfaction and performance rating on a 1 to 5 scale.",
    )
    comments: Optional[str] = Field(
        None,
        max_length=2000,
        description="Qualitative feedback, operational observations, or user comments.",
    )
    outcome: Optional[str] = Field(
        None,
        max_length=2000,
        description="Factual, observed real-world outcome or metric achieved by the project.",
    )


class FeedbackResponse(BaseModel):
    """Schema representing an official feedback record in the database."""
    feedback_id: Union[int, str] = Field(..., description="Unique feedback record identifier")
    project_id: str = Field(..., description="Project ID being evaluated")
    challenge_id: str = Field(..., description="Associated challenge ID")
    submitted_by: str = Field(..., description="Submitter name or masked privacy identifier")
    respondent_role: str = Field(..., description="Authoritative platform role of the submitter")
    rating: int = Field(..., ge=1, le=5, description="Rating between 1 and 5")
    comments: Optional[str] = Field(None, description="Qualitative feedback comments")
    outcome: Optional[str] = Field(None, description="Observed outcome statement")
    created_at: Optional[str] = Field(None, description="Timestamp of feedback submission")


class ProjectStatusTransition(BaseModel):
    """Schema for advancing a project through legitimate lifecycle stages."""
    status: str = Field(
        ...,
        description="Target lifecycle state: active, prototype, pilot, deployed, solved, completed",
    )
    justification: Optional[str] = Field(
        None,
        max_length=1000,
        description="Operational justification, field evidence, or milestone milestone verification for the status advancement.",
    )


class ProjectImpactResponse(BaseModel):
    """Role-tailored outcome and impact intelligence response."""
    project_id: str
    project_title: str
    challenge_id: str
    challenge_title: Optional[str] = None
    current_status: str
    university_name: Optional[str] = None
    faculty_name: Optional[str] = None
    industry_name: Optional[str] = None
    student_participants_count: int = 0
    average_rating: Optional[float] = None
    total_feedback_count: int = 0
    milestones_summary: Dict[str, Any] = Field(default_factory=dict)
    role_specific_impact: Dict[str, Any] = Field(default_factory=dict)
    data_sources: List[str] = Field(default_factory=list)
