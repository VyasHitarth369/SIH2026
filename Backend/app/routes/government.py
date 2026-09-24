"""government.py

Routes for Phase 8: Government Monitoring & Policy Intelligence.
Provides system-wide read-only monitoring dashboards, active problem rosters,
faculty allocations, student participant listings, and solved project outcomes.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies.auth import require_government_officer
from app.schemas.government import (
    GovernmentDashboardMetrics,
    GovernmentDecisionResponse,
    GovernmentFacultyItem,
    GovernmentProblemItem,
    GovernmentRejectRequest,
    GovernmentSolvedProjectItem,
    GovernmentStudentItem,
)
from app.services.auth_service import AuthenticatedUser
from app.services.government_service import GovernmentService

router = APIRouter(prefix="/api/government", tags=["Government Monitoring & Policy Intelligence"])


def get_government_service() -> GovernmentService:
    """Dependency provider for GovernmentService to enable testing."""
    return GovernmentService()


# -----------------------------------------------------------------------------
# 1. GET /api/government/analytics — System-Wide Dashboard KPIs
# -----------------------------------------------------------------------------
@router.get(
    "/analytics",
    response_model=Dict[str, Any],
    summary="Get system-wide policy intelligence metrics and KPI analytics",
)
def get_government_analytics(
    current_user: AuthenticatedUser = Depends(require_government_officer()),
    service: GovernmentService = Depends(get_government_service),
):
    """Calculates system-wide metrics across challenges, participation, projects,

    milestones, and community feedback directly from database tables.
    Strictly avoids metric fabrication.
    """
    try:
        data = service.get_dashboard_analytics(current_user)
        return {
            "success": True,
            "data": data,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate government analytics: {str(e)}",
        )


# -----------------------------------------------------------------------------
# 2. GET /api/government/problems — Monitored Problem Statements
# -----------------------------------------------------------------------------
@router.get(
    "/problems",
    summary="List monitored problem statements with AI review and execution status",
)
def get_monitored_problems(
    category: Optional[str] = Query(None, description="Category filter: pending, allocated, rejected, solved, or all"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by challenge status"),
    district: Optional[str] = Query(None, description="Filter by district"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    limit: int = Query(100, ge=1, le=500),
    current_user: AuthenticatedUser = Depends(require_government_officer()),
    service: GovernmentService = Depends(get_government_service),
):
    """Retrieves challenges with hydrated AI analysis and project execution progress."""
    try:
        problems = service.get_monitored_problems(
            category=category,
            status_filter=status_filter,
            district=district,
            page=page,
            limit=limit,
        )
        return {
            "success": True,
            "counts": getattr(problems, "counts", {}),
            "total": getattr(problems, "total", len(problems)),
            "page": getattr(problems, "page", page),
            "limit": getattr(problems, "limit", limit),
            "data": list(problems),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve monitored problems: {str(e)}",
        )


# -----------------------------------------------------------------------------
# 3. GET /api/government/faculties — Assigned Faculty Roster
# -----------------------------------------------------------------------------
@router.get(
    "/faculties",
    summary="List faculty members assigned across collaborative innovation projects",
)
def get_assigned_faculties(
    current_user: AuthenticatedUser = Depends(require_government_officer()),
    service: GovernmentService = Depends(get_government_service),
):
    """Retrieves faculty members currently allocated to active projects with student counts."""
    try:
        data = service.get_assigned_faculties()
        return {
            "success": True,
            "total": len(data),
            "data": data,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve assigned faculty roster: {str(e)}",
        )


# -----------------------------------------------------------------------------
# 4. GET /api/government/students — Students Solving Problems
# -----------------------------------------------------------------------------
@router.get(
    "/students",
    summary="List students actively solving problems in innovation project teams",
)
def get_students_solving_problems(
    current_user: AuthenticatedUser = Depends(require_government_officer()),
    service: GovernmentService = Depends(get_government_service),
):
    """Retrieves active student participants in project teams with project context."""
    try:
        data = service.get_students_solving_problems()
        return {
            "success": True,
            "total": len(data),
            "data": data,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve participating students roster: {str(e)}",
        )


# -----------------------------------------------------------------------------
# 5. GET /api/government/solved-projects — Solved & Successful Projects
# -----------------------------------------------------------------------------
@router.get(
    "/solved-projects",
    summary="List projects marked solved or completed with stakeholder credits and outcomes",
)
def get_solved_projects(
    current_user: AuthenticatedUser = Depends(require_government_officer()),
    service: GovernmentService = Depends(get_government_service),
):
    """Retrieves projects marked solved or completed with stakeholder credits and outcomes."""
    try:
        data = service.get_solved_projects()
        return {
            "success": True,
            "total": len(data),
            "data": data,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve solved projects: {str(e)}",
        )


# -----------------------------------------------------------------------------
# 6. GET /api/government/mous — System-Wide Authoritative MOU Records
# -----------------------------------------------------------------------------
@router.get(
    "/mous",
    summary="List factual MOU collaboration records across universities and industries",
)
def get_government_mous(
    current_user: AuthenticatedUser = Depends(require_government_officer()),
    service: GovernmentService = Depends(get_government_service),
):
    """Retrieves factual tri-party MOU records between universities, industries,
    and the Government of Jharkhand. Strictly avoids fabricating fake records or PDFs.
    """
    try:
        data = service.get_government_mous()
        return {
            "success": True,
            "total": len(data),
            "data": data,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve government MOUs: {str(e)}",
        )


# -----------------------------------------------------------------------------
# 7. POST /api/government/problems/{challenge_id}/approve — Approve Problem Statement
# -----------------------------------------------------------------------------
@router.post(
    "/problems/{challenge_id}/approve",
    response_model=GovernmentDecisionResponse,
    summary="Approve a problem statement and trigger Top-5 university matching",
)
def approve_challenge(
    challenge_id: str,
    current_user: AuthenticatedUser = Depends(require_government_officer()),
    service: GovernmentService = Depends(get_government_service),
):
    """Approves a citizen/stakeholder problem statement. Advances status to 'routed'
    and triggers deterministic Top-5 university matching in 'recommended' state.
    """
    try:
        return service.approve_challenge(challenge_id, current_user)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to approve challenge: {str(e)}",
        )


# -----------------------------------------------------------------------------
# 8. POST /api/government/problems/{challenge_id}/reject — Reject Problem Statement
# -----------------------------------------------------------------------------
@router.post(
    "/problems/{challenge_id}/reject",
    response_model=GovernmentDecisionResponse,
    summary="Reject a problem statement with a mandatory reason",
)
def reject_challenge(
    challenge_id: str,
    body: GovernmentRejectRequest,
    current_user: AuthenticatedUser = Depends(require_government_officer()),
    service: GovernmentService = Depends(get_government_service),
):
    """Declines a problem statement with a mandatory rejection reason.
    Advances status to 'rejected' and prevents university matching.
    """
    try:
        return service.reject_challenge(challenge_id, body.reason, current_user)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reject challenge: {str(e)}",
        )


