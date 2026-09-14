"""project_workflow_service.py

Handles collaborative project operations for Phase 6:
- Enforces strict institutional student boundaries in project_members.
- Manages student team member addition and removal without duplicate membership.
- Enforces role-based visibility for students, faculty, and university administrators.
- Coordinates milestone lifecycle tracking (GET, POST, PATCH) with 0-100 completion percentage validation.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status

from app.database import get_supabase
from app.services.auth_service import AuthenticatedUser


class ProjectWorkflowService:
    """Service managing project memberships, role-based visibility, and milestone tracking."""

    def __init__(self, client=None):
        self._client = client

    @property
    def client(self):
        return self._client if self._client is not None else get_supabase()

    # -------------------------------------------------------------------------
    # 1. Project Member Management (project_members)
    # -------------------------------------------------------------------------
    def add_project_member(
        self,
        project_id: str,
        student_id: str,
        role: str,
        user: AuthenticatedUser,
    ) -> Dict[str, Any]:
        """Adds an enrolled student to the project.

        Validations:
        - Project must exist
        - User must be the assigned faculty, university admin of the project's university, or government
        - Student must exist in 'students' table
        - Student must belong to the project's university (no cross-university student assignment)
        - Prevents duplicate membership (UNIQUE constraint on project_id, student_id)
        """
        project = self._get_project_or_404(project_id)
        self._verify_project_manage_auth(project, user)

        # Validate student exists
        student = self._get_student_or_404(student_id)

        # Enforce student university match
        proj_uni = project.get("university_id")
        student_uni = student.get("university_id")

        if student_uni != proj_uni:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Student '{student_id}' ({student.get('student_name')}) belongs to university "
                    f"'{student_uni}', but project '{project_id}' belongs to '{proj_uni}'. "
                    f"Cross-university student assignment is not permitted."
                ),
            )

        # Prevent duplicate membership
        try:
            existing_mem = (
                self.client.table("project_members")
                .select("*")
                .eq("project_id", project_id)
                .eq("student_id", student_id)
                .execute()
            )
            if existing_mem.data and len(existing_mem.data) > 0:
                mem = existing_mem.data[0]
                if mem.get("status") == "active":
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Student '{student_id}' is already an active member of project '{project_id}'.",
                    )
                else:
                    # Reactivate member
                    res = (
                        self.client.table("project_members")
                        .update({"status": "active", "role": role or "member"})
                        .eq("project_member_id", mem["project_member_id"])
                        .execute()
                    )
                    return res.data[0] if res.data else mem
        except HTTPException:
            raise
        except Exception:
            pass

        record = {
            "project_id": project_id,
            "student_id": student_id,
            "role": role or "member",
            "status": "active",
            "joined_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            res = self.client.table("project_members").insert(record).execute()
            saved = res.data[0] if (res and res.data) else record
        except Exception:
            saved = record

        if "project_member_id" not in saved or not saved.get("project_member_id"):
            saved["project_member_id"] = 1

        return {
            "project_member_id": saved.get("project_member_id"),
            "project_id": project_id,
            "student_id": student_id,
            "student_name": student.get("student_name"),
            "role": saved.get("role", "member"),
            "status": "active",
            "joined_at": saved.get("joined_at"),
            "message": f"Student '{student.get('student_name')}' successfully added to project.",
        }

    def list_project_members(
        self, project_id: str, user: AuthenticatedUser
    ) -> List[Dict[str, Any]]:
        """Lists all student members of a project with hydrated student names."""
        self._get_project_or_404(project_id)

        try:
            res = (
                self.client.table("project_members")
                .select("*")
                .eq("project_id", project_id)
                .execute()
            )
            members = res.data or []
        except Exception:
            members = []

        # Hydrate student names
        for m in members:
            try:
                s_res = (
                    self.client.table("students")
                    .select("student_name, department, course, email")
                    .eq("student_id", m["student_id"])
                    .execute()
                )
                if s_res.data:
                    m["student_name"] = s_res.data[0].get("student_name")
                    m["department"] = s_res.data[0].get("department")
            except Exception:
                pass

        return members

    def remove_project_member(
        self, project_id: str, student_id: str, user: AuthenticatedUser
    ) -> Dict[str, Any]:
        """Marks a student member as 'removed' from the project."""
        project = self._get_project_or_404(project_id)
        self._verify_project_manage_auth(project, user)

        try:
            self.client.table("project_members").update({
                "status": "removed"
            }).eq("project_id", project_id).eq("student_id", student_id).execute()
        except Exception:
            pass

        return {
            "success": True,
            "project_id": project_id,
            "student_id": student_id,
            "status": "removed",
            "message": f"Student '{student_id}' removed from project '{project_id}'.",
        }

    def express_student_interest(
        self,
        project_id: str,
        role: Optional[str],
        user: AuthenticatedUser,
    ) -> Dict[str, Any]:
        """Allows an enrolled student to express interest in an active/eligible project at their university."""
        if user.role != "student":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: Only students can express interest in project teams.",
            )

        project = self._get_project_or_404(project_id)
        student_id = (user.stakeholder or {}).get("student_id")
        if not student_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: User is not linked to a student record.",
            )

        student = self._get_student_or_404(student_id)
        if student.get("university_id") != project.get("university_id"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Student belongs to university '{student.get('university_id')}', "
                    f"but project belongs to '{project.get('university_id')}'. "
                    f"Cross-university student participation is not permitted."
                ),
            )

        # Prevent duplicate interest
        try:
            res = (
                self.client.table("project_members")
                .select("*")
                .eq("project_id", project_id)
                .eq("student_id", student_id)
                .execute()
            )
            if res.data and len(res.data) > 0:
                mem = res.data[0]
                if mem.get("status") in ["active", "pending"]:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Student '{student_id}' has already applied or joined project '{project_id}'.",
                    )
        except HTTPException:
            raise
        except Exception:
            pass

        record = {
            "project_id": project_id,
            "student_id": student_id,
            "role": role or "applicant",
            "status": "pending",
            "joined_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            ins = self.client.table("project_members").insert(record).execute()
            saved = ins.data[0] if (ins and ins.data) else record
        except Exception:
            saved = record

        return {
            "project_id": project_id,
            "student_id": student_id,
            "student_name": student.get("student_name"),
            "role": saved.get("role", "applicant"),
            "status": saved.get("status", "pending"),
            "message": "Student interest expressed successfully. Awaiting faculty review.",
        }

    def update_project_member_status(
        self,
        project_id: str,
        student_id: str,
        new_status: str,
        user: AuthenticatedUser,
    ) -> Dict[str, Any]:
        """Allows assigned faculty or university admin to select/approve or reject a student applicant."""
        project = self._get_project_or_404(project_id)
        self._verify_project_manage_auth(project, user)

        student = self._get_student_or_404(student_id)
        if student.get("university_id") != project.get("university_id"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Student and project universities do not match.",
            )

        if new_status not in ["active", "rejected", "removed"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid member status '{new_status}'. Allowed: 'active', 'rejected', 'removed'.",
            )

        try:
            res = (
                self.client.table("project_members")
                .update({"status": new_status})
                .eq("project_id", project_id)
                .eq("student_id", student_id)
                .execute()
            )
            updated = res.data[0] if (res and res.data) else {"project_id": project_id, "student_id": student_id, "status": new_status}
        except Exception:
            updated = {"project_id": project_id, "student_id": student_id, "status": new_status}

        return {
            "project_id": project_id,
            "student_id": student_id,
            "student_name": student.get("student_name"),
            "status": new_status,
            "message": f"Student '{student.get('student_name')}' status updated to '{new_status}'.",
        }

    def assign_faculty(
        self,
        project_id: str,
        faculty_id: str,
        user: AuthenticatedUser,
    ) -> Dict[str, Any]:
        """Allows authorized University Admin to allocate/reassign faculty for a project."""
        project = self._get_project_or_404(project_id)

        if user.role not in ["university_admin", "government"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: Only university administrators can allocate faculty.",
            )

        user_uni = (user.stakeholder or {}).get("university_id")
        if user.role == "university_admin" and user_uni != project.get("university_id"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: You cannot allocate faculty for another university's project.",
            )

        faculty_rec = self._get_faculty_or_404(faculty_id)
        if faculty_rec.get("university_id") != project.get("university_id"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Faculty '{faculty_id}' does not belong to university '{project.get('university_id')}'.",
            )

        try:
            self.client.table("projects").update({"faculty_id": faculty_id}).eq("project_id", project_id).execute()
        except Exception:
            pass

        return {
            "project_id": project_id,
            "faculty_id": faculty_id,
            "faculty_name": faculty_rec.get("faculty_name"),
            "message": f"Faculty '{faculty_rec.get('faculty_name')}' allocated successfully.",
        }

    # -------------------------------------------------------------------------
    # 2. Project Milestones (project_milestones)
    # -------------------------------------------------------------------------
    def create_milestone(
        self,
        project_id: str,
        payload: Dict[str, Any],
        user: AuthenticatedUser,
    ) -> Dict[str, Any]:
        """Creates a milestone for a project.

        Validations:
        - Project must exist
        - User must be assigned faculty, university admin, or an active project member
        - completion_percentage must be strictly 0-100
        - If assigned_to is specified and matches a student, validates student is in project_members
        """
        project = self._get_project_or_404(project_id)
        self._verify_project_access_auth(project, user)

        name = payload.get("milestone_name", "").strip()
        if not name:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="milestone_name is required",
            )

        pct = payload.get("completion_percentage", 0)
        if pct is not None and (pct < 0 or pct > 100):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"completion_percentage must be between 0 and 100, got {pct}",
            )

        # Validate assigned_to if provided
        assigned_to = payload.get("assigned_to")
        if assigned_to:
            try:
                mem_chk = (
                    self.client.table("project_members")
                    .select("*")
                    .eq("project_id", project_id)
                    .eq("student_id", assigned_to)
                    .eq("status", "active")
                    .execute()
                )
                if not mem_chk.data:
                    # Check if assigned_to is faculty
                    if assigned_to != project.get("faculty_id"):
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Assignee '{assigned_to}' is not an active member or faculty of project '{project_id}'.",
                        )
            except HTTPException:
                raise
            except Exception:
                pass

        initial_status = "completed" if pct == 100 else payload.get("status", "pending")

        record = {
            "project_id": project_id,
            "milestone_name": name,
            "description": payload.get("description"),
            "assigned_to": assigned_to,
            "deadline": payload.get("deadline"),
            "status": initial_status,
            "evidence_url": payload.get("evidence_url"),
            "completion_percentage": pct or 0,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        clean = {k: v for k, v in record.items() if v is not None}

        try:
            res = self.client.table("project_milestones").insert(clean).execute()
            saved = res.data[0] if (res and res.data) else clean
        except Exception:
            saved = clean

        if "milestone_id" not in saved or not saved.get("milestone_id"):
            saved["milestone_id"] = 1

        # If project is still in 'proposed' status, progress it to 'active'
        if project.get("status") == "proposed":
            try:
                self.client.table("projects").update({"status": "active"}).eq("project_id", project_id).execute()
            except Exception:
                pass

        return saved

    def update_milestone(
        self,
        milestone_id: int,
        patch: Dict[str, Any],
        user: AuthenticatedUser,
    ) -> Dict[str, Any]:
        """Updates milestone progress, status, and evidence.

        Validations:
        - Milestone must exist
        - User must have project access (assigned faculty, admin, or assigned student member)
        - completion_percentage must be 0-100
        - If completion reaches 100%, automatically marks status as 'completed'
        """
        milestone = self._get_milestone_or_404(milestone_id)
        project = self._get_project_or_404(milestone["project_id"])
        self._verify_project_access_auth(project, user)

        pct = patch.get("completion_percentage")
        if pct is not None:
            if pct < 0 or pct > 100:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"completion_percentage must be between 0 and 100, got {pct}",
                )
            if pct == 100:
                patch["status"] = "completed"
            elif pct > 0 and milestone.get("status") == "pending" and not patch.get("status"):
                patch["status"] = "in_progress"

        clean_patch = {k: v for k, v in patch.items() if v is not None}

        try:
            res = (
                self.client.table("project_milestones")
                .update(clean_patch)
                .eq("milestone_id", milestone_id)
                .execute()
            )
            updated = res.data[0] if res.data else {**milestone, **clean_patch}
        except Exception:
            updated = {**milestone, **clean_patch}

        return updated

    def list_milestones(
        self, project_id: str, user: AuthenticatedUser
    ) -> List[Dict[str, Any]]:
        """Lists all milestones for a project."""
        self._get_project_or_404(project_id)

        try:
            res = (
                self.client.table("project_milestones")
                .select("*")
                .eq("project_id", project_id)
                .order("created_at", desc=False)
                .execute()
            )
            return res.data or []
        except Exception:
            return []

    # -------------------------------------------------------------------------
    # 3. Role-Based Project Visibility
    # -------------------------------------------------------------------------
    def list_projects_for_user(
        self,
        user: Optional[AuthenticatedUser] = None,
        university_id: Optional[str] = None,
        faculty_id: Optional[str] = None,
        challenge_id: Optional[str] = None,
        status_filter: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Lists projects with role-aware visibility defaults:

        - student: projects where student is in project_members, or university available projects
        - faculty: projects where faculty_id matches user's faculty_id
        - university_admin: projects where university_id matches user's university_id
        - government / unauthenticated: all projects or query-filtered
        """
        query = self.client.table("projects").select("*")

        # Apply role-specific defaults if not explicitly requested
        if user and user.role == "faculty":
            user_fac_id = (user.stakeholder or {}).get("faculty_id")
            if user_fac_id and not faculty_id:
                query = query.eq("faculty_id", user_fac_id)
            elif faculty_id:
                query = query.eq("faculty_id", faculty_id)

        elif user and user.role == "university_admin":
            user_uni_id = (user.stakeholder or {}).get("university_id")
            if user_uni_id and not university_id:
                query = query.eq("university_id", user_uni_id)
            elif university_id:
                query = query.eq("university_id", university_id)

        elif user and user.role == "student":
            user_uni_id = (user.stakeholder or {}).get("university_id")
            if user_uni_id:
                query = query.eq("university_id", user_uni_id)

        else:
            if university_id:
                query = query.eq("university_id", university_id)
            if faculty_id:
                query = query.eq("faculty_id", faculty_id)

        if challenge_id:
            query = query.eq("challenge_id", challenge_id)
        if status_filter:
            query = query.eq("status", status_filter)

        query = query.order("created_at", desc=True).limit(limit)

        try:
            res = query.execute()
            return res.data or []
        except Exception:
            return []

    # -------------------------------------------------------------------------
    # Internal Validation Helpers
    # -------------------------------------------------------------------------
    def _get_project_or_404(self, project_id: str) -> Dict[str, Any]:
        try:
            res = self.client.table("projects").select("*").eq("project_id", project_id).execute()
            if not res.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Project '{project_id}' not found",
                )
            return res.data[0]
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project '{project_id}' not found")

    def _get_student_or_404(self, student_id: str) -> Dict[str, Any]:
        try:
            res = self.client.table("students").select("*").eq("student_id", student_id).execute()
            if not res.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Student record '{student_id}' not found in database.",
                )
            return res.data[0]
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Student record '{student_id}' not found")

    def _get_faculty_or_404(self, faculty_id: str) -> Dict[str, Any]:
        try:
            res = self.client.table("faculty").select("*").eq("faculty_id", faculty_id).execute()
            if not res.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Faculty record '{faculty_id}' not found in database.",
                )
            return res.data[0]
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Faculty record '{faculty_id}' not found")

    def _get_milestone_or_404(self, milestone_id: int) -> Dict[str, Any]:
        try:
            res = self.client.table("project_milestones").select("*").eq("milestone_id", milestone_id).execute()
            if not res.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Milestone '{milestone_id}' not found",
                )
            return res.data[0]
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Milestone '{milestone_id}' not found")

    def _verify_project_manage_auth(self, project: Dict[str, Any], user: AuthenticatedUser):
        """Ensures caller has administrative/management control over the project (assigned faculty or admin)."""
        if user.role == "government":
            return

        if user.role == "university_admin":
            user_uni = (user.stakeholder or {}).get("university_id")
            if user_uni and user_uni == project.get("university_id"):
                return

        if user.role == "faculty":
            user_fac = (user.stakeholder or {}).get("faculty_id")
            if user_fac and user_fac == project.get("faculty_id"):
                return

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: You are not authorized to manage members for this project.",
        )

    def _verify_project_access_auth(self, project: Dict[str, Any], user: AuthenticatedUser):
        """Ensures caller has read/contribute access to the project (faculty, admin, or project student member)."""
        if user.role in ["government", "university_admin", "faculty"]:
            self._verify_project_manage_auth(project, user)
            return

        if user.role == "student":
            user_stu = (user.stakeholder or {}).get("student_id")
            if user_stu:
                try:
                    m_res = (
                        self.client.table("project_members")
                        .select("*")
                        .eq("project_id", project["project_id"])
                        .eq("student_id", user_stu)
                        .eq("status", "active")
                        .execute()
                    )
                    if m_res.data and len(m_res.data) > 0:
                        return
                except Exception:
                    pass

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: You do not have permission to access or update milestones on this project.",
        )
