from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class UniversityResponseRequest(BaseModel):
    """Payload for university administrator accepting or rejecting a match."""

    action: Literal["accept", "reject"] = Field(
        ...,
        description="Must be 'accept' or 'reject'. Acceptance is provisional until deadline finalization.",
    )
    response_note: Optional[str] = Field(
        None,
        description="Optional administrative rationale, conditions, or faculty availability note.",
    )

    model_config = ConfigDict(extra="ignore")


class FinalizeSelectionRequest(BaseModel):
    """Payload for finalizing university selection after acceptance / deadline window."""

    force_deadline: Optional[bool] = Field(
        False,
        description="If True, treats deadline as expired and immediately selects highest-ranked accepted university.",
    )

    model_config = ConfigDict(extra="ignore")


class ProjectCreate(BaseModel):
    """Payload for creating a project upon university selection and faculty allocation."""

    challenge_id: str
    university_id: str
    faculty_id: str
    industry_id: Optional[str] = None
    project_title: str = Field(..., min_length=3)
    description: Optional[str] = None
    status: Optional[str] = "proposed"
    start_date: Optional[str] = None
    expected_end_date: Optional[str] = None
    actual_end_date: Optional[str] = None

    model_config = ConfigDict(extra="ignore")


class ProjectResponse(BaseModel):
    """Response representing a collaborative innovation project."""

    project_id: str
    challenge_id: str
    university_id: str
    faculty_id: Optional[str] = None
    industry_id: Optional[str] = None
    project_title: str
    description: Optional[str] = None
    status: str = "proposed"
    start_date: Optional[str] = None
    expected_end_date: Optional[str] = None
    actual_end_date: Optional[str] = None
    created_at: Optional[str] = None
    university: Optional[Dict[str, Any]] = None
    faculty: Optional[Dict[str, Any]] = None
    challenge: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(extra="ignore")


# -----------------------------------------------------------------------------
# Phase 6: Project Members & Milestones Schemas
# -----------------------------------------------------------------------------
class ProjectMemberAdd(BaseModel):
    """Payload for adding an enrolled university student to a project."""

    student_id: str = Field(..., description="Student ID of enrolled student in selected university")
    role: Optional[str] = Field("member", description="Role: member, lead, researcher, developer")

    model_config = ConfigDict(extra="ignore")


class StudentInterestCreate(BaseModel):
    """Payload for student expressing interest in an eligible project."""

    role: Optional[str] = Field("applicant", description="Desired role e.g. applicant, researcher, developer")

    model_config = ConfigDict(extra="ignore")


class MemberStatusUpdate(BaseModel):
    """Payload for updating student membership status (faculty/admin select/reject)."""

    status: Literal["active", "rejected", "removed"] = Field(..., description="Target status: active, rejected, removed")

    model_config = ConfigDict(extra="ignore")


class FacultyAssignRequest(BaseModel):
    """Payload for allocating faculty to a project."""

    faculty_id: str = Field(..., description="Faculty ID to allocate to the project")

    model_config = ConfigDict(extra="ignore")


class MultiFacultyAssignRequest(BaseModel):
    """Payload for allocating one or more faculty mentors to a project/challenge."""

    faculty_ids: List[str] = Field(..., min_length=1, description="List of authoritative faculty IDs to allocate")
    project_title: Optional[str] = Field(None, description="Optional custom project title")

    model_config = ConfigDict(extra="ignore")


class UniversityRejectRequest(BaseModel):
    """Payload for university declining a challenge recommendation."""

    reason: str = Field(..., min_length=3, description="Mandatory reason for rejection")

    model_config = ConfigDict(extra="ignore")


class ProjectMemberResponse(BaseModel):
    """Representation of a student team member in project_members."""

    project_member_id: Optional[int] = None
    project_id: str
    student_id: str
    student_name: Optional[str] = None
    role: str = "member"
    status: str = "active"
    joined_at: Optional[str] = None

    model_config = ConfigDict(extra="ignore")


class MilestoneCreate(BaseModel):
    """Payload for creating a project milestone."""

    milestone_name: str = Field(..., min_length=3)
    description: Optional[str] = None
    assigned_to: Optional[str] = Field(None, description="Student ID or assignee name")
    deadline: Optional[str] = None
    status: Optional[str] = "pending"
    evidence_url: Optional[str] = None
    completion_percentage: Optional[int] = Field(
        0, ge=0, le=100, description="Completion percentage strictly between 0 and 100"
    )

    model_config = ConfigDict(extra="ignore")


class MilestoneUpdate(BaseModel):
    """Payload for updating an existing milestone."""

    milestone_name: Optional[str] = None
    description: Optional[str] = None
    assigned_to: Optional[str] = None
    deadline: Optional[str] = None
    status: Optional[str] = None
    evidence_url: Optional[str] = None
    completion_percentage: Optional[int] = Field(
        None, ge=0, le=100, description="Completion percentage strictly between 0 and 100"
    )

    model_config = ConfigDict(extra="ignore")


class MilestoneResponse(BaseModel):
    """Representation of a project milestone."""

    milestone_id: Optional[int] = None
    project_id: str
    milestone_name: str
    description: Optional[str] = None
    assigned_to: Optional[str] = None
    deadline: Optional[str] = None
    status: str = "pending"
    evidence_url: Optional[str] = None
    completion_percentage: int = 0
    created_at: Optional[str] = None

    model_config = ConfigDict(extra="ignore")


class ProjectMilestoneStatusUpdate(BaseModel):
    """Standardized 7-stage milestone update for assigned faculty."""

    milestone: str = Field(..., description="Target standardized milestone from 7-stage sequence")

    model_config = ConfigDict(extra="ignore")

