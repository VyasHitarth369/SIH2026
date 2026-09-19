"""projects.py

Routes for Project Creation, Faculty Allocation, and Collaborative Project Lifecycle
Management (Phase 5).
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies.auth import get_current_user, get_current_user_optional
from app.schemas.industry import (
    EmployeeInterestCreate,
    EmployeeInterestUpdate,
    EmployeeInterestResponse,
)
from app.schemas.project import (
    FacultyAssignRequest,
    MemberStatusUpdate,
    MilestoneCreate,
    MilestoneResponse,
    ProjectCreate,
    ProjectMemberAdd,
    ProjectMemberResponse,
    ProjectMilestoneStatusUpdate,
    ProjectResponse,
    StudentInterestCreate,
)
from app.services.auth_service import AuthenticatedUser
from app.services.industry_workflow_service import IndustryWorkflowService
from app.services.project_workflow_service import ProjectWorkflowService
from app.services.university_workflow_service import UniversityWorkflowService
from app.services.feedback_service import FeedbackService
from app.schemas.feedback import (
    FeedbackCreate,
    FeedbackResponse,
    ProjectStatusTransition,
    ProjectImpactResponse,
)

router = APIRouter(prefix="/api/projects", tags=["Projects & Faculty Allocation"])


def get_workflow_service() -> UniversityWorkflowService:
    """Dependency provider for UniversityWorkflowService."""
    return UniversityWorkflowService()


def get_project_workflow_service() -> ProjectWorkflowService:
    """Dependency provider for ProjectWorkflowService."""
    return ProjectWorkflowService()


def get_industry_workflow_service() -> IndustryWorkflowService:
    """Dependency provider for IndustryWorkflowService."""
    return IndustryWorkflowService()


def get_feedback_service() -> FeedbackService:
    """Dependency provider for FeedbackService."""
    return FeedbackService()



# -----------------------------------------------------------------------------
# 1. POST /api/projects — Create Project & Allocate Faculty
# -----------------------------------------------------------------------------
@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Create a new collaborative project with allocated faculty",
)
def create_project(
    project_in: ProjectCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: UniversityWorkflowService = Depends(get_workflow_service),
):
    """Creates a project upon official university selection and faculty allocation.

    Validates:
    - User is a verified administrator for the university
    - University is the 'selected' university for the challenge
    - Faculty strictly belongs to the selected university
    - Project status defaults to 'proposed'
    """
    try:
        payload = project_in.model_dump(exclude_none=True)
        created = service.create_project(payload, current_user)
        return {
            "success": True,
            "message": "Project created successfully with allocated faculty",
            "data": created,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create project: {str(e)}",
        )


# -----------------------------------------------------------------------------
# 2. GET /api/projects — List Projects
# -----------------------------------------------------------------------------
@router.get(
    "",
    summary="List collaborative projects with role-aware visibility",
)
def list_projects(
    university_id: Optional[str] = Query(None, description="Filter by university ID"),
    faculty_id: Optional[str] = Query(None, description="Filter by allocated faculty ID"),
    challenge_id: Optional[str] = Query(None, description="Filter by challenge ID"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by project lifecycle status"),
    limit: int = Query(100, ge=1, le=500),
    my_projects: bool = Query(False, description="Filter to projects where current student is an enrolled member"),
    approved_only: bool = Query(False, description="Filter to approved/active projects"),
    current_user: Optional[AuthenticatedUser] = Depends(get_current_user_optional),
    uni_service: UniversityWorkflowService = Depends(get_workflow_service),
    proj_service: ProjectWorkflowService = Depends(get_project_workflow_service),
):
    """Lists projects matching filter criteria, with role-based scoping when authenticated."""
    try:
        if current_user:
            data = proj_service.list_projects_for_user(
                user=current_user,
                university_id=university_id,
                faculty_id=faculty_id,
                challenge_id=challenge_id,
                status_filter=status_filter,
                limit=limit,
                my_projects=my_projects,
                approved_only=approved_only,
            )
        else:
            data = uni_service.list_projects(
                university_id=university_id,
                faculty_id=faculty_id,
                challenge_id=challenge_id,
                status_filter=status_filter,
                limit=limit,
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
            detail=f"Failed to list projects: {str(e)}",
        )


# -----------------------------------------------------------------------------
# 2b. GET /api/projects/eligible-for-employee — List Projects for Employee Industry
# -----------------------------------------------------------------------------
@router.get(
    "/eligible-for-employee",
    summary="List collaborative projects partnered with employee's industry",
)
def list_eligible_projects_for_employee(
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: IndustryWorkflowService = Depends(get_industry_workflow_service),
):
    """Lists active and prototype projects partnered with the authenticated employee's industry."""
    try:
        data = service.list_eligible_projects_for_employee(current_user)
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
            detail=f"Failed to list eligible projects for employee: {str(e)}",
        )


