"""government.py

Pydantic schemas for Phase 8: Government Monitoring & Policy Intelligence.
Covers dashboard metrics, active problem tracking, faculty rosters,
student participation summaries, and solved projects without metric fabrication.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ChallengesMetricSummary(BaseModel):
    """Summary of challenges lifecycle from 'challenges' and 'ai_analysis' tables."""

    total_submitted: int = Field(0, description="Total challenges originally submitted")
    total_challenges: int = Field(0, description="Total count in challenges table")
    active_challenges: int = Field(0, description="Challenges currently in active review/matching/execution")
    validated_challenges: int = Field(0, description="Challenges with validated problem gap")
    by_domain: Dict[str, int] = Field(default_factory=dict, description="Distribution of challenges by domain/category")
    by_source: Dict[str, int] = Field(default_factory=dict, description="Distribution by source (citizen, govt, industry)")
    by_district: Dict[str, int] = Field(default_factory=dict, description="Distribution across districts")

    model_config = ConfigDict(extra="ignore")


class ParticipationMetricSummary(BaseModel):
    """Summary of institutional and stakeholder engagement."""

    universities_engaged: int = Field(0, description="Distinct universities with projects or accepted matches")
    industries_engaged: int = Field(0, description="Distinct industries with projects or accepted matches")
    faculty_assigned: int = Field(0, description="Distinct faculty allocated across innovation projects")
    students_participating: int = Field(0, description="Distinct students active in project_members")

    model_config = ConfigDict(extra="ignore")


class ProjectsMetricSummary(BaseModel):
    """Summary of project states from 'projects' table."""

    total_projects: int = Field(0, description="Total collaborative projects")
    active_projects: int = Field(0, description="Projects in active execution (active, prototype, pilot, deployed)")
    proposed_projects: int = Field(0, description="Projects in proposed stage awaiting milestone initiation")
    solved_problems: int = Field(0, description="Projects marked solved or completed")
    lifecycle_funnel: Dict[str, int] = Field(default_factory=dict, description="Counts by lifecycle milestone stage")

    model_config = ConfigDict(extra="ignore")


class MilestonesMetricSummary(BaseModel):
    """System-wide milestone completion metrics from 'project_milestones' table."""

    total_milestones: int = Field(0, description="Total milestones created across projects")
    completed_milestones: int = Field(0, description="Milestones with status 'completed' or completion_percentage=100")
    in_progress_milestones: int = Field(0, description="Milestones with status 'in_progress'")
    pending_milestones: int = Field(0, description="Milestones with status 'pending'")
    overall_completion_rate: float = Field(0.0, description="Average completion percentage across all milestones (0-100)")

    model_config = ConfigDict(extra="ignore")


class OutcomesMetricSummary(BaseModel):
    """Feedback and community endorsement outcomes from 'feedback' and 'challenge_support'."""

    total_feedback_count: int = Field(0, description="Total public/stakeholder feedback records")
    average_feedback_rating: Optional[float] = Field(None, description="Average satisfaction/impact rating (1-5)")
    total_challenge_support_votes: int = Field(0, description="Total citizen endorsement votes across challenges")

    model_config = ConfigDict(extra="ignore")


class GovernmentDashboardMetrics(BaseModel):
    """Top-level aggregated policy-intelligence payload for government monitoring."""

    officer_name: Optional[str] = None
    department: Optional[str] = None
    district: Optional[str] = None
    challenges: ChallengesMetricSummary
    participation: ParticipationMetricSummary
    projects: ProjectsMetricSummary
    milestones: MilestonesMetricSummary
    outcomes: OutcomesMetricSummary
    data_sources: List[str] = Field(
        default_factory=lambda: [
            "challenges",
            "ai_analysis",
            "projects",
            "project_members",
            "project_milestones",
            "challenge_university_matches",
            "challenge_industry_matches",
            "feedback",
            "challenge_support",
        ]
    )
    limitations: List[str] = Field(
        default_factory=lambda: [
            "Financial disbursement and budget allocation metrics are unavailable in the current 18-table schema.",
            "Historical resolution duration is estimated where actual_end_date is recorded on completed projects.",
        ]
    )

    model_config = ConfigDict(extra="ignore")


class GovernmentProblemItem(BaseModel):
    """Monitored problem statement with AI review and project execution relations."""

    challenge_id: str
    title: str
    description: str
    location: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    status: str
    submitted_by: Optional[str] = None
    created_at: Optional[str] = None
    impact_scope: Optional[str] = None
    category: Optional[str] = None
    required_skills: Optional[str] = None
    required_technologies: Optional[str] = None
    innovation_scope: Optional[str] = None
    project_id: Optional[str] = None
    project_title: Optional[str] = None
    project_status: Optional[str] = None
    university_name: Optional[str] = None
    faculty_name: Optional[str] = None
    industry_name: Optional[str] = None
    milestone_progress_pct: Optional[float] = None
    government_rejection_reason: Optional[str] = None
    government_reviewed_at: Optional[str] = None
    government_reviewed_by: Optional[str] = None
    university_rejections: List[Dict[str, Any]] = Field(default_factory=list)
    top_universities: Optional[List[Dict[str, Any]]] = None
    top_industries: Optional[List[Dict[str, Any]]] = None
    industry_matching_status: Optional[str] = "Pending"

    model_config = ConfigDict(extra="ignore")


class GovernmentRejectRequest(BaseModel):
    """Schema for Government declining a challenge with mandatory reason."""

    reason: str = Field(..., min_length=1, description="Mandatory reason for declining the problem statement")

    model_config = ConfigDict(extra="ignore")


class GovernmentDecisionResponse(BaseModel):
    """Schema for Government approve/reject responses."""

    success: bool
    challenge_id: str
    status: str
    message: str
    government_rejection_reason: Optional[str] = None
    government_reviewed_at: Optional[str] = None
    government_reviewed_by: Optional[str] = None
    university_matches: Optional[List[Dict[str, Any]]] = None
    top_universities: Optional[List[Dict[str, Any]]] = None

    model_config = ConfigDict(extra="ignore")


class GovernmentFacultyItem(BaseModel):
    """Assigned faculty member across collaborative innovation projects."""

    faculty_id: str
    faculty_name: str
    department: Optional[str] = None
    designation: Optional[str] = None
    email: Optional[str] = None
    university_id: str
    university_name: Optional[str] = None
    project_id: str
    project_title: str
    challenge_id: str
    participating_students_count: int = 0

    model_config = ConfigDict(extra="ignore")


class GovernmentStudentItem(BaseModel):
    """Student participant solving societal problems in an active project team."""

    student_id: str
    student_name: str
    department: Optional[str] = None
    course: Optional[str] = None
    university_id: str
    university_name: Optional[str] = None
    project_id: str
    project_title: str
    role: str = "member"
    status: str = "active"

    model_config = ConfigDict(extra="ignore")


class GovernmentSolvedProjectItem(BaseModel):
    """Successfully solved project with outcome details and stakeholder credits."""

    project_id: str
    challenge_id: str
    project_title: str
    description: Optional[str] = None
    status: str
    start_date: Optional[str] = None
    actual_end_date: Optional[str] = None
    university_name: Optional[str] = None
    faculty_name: Optional[str] = None
    industry_name: Optional[str] = None
    student_participants: List[str] = Field(default_factory=list)
    average_rating: Optional[float] = None
    outcome_summary: Optional[str] = None

    model_config = ConfigDict(extra="ignore")
