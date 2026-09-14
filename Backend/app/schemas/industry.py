"""industry.py

Pydantic schemas for Phase 7: Industry Collaboration Workflow:
- SPOC collaboration acceptance/rejection on challenge matches
- Employee interest expressions on collaborative innovation projects
- SPOC employee selection and interest lifecycle management
"""

from typing import Any, Dict, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class IndustryCollaborationResponse(BaseModel):
    """Payload for Industry SPOC accepting or rejecting an industry match."""

    action: Literal["accept", "reject"] = Field(
        ...,
        description="Decision: 'accept' or 'reject'. Acceptance confirms corporate partnership.",
    )
    response_note: Optional[str] = Field(
        None,
        description="Optional corporate note, available resources, equipment, or mentorship commitment.",
    )

    model_config = ConfigDict(extra="ignore")


class EmployeeInterestCreate(BaseModel):
    """Payload for an eligible verified industry employee expressing interest in a project."""

    message: Optional[str] = Field(
        None,
        max_length=1000,
        description="Statement of interest, specialized skills, or technical contribution proposal.",
    )

    model_config = ConfigDict(extra="ignore")


class EmployeeInterestUpdate(BaseModel):
    """Payload for SPOC selecting/rejecting employee or employee withdrawing interest."""

    status: Literal["selected", "not_selected", "withdrawn"] = Field(
        ...,
        description="Updated interest status. 'selected' indicates official project participant.",
    )
    note: Optional[str] = Field(
        None,
        description="Optional rationale or assignment note from SPOC.",
    )

    model_config = ConfigDict(extra="ignore")


class EmployeeInterestResponse(BaseModel):
    """Representation of an employee interest record with hydrated employee profile."""

    interest_id: Optional[int] = None
    project_id: str
    employee_id: str
    employee_name: Optional[str] = None
    department: Optional[str] = None
    designation: Optional[str] = None
    email: Optional[str] = None
    message: Optional[str] = None
    status: str = "interested"
    created_at: Optional[str] = None

    model_config = ConfigDict(extra="ignore")
