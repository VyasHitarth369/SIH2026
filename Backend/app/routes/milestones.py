"""milestones.py

Routes for Project Milestone progress updates and evidence submissions (Phase 6).
"""

from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies.auth import get_current_user
from app.routes.projects import get_project_workflow_service
from app.schemas.project import MilestoneUpdate, MilestoneResponse
from app.services.auth_service import AuthenticatedUser
from app.services.project_workflow_service import ProjectWorkflowService

router = APIRouter(prefix="/api/milestones", tags=["Milestones & Progress Tracking"])



# -----------------------------------------------------------------------------
# 1. PATCH /api/milestones/{milestone_id} — Update Milestone Progress & Evidence
# -----------------------------------------------------------------------------
@router.patch(
    "/{milestone_id}",
    summary="Update milestone progress, status, and evidence",
)
def update_milestone(
    milestone_id: int,
    patch: MilestoneUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: ProjectWorkflowService = Depends(get_project_workflow_service),
):
    """Updates milestone status, evidence URL, and completion percentage (0-100).

    Validates:
    - User has project access (assigned student member, faculty, or university admin)
    - Completion percentage must be strictly between 0 and 100
    - If completion reaches 100%, automatically marks status as 'completed'
    """
    try:
        payload = patch.model_dump(exclude_none=True)
        updated = service.update_milestone(milestone_id, payload, current_user)
        return {
            "success": True,
            "message": "Milestone updated successfully",
            "data": updated,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update milestone '{milestone_id}': {str(e)}",
        )