# -----------------------------------------------------------------------------
# 2c. GET /api/projects/certificates — List Certificates for Student
# -----------------------------------------------------------------------------
@router.get(
    "/certificates",
    summary="List certificate eligibility for authenticated student",
)
def list_certificates(
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: ProjectWorkflowService = Depends(get_project_workflow_service),
):
    """Lists all projects for the authenticated student with certificate eligibility and status."""
    try:
        data = service.list_student_certificates(current_user)
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
            detail=f"Failed to list certificates: {str(e)}",
        )


# -----------------------------------------------------------------------------
# 2d. GET /api/projects/{project_id}/certificate — Single Project Certificate
# -----------------------------------------------------------------------------
@router.get(
    "/{project_id}/certificate",
    summary="Get and verify E-Certificate for completed project",
)
def get_project_certificate(
    project_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: ProjectWorkflowService = Depends(get_project_workflow_service),
):
    """Retrieves authoritative E-Certificate for a project that reached 'Solution Deployed'.
    Strictly enforces:
    - User is enrolled member on the project
    - Project status is 'deployed', 'solved', or 'completed'
    """
    try:
        cert = service.get_project_certificate(project_id, current_user)
        return {
            "success": True,
            "message": "Certificate retrieved successfully",
            "data": cert,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve certificate: {str(e)}",
        )


# -----------------------------------------------------------------------------
# 3. GET /api/projects/{project_id} — Single Project Details
# -----------------------------------------------------------------------------
@router.get(
    "/{project_id}",
    summary="Get project details with hydrated relations",
)
def get_project(
    project_id: str,
    service: UniversityWorkflowService = Depends(get_workflow_service),
):
    """Retrieves a single project with hydrated university, faculty, and challenge details."""
    try:
        project = service.get_project(project_id)
        return {
            "success": True,
            "data": project,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch project '{project_id}': {str(e)}",
        )


# -----------------------------------------------------------------------------
# 4. POST /api/projects/{project_id}/members — Add Student Member
# -----------------------------------------------------------------------------
@router.post(
    "/{project_id}/members",
    status_code=status.HTTP_201_CREATED,
    summary="Add an enrolled university student to the project",
)
def add_project_member(
    project_id: str,
    member_in: ProjectMemberAdd,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: ProjectWorkflowService = Depends(get_project_workflow_service),
):
    """Adds an enrolled student to the project.

    Enforces:
    - User must be assigned faculty, university admin, or government
    - Student must belong to the project's university (no cross-university student assignment)
    - Duplicate active membership is rejected
    """
    try:
        res = service.add_project_member(
            project_id=project_id,
            student_id=member_in.student_id,
            role=member_in.role or "member",
            user=current_user,
        )
        return {
            "success": True,
            "message": "Student successfully added to project",
            "data": res,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add member to project: {str(e)}",
        )


# -----------------------------------------------------------------------------
# 5. GET /api/projects/{project_id}/members — List Project Members
# -----------------------------------------------------------------------------
@router.get(
    "/{project_id}/members",
    summary="List student team members on a project",
)
def list_project_members(
    project_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: ProjectWorkflowService = Depends(get_project_workflow_service),
):
    """Lists student members belonging to the specified project."""
    try:
        members = service.list_project_members(project_id, current_user)
        return {
            "success": True,
            "total": len(members),
            "data": members,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list members for project '{project_id}': {str(e)}",
        )


# -----------------------------------------------------------------------------
# 6. DELETE /api/projects/{project_id}/members/{student_id} — Remove Member
# -----------------------------------------------------------------------------
@router.delete(
    "/{project_id}/members/{student_id}",
    summary="Remove a student member from a project",
)
def remove_project_member(
    project_id: str,
    student_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: ProjectWorkflowService = Depends(get_project_workflow_service),
):
    """Marks a student member as removed. Requires assigned faculty or university admin."""
    try:
        res = service.remove_project_member(project_id, student_id, current_user)
        return {
            "success": True,
            "message": "Student successfully removed from project",
            "data": res,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove member: {str(e)}",
        )


