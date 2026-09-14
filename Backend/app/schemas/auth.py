from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict


class UserRole(str, Enum):
    CITIZEN = "citizen"
    STUDENT = "student"
    FACULTY = "faculty"
    UNIVERSITY_ADMIN = "university_admin"
    INDUSTRY_EMPLOYEE = "industry_employee"
    GOVERNMENT = "government"


class ProfileResponse(BaseModel):
    user_id: str
    role: str
    full_name: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    model_config = ConfigDict(extra="ignore")


class UserAuthResponse(BaseModel):
    user_id: str
    email: Optional[str] = None
    role: str
    full_name: Optional[str] = None
    profile: Optional[Dict[str, Any]] = None
    stakeholder: Optional[Dict[str, Any]] = None
    verification_status: str = "unlinked"
    is_verified: bool = False
    is_spoc: bool = False
    approval_authority: bool = False

    model_config = ConfigDict(extra="ignore")
