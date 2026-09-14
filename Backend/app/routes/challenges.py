"""challenges.py

API Routes for Citizen Challenge Submission, AI Review, Existing-Solution Discovery,
and Gap Validation under Concordia / Samadhan Setu Phase 3.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies.auth import get_current_user, get_current_user_optional
from app.schemas.analysis import (
    AnalyzeChallengeResponse,
    ExistingSolutionDecisionRequest,
)
from app.schemas.challenge import ChallengeCreate, ChallengeResponse
from app.schemas.project import UniversityResponseRequest, FinalizeSelectionRequest
from app.schemas.industry import IndustryCollaborationResponse
from app.services.auth_service import AuthenticatedUser
from app.services.challenge_service import ChallengeService

router = APIRouter(prefix="/api/challenges", tags=["Challenges & Citizen AI Workflow"])


def get_challenge_service() -> ChallengeService:
    """Dependency provider for ChallengeService to enable modular testing."""
    return ChallengeService()


def get_workflow_service():
    """Dependency provider for UniversityWorkflowService."""
    from app.services.university_workflow_service import UniversityWorkflowService
    return UniversityWorkflowService()


def get_industry_workflow_service():
    """Dependency provider for IndustryWorkflowService."""
    from app.services.industry_workflow_service import IndustryWorkflowService
    return IndustryWorkflowService()


# -----------------------------------------------------------------------------
# 1. POST /api/challenges — Citizen Challenge Submission
# -----------------------------------------------------------------------------
@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Submit a new societal challenge",
)
def create_challenge(
    challenge: ChallengeCreate,
    current_user: Optional[AuthenticatedUser] = Depends(get_current_user_optional),
    service: ChallengeService = Depends(get_challenge_service),
):
    """Submits a new challenge, persists to Supabase 'challenges' table,

    and associates with the authenticated user ID.
    Strictly uses impact_scope (never impact_score).
    """
    try:
        payload = challenge.model_dump(exclude_none=True)
        created = service.create_challenge(payload, current_user)
        return {
            "success": True,
            "message": "Challenge submitted successfully",
            "data": created,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit challenge: {str(e)}",
        )


# -----------------------------------------------------------------------------
# 2. GET /api/challenges — List Challenges
# -----------------------------------------------------------------------------
@router.get(
    "",
    summary="List challenges with optional filtering",
)
def list_challenges(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    city: Optional[str] = Query(None, description="Filter by city"),
    user_id: Optional[str] = Query(None, description="Filter by submitting user ID"),
    limit: int = Query(100, ge=1, le=500),
    service: ChallengeService = Depends(get_challenge_service),
):
    """Lists challenges ordered by created_at descending."""
    try:
        data = service.list_challenges(
            status_filter=status_filter,
            city_filter=city,
            user_id_filter=user_id,
            limit=limit,
        )
        return {
            "success": True,
            "data": data,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch challenges: {str(e)}",
        )


# -----------------------------------------------------------------------------
# 2b. GET /api/challenges/universities/{university_id}/invitations
# -----------------------------------------------------------------------------
@router.get(
    "/universities/{university_id}/invitations",
    summary="List challenge match invitations for a university",
)
def list_university_invitations(
    university_id: str,
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    current_user: AuthenticatedUser = Depends(get_current_user),
    service=Depends(get_workflow_service),
):
    """Lists match invitations for a university with hydrated challenge and AI details."""
    try:
        data = service.list_university_invitations(
            university_id=university_id,
            user=current_user,
            status_filter=status_filter,
        )
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
            detail=f"Failed to fetch university invitations: {str(e)}",
        )


# -----------------------------------------------------------------------------
# 2c. GET /api/challenges/industries/{industry_id}/invitations
# -----------------------------------------------------------------------------
@router.get(
    "/industries/{industry_id}/invitations",
    summary="List challenge collaboration requests for an industry",
)
def list_industry_invitations(
    industry_id: str,
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    current_user: AuthenticatedUser = Depends(get_current_user),
    service=Depends(get_industry_workflow_service),
):
    """Lists collaboration requests for an industry with hydrated challenge and AI details."""
    try:
        data = service.list_industry_invitations(
            industry_id=industry_id,
            user=current_user,
            status_filter=status_filter,
        )
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
            detail=f"Failed to fetch industry invitations: {str(e)}",
        )


# -----------------------------------------------------------------------------
# 3. GET /api/challenges/{challenge_id} — Single Challenge with AI Analysis
# -----------------------------------------------------------------------------
@router.get(
    "/{challenge_id}",
    summary="Get challenge details with hydrated AI analysis",
)
def get_challenge(
    challenge_id: str,
    service: ChallengeService = Depends(get_challenge_service),
):
    """Retrieves single challenge by ID and hydrates associated ai_analysis record if available."""
    try:
        data = service.get_challenge(challenge_id)
        return {
            "success": True,
            "data": data,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch challenge '{challenge_id}': {str(e)}",
        )


# -----------------------------------------------------------------------------
# 4. POST /api/challenges/{challenge_id}/analyze — AI Review & Discovery (Call 1)
# -----------------------------------------------------------------------------
@router.post(
    "/{challenge_id}/analyze",
    summary="Trigger AI review and existing-solution discovery (LLM Call 1)",
)
def analyze_challenge(
    challenge_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: ChallengeService = Depends(get_challenge_service),
):
    """Executes Call 1 of the AI review pipeline:

    - Evaluates validity, societal value, feasibility, and duplicates.
    - Searches verified real solutions without hallucinations.
    - If found: persists evidence and sets status to 'existing_solution_found'.
    - If not found: classifies problem in Call 1, setting status to 'validated' (max 1 call used).
    - Enforces challenge ownership and prevents redundant analysis calls.
    """
    try:
        result = service.analyze_challenge(challenge_id, current_user)
        return {
            "success": True,
            "data": result,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed for challenge '{challenge_id}': {str(e)}",
        )


# -----------------------------------------------------------------------------
# 5. POST /api/challenges/{challenge_id}/existing-solution-response — Citizen Decision
# -----------------------------------------------------------------------------
@router.post(
    "/{challenge_id}/existing-solution-response",
    summary="Citizen response to discovered solution (Call 2 if rejected)",
)
def handle_existing_solution_response(
    challenge_id: str,
    decision: ExistingSolutionDecisionRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: ChallengeService = Depends(get_challenge_service),
):
    """Processes citizen response to an existing solution:

    - If accepted: marks challenge resolved via existing solution. Closes workflow. (0 extra calls)
    - If rejected: triggers Call 2 to evaluate gap validity (unavailability, cost, coverage, etc.)
      and classify the problem into 'validated' for university/industry matching. (1 extra call)
    - Strict 2-call maximum per challenge budget maintained.
    """
    try:
        result = service.handle_existing_solution_response(
            challenge_id=challenge_id,
            user=current_user,
            accepted=decision.is_accepted,
            rejection_reason=decision.effective_rejection_reason,
            rejection_category=decision.rejection_category,
        )
        return {
            "success": True,
            "data": result,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process existing solution decision: {str(e)}",
        )


def get_matching_service():
    """Dependency provider for MatchingService."""
    from app.services.matching_service import MatchingService
    return MatchingService()


# -----------------------------------------------------------------------------
# 6. GET /api/challenges/{challenge_id}/universities — Deterministic University Matches
# -----------------------------------------------------------------------------
@router.get(
    "/{challenge_id}/universities",
    summary="Get deterministically ranked university matches for a challenge",
)
def get_challenge_university_matches(
    challenge_id: str,
    limit: int = Query(5, ge=1, le=20),
    current_user: AuthenticatedUser = Depends(get_current_user),
    service=Depends(get_matching_service),
):
    """Calculates or retrieves deterministically ranked university matches

    from challenge_university_matches according to weights:
    skills 25%, technologies 25%, research 15%, domain 10%, primary_focus 10%,
    departments 5%, facilities 3%, past_projects 2%.
    """
    try:
        matches = service.get_or_generate_university_matches(
            challenge_id=challenge_id,
            user=current_user,
            limit=limit,
        )
        return {
            "success": True,
            "challenge_id": challenge_id,
            "total_matches": len(matches),
            "data": matches,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get university matches: {str(e)}",
        )


# -----------------------------------------------------------------------------
# 7. GET /api/challenges/{challenge_id}/industries — Deterministic Industry Matches
# -----------------------------------------------------------------------------
@router.get(
    "/{challenge_id}/industries",
    summary="Get deterministically ranked industry matches for a challenge",
)
def get_challenge_industry_matches(
    challenge_id: str,
    limit: int = Query(5, ge=1, le=20),
    current_user: AuthenticatedUser = Depends(get_current_user),
    service=Depends(get_matching_service),
):
    """Calculates or retrieves deterministically ranked industry matches

    from challenge_industry_matches according to weights:
    skills 22%, technologies 22%, domain 15%, deployment 12%, resources 10%,
    products_services 8%, geography 5%, CSR 3%, past_projects 3%.
    """
    try:
        matches = service.get_or_generate_industry_matches(
            challenge_id=challenge_id,
            user=current_user,
            limit=limit,
        )
        return {
            "success": True,
            "challenge_id": challenge_id,
            "total_matches": len(matches),
            "data": matches,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get industry matches: {str(e)}",
        )




# -----------------------------------------------------------------------------
# 8. POST /api/challenges/{challenge_id}/universities/{university_id}/respond — Admin Decision
# -----------------------------------------------------------------------------
@router.post(
    "/{challenge_id}/universities/{university_id}/respond",
    summary="University administrator provisional response (accept/reject) to match",
)
def respond_to_university_match(
    challenge_id: str,
    university_id: str,
    decision: UniversityResponseRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service=Depends(get_workflow_service),
):
    """Processes university administrator acceptance or rejection of a challenge match.

    Validates:
    - User is authenticated and verified university_admin
    - Admin belongs to the relevant university_id
    - Challenge and match exist
    - Match status is in ['recommended', 'invited']
    - Acceptance is provisional until deadline / selection finalization
    """
    try:
        result = service.respond_to_university_match(
            challenge_id=challenge_id,
            university_id=university_id,
            action=decision.action,
            user=current_user,
            response_note=decision.response_note,
        )
        return {
            "success": True,
            "data": result,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record university response: {str(e)}",
        )


# -----------------------------------------------------------------------------
# 9. POST /api/challenges/{challenge_id}/universities/finalize-selection — Highest-Ranked Selection
# -----------------------------------------------------------------------------
@router.post(
    "/{challenge_id}/universities/finalize-selection",
    summary="Evaluate response window and select the highest-ranked accepted university",
)
def finalize_university_selection(
    challenge_id: str,
    request_data: Optional[FinalizeSelectionRequest] = None,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service=Depends(get_workflow_service),
):
    """Executes the Phase 5 selection rule:

    The highest-ranked accepted university is selected after the response deadline.
    - Selected university status becomes 'selected'
    - Other eligible candidate matches become 'not_selected'
    - Challenge status becomes 'university_selected'
    """
    try:
        force = request_data.force_deadline if request_data else False
        result = service.finalize_university_selection(
            challenge_id=challenge_id,
            user=current_user,
            force_deadline=force,
        )
        return {
            "success": True,
            "data": result,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to finalize university selection: {str(e)}",
        )




# -----------------------------------------------------------------------------
# 10. POST /api/challenges/{challenge_id}/industries/{industry_id}/respond — SPOC Decision
# -----------------------------------------------------------------------------
@router.post(
    "/{challenge_id}/industries/{industry_id}/respond",
    summary="Industry SPOC response (accept/reject) to industry match",
)
def respond_to_industry_match(
    challenge_id: str,
    industry_id: str,
    decision: IndustryCollaborationResponse,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service=Depends(get_industry_workflow_service),
):
    """Processes Industry SPOC acceptance or rejection of a challenge match.

    Validates:
    - User is authenticated and verified industry_employee (or government)
    - User has approval_authority = TRUE (Designation alone does NOT confer permission)
    - SPOC strictly belongs to the specified industry_id
    - Challenge and match records exist in the database
    - Updates match status to 'accepted' or 'rejected'
    - Associates industry with active project if already created
    """
    try:
        result = service.respond_to_industry_match(
            challenge_id=challenge_id,
            industry_id=industry_id,
            action=decision.action,
            response_note=decision.response_note,
            user=current_user,
        )
        return {
            "success": True,
            "message": f"Industry collaboration proposal successfully marked as '{result.get('status')}'.",
            "data": result,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record industry collaboration decision: {str(e)}",
        )