# -----------------------------------------------------------------------------
# 6b. POST /api/projects/{project_id}/student-interest — Express Interest
# -----------------------------------------------------------------------------
@router.post(
    "/{project_id}/student-interest",
    status_code=status.HTTP_201_CREATED,
    summary="Express interest as an enrolled university student in an active project",
)
def express_student_interest(
    project_id: str,
    interest_in: Optional[StudentInterestCreate] = None,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: ProjectWorkflowService = Depends(get_project_workflow_service),
):
    """Enrolled university students express interest in eligible projects."""
    try:
        role = interest_in.role if interest_in else "applicant"
        res = service.express_student_interest(
            project_id=project_id,
            role=role,
            user=current_user,
        )
        return {
            "success": True,
            "message": "Student interest expressed successfully.",
            "data": res,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to express student interest: {str(e)}",
        )


# -----------------------------------------------------------------------------
# 6c. PATCH /api/projects/{project_id}/members/{student_id} — Faculty Select/Reject Student
# -----------------------------------------------------------------------------
@router.patch(
    "/{project_id}/members/{student_id}",
    summary="Update student membership status (faculty/admin selects or rejects student)",
)
def update_student_member_status(
    project_id: str,
    student_id: str,
    status_in: MemberStatusUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: ProjectWorkflowService = Depends(get_project_workflow_service),
):
    """Faculty reviews and selects/rejects student applicants."""
    try:
        res = service.update_project_member_status(
            project_id=project_id,
            student_id=student_id,
            new_status=status_in.status,
            user=current_user,
        )
        return {
            "success": True,
            "message": f"Student status updated to '{status_in.status}'.",
            "data": res,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update student member status: {str(e)}",
        )


# -----------------------------------------------------------------------------
# 6d. PATCH /api/projects/{project_id}/faculty — University Admin Allocate Faculty
# -----------------------------------------------------------------------------
@router.patch(
    "/{project_id}/faculty",
    summary="Allocate or reassign faculty for a project (University Admin)",
)
def allocate_project_faculty(
    project_id: str,
    faculty_in: FacultyAssignRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: ProjectWorkflowService = Depends(get_project_workflow_service),
):
    """University Administrator assigns eligible faculty to a project."""
    try:
        res = service.assign_faculty(
            project_id=project_id,
            faculty_id=faculty_in.faculty_id,
            user=current_user,
        )
        return {
            "success": True,
            "message": "Faculty allocated to project successfully.",
            "data": res,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to allocate faculty: {str(e)}",
        )


# -----------------------------------------------------------------------------
# 6e. GET /api/projects/university/faculty — Authoritative University Faculty List
# -----------------------------------------------------------------------------
@router.get(
    "/university/faculty",
    summary="List authoritative faculty belonging to the authenticated administrator's university",
)
def list_my_university_faculty(
    current_user: AuthenticatedUser = Depends(get_current_user),
    uni_service: UniversityWorkflowService = Depends(get_workflow_service),
):
    """Returns faculty records for the authenticated university administrator."""
    try:
        data = uni_service.list_university_faculty(current_user)
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
            detail=f"Failed to fetch university faculty: {str(e)}",
        )


# -----------------------------------------------------------------------------
# 6f. GET /api/projects/university/mous — Authoritative University MOU Records
# -----------------------------------------------------------------------------
@router.get(
    "/university/mous",
    summary="List MOU collaboration records for the authenticated administrator's university",
)
def list_my_university_mous(
    current_user: AuthenticatedUser = Depends(get_current_user),
    uni_service: UniversityWorkflowService = Depends(get_workflow_service),
):
    """Returns MOU collaboration records for the authenticated university administrator."""
    try:
        data = uni_service.list_university_mous(current_user)
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
            detail=f"Failed to fetch university MOUs: {str(e)}",
        )


# -----------------------------------------------------------------------------
# 7. GET /api/projects/{project_id}/milestones — List Project Milestones
# -----------------------------------------------------------------------------
@router.get(
    "/{project_id}/milestones",
    summary="List milestones for a project",
)
def list_project_milestones(
    project_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: ProjectWorkflowService = Depends(get_project_workflow_service),
):
    """Retrieves all milestone records associated with a project."""
    try:
        data = service.list_milestones(project_id, current_user)
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
            detail=f"Failed to list milestones for project '{project_id}': {str(e)}",
        )


# -----------------------------------------------------------------------------
# 8. POST /api/projects/{project_id}/milestones — Create Project Milestone
# -----------------------------------------------------------------------------
@router.post(
    "/{project_id}/milestones",
    status_code=status.HTTP_201_CREATED,
    summary="Create a new milestone for a project",
)
def create_project_milestone(
    project_id: str,
    milestone_in: MilestoneCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: ProjectWorkflowService = Depends(get_project_workflow_service),
):
    """Creates a milestone for the project.

    Enforces:
    - User has project access (faculty, admin, or project member)
    - completion_percentage is strictly 0-100
    - If assigned_to is provided, verifies assignee belongs to project
    """
    try:
        payload = milestone_in.model_dump(exclude_none=True)
        created = service.create_milestone(project_id, payload, current_user)
        return {
            "success": True,
            "message": "Milestone created successfully",
            "data": created,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create milestone: {str(e)}",
        )


# -----------------------------------------------------------------------------
# 8b. PATCH /api/projects/{project_id}/milestone — Update Standardized Milestone
# -----------------------------------------------------------------------------
@router.patch(
    "/{project_id}/milestone",
    summary="Update standardized 7-stage project milestone for assigned faculty",
)
def update_standardized_milestone(
    project_id: str,
    milestone_in: ProjectMilestoneStatusUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: ProjectWorkflowService = Depends(get_project_workflow_service),
):
    """Allows assigned faculty to advance milestone along the authoritative 7-stage sequence.

    Enforces:
    - User is authenticated assigned faculty for this project (HTTP 403)
    - Completed projects ("Solution Deployed") cannot be edited (HTTP 400)
    - Backward progression is blocked (HTTP 400)
    - Skipping required stages is blocked (HTTP 400)
    - Specifically allows Student Team Formed -> Development In Progress
    - Specifically allows Development In Progress -> Solution Deployed
    """
    try:
        res = service.update_project_standardized_milestone(
            project_id=project_id,
            milestone_input=milestone_in.milestone,
            user=current_user,
        )
        return {
            "success": True,
            "message": res.get("message", "Project milestone updated successfully."),
            "data": res,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update milestone: {str(e)}",
        )


# -----------------------------------------------------------------------------
# 9. POST /api/projects/{project_id}/employee-interest — Express Interest
# -----------------------------------------------------------------------------
@router.post(
    "/{project_id}/employee-interest",
    status_code=status.HTTP_201_CREATED,
    summary="Express interest as a verified industry employee in an innovation project",
)
def express_employee_interest(
    project_id: str,
    interest_in: Optional[EmployeeInterestCreate] = None,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: IndustryWorkflowService = Depends(get_industry_workflow_service),
):
    """Allows an eligible verified industry employee to express interest in a project.

    Enforces:
    - User is authenticated and verified with role 'industry_employee'
    - Employee strictly belongs to the project's allocated industry partner
    - Prevents duplicate active interest expressions (duplicate -> 400 Bad Request)
    - Note: Employee interest != official project assignment.
    """
    try:
        msg = interest_in.message if interest_in else None
        res = service.express_employee_interest(
            project_id=project_id,
            message=msg,
            user=current_user,
        )
        return {
            "success": True,
            "message": "Employee interest expressed successfully.",
            "data": res,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to express employee interest: {str(e)}",
        )


# -----------------------------------------------------------------------------
# 10. GET /api/projects/{project_id}/employee-interests — List Interests
# -----------------------------------------------------------------------------
@router.get(
    "/{project_id}/employee-interests",
    summary="List employee interest expressions for a project",
)
def list_employee_interests(
    project_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: IndustryWorkflowService = Depends(get_industry_workflow_service),
):
    """Lists employee interest records on a project with hydrated employee details."""
    try:
        interests = service.list_employee_interests(project_id, current_user)
        return {
            "success": True,
            "total": len(interests),
            "data": interests,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list employee interests for project '{project_id}': {str(e)}",
        )


# -----------------------------------------------------------------------------
# 11. PATCH /api/projects/{project_id}/employee-interests/{interest_id} — SPOC Selection / Withdraw
# -----------------------------------------------------------------------------
@router.patch(
    "/{project_id}/employee-interests/{interest_id}",
    summary="Update employee interest status (SPOC selects/rejects or employee withdraws)",
)
def update_employee_interest(
    project_id: str,
    interest_id: int,
    patch: EmployeeInterestUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: IndustryWorkflowService = Depends(get_industry_workflow_service),
):
    """Updates interest status: 'selected', 'not_selected', or 'withdrawn'.

    Enforces:
    - 'selected' / 'not_selected': strictly restricted to verified Industry SPOC (approval_authority=True)
    - Anti-Self-Selection: An employee cannot select themselves!
    - Employee must belong to the correct industry
    - 'withdrawn': can be triggered by the applicant employee or their Industry SPOC
    """
    try:
        res = service.update_employee_interest_status(
            project_id=project_id,
            interest_id=interest_id,
            new_status=patch.status,
            note=patch.note,
            user=current_user,
        )
        return {
            "success": True,
            "message": f"Employee interest status updated to '{patch.status}'.",
            "data": res,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update employee interest '{interest_id}': {str(e)}",
        )


# -----------------------------------------------------------------------------
# 12. POST /api/projects/{project_id}/feedback — Submit Stakeholder Feedback
# -----------------------------------------------------------------------------
@router.post(
    "/{project_id}/feedback",
    status_code=status.HTTP_201_CREATED,
    summary="Submit qualitative, quantitative, and outcome feedback for a project",
)
def submit_feedback(
    project_id: str,
    feedback_in: FeedbackCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: FeedbackService = Depends(get_feedback_service),
):
    """Submits stakeholder feedback and real-world outcomes for a project.

    Enforces:
    - Authenticated user with legitimate platform role
    - 1 to 5 rating scale
    - Submitter eligibility per role (resident citizens, active students, assigned faculty, etc.)
    - Duplicate prevention: prevents multiple spam feedback submissions
    - Matches challenge_id against project
    """
    try:
        payload = feedback_in.model_dump(exclude_none=True)
        res = service.submit_feedback(
            project_id=project_id,
            payload=payload,
            user=current_user,
        )
        return {
            "success": True,
            "message": "Feedback submitted successfully.",
            "data": res,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit feedback: {str(e)}",
        )


# -----------------------------------------------------------------------------
# 13. GET /api/projects/{project_id}/feedback — List Project Feedback
# -----------------------------------------------------------------------------
@router.get(
    "/{project_id}/feedback",
    summary="List feedback entries for a project with role-appropriate privacy",
)
def list_feedback(
    project_id: str,
    current_user: Optional[AuthenticatedUser] = Depends(get_current_user_optional),
    service: FeedbackService = Depends(get_feedback_service),
):
    """Retrieves all validated feedback records for a project."""
    try:
        feedback_list = service.list_project_feedback(
            project_id=project_id,
            user=current_user,
        )
        return {
            "success": True,
            "total": len(feedback_list),
            "data": feedback_list,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list feedback for project '{project_id}': {str(e)}",
        )


# -----------------------------------------------------------------------------
# 14. PATCH /api/projects/{project_id}/status — Advance Project Lifecycle
# -----------------------------------------------------------------------------
@router.patch(
    "/{project_id}/status",
    summary="Advance project through legitimate lifecycle stages",
)
def update_project_status(
    project_id: str,
    status_in: ProjectStatusTransition,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: FeedbackService = Depends(get_feedback_service),
):
    """Advances project lifecycle:
    proposed -> active -> prototype -> pilot -> deployed -> solved -> completed.

    Enforces:
    - Caller must be Assigned Faculty, University Admin, Industry SPOC, or Government
    - Students and general citizens are strictly blocked (403 Forbidden)
    - Valid sequential forward transitions (no arbitrary leaps)
    - Reaching 'solved' or 'completed' requires verified milestones or feedback
    - Automatically marks linked challenge as 'resolved' and records actual_end_date
    """
    try:
        res = service.update_project_status(
            project_id=project_id,
            new_status=status_in.status,
            justification=status_in.justification,
            user=current_user,
        )
        return {
            "success": True,
            "message": f"Project successfully advanced to '{status_in.status}'.",
            "data": res,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update project status: {str(e)}",
        )


# -----------------------------------------------------------------------------
# 15. GET /api/projects/{project_id}/impact — Role-Tailored Impact Summary
# -----------------------------------------------------------------------------
@router.get(
    "/{project_id}/impact",
    summary="Retrieve role-tailored outcome and impact tracking intelligence",
)
def get_project_impact(
    project_id: str,
    current_user: Optional[AuthenticatedUser] = Depends(get_current_user_optional),
    service: FeedbackService = Depends(get_feedback_service),
):
    """Provides structured outcome and impact metrics tailored to the requesting stakeholder."""
    try:
        impact_data = service.get_project_impact_summary(
            project_id=project_id,
            user=current_user,
        )
        return {
            "success": True,
            "data": impact_data,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve impact summary for project '{project_id}': {str(e)}",
        )


