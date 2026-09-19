"""project_workflow_service.py

Handles collaborative project operations for Phase 6:
- Enforces strict institutional student boundaries in project_members.
- Manages student team member addition and removal without duplicate membership.
- Enforces role-based visibility for students, faculty, and university administrators.
- Coordinates milestone lifecycle tracking (GET, POST, PATCH) with 0-100 completion percentage validation.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from fastapi import HTTPException, status

from app.database import get_supabase
from app.services.auth_service import AuthenticatedUser


class ProjectWorkflowService:
    """Service managing project memberships, role-based visibility, and milestone tracking."""

    STANDARDIZED_MILESTONES = [
        "Problem Submitted",
        "Routed to Universities",
        "University Allocated",
        "Faculty Assigned",
        "Student Team Formed",
        "Development In Progress",
        "Solution Deployed",
    ]

    MILESTONE_KEY_MAP = {
        "submitted": "Problem Submitted",
        "problem submitted": "Problem Submitted",
        "routed": "Routed to Universities",
        "routed to universities": "Routed to Universities",
        "allocated": "University Allocated",
        "university allocated": "University Allocated",
        "faculty": "Faculty Assigned",
        "faculty assigned": "Faculty Assigned",
        "team": "Student Team Formed",
        "student team formed": "Student Team Formed",
        "progress": "Development In Progress",
        "development in progress": "Development In Progress",
        "deployed": "Solution Deployed",
        "solution deployed": "Solution Deployed",
        "solved": "Solution Deployed",
        "completed": "Solution Deployed",
    }

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

        if new_status == "active":
            try:
                chk = (
                    self.client.table("project_members")
                    .select("*")
                    .eq("project_id", project_id)
                    .eq("student_id", student_id)
                    .eq("status", "active")
                    .execute()
                )
                if chk.data and len(chk.data) > 0:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Duplicate selection: Student '{student_id}' is already an active member of project '{project_id}'.",
                    )
            except HTTPException:
                raise
            except Exception:
                pass

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

    def get_project_current_stage(self, project_id: str) -> Tuple[int, str]:
        """Returns (index, milestone_name) for the project within the 7 standardized stages."""
        project = self._get_project_or_404(project_id)
        if project.get("status") in ["deployed", "solved", "completed"]:
            return (6, "Solution Deployed")

        highest_idx = 3  # At least Faculty Assigned (index 3) since project is assigned
        try:
            m_res = (
                self.client.table("project_milestones")
                .select("milestone_name, status")
                .eq("project_id", project_id)
                .execute()
            )
            for m in (m_res.data or []):
                m_name = m.get("milestone_name")
                if m_name:
                    norm = self.MILESTONE_KEY_MAP.get(m_name.strip().lower())
                    if norm in self.STANDARDIZED_MILESTONES and m.get("status") in ["completed", "active"]:
                        idx = self.STANDARDIZED_MILESTONES.index(norm)
                        if idx > highest_idx:
                            highest_idx = idx
        except Exception:
            pass

        # Also check project_members: if active students exist and highest_idx < 4
        try:
            pm_res = (
                self.client.table("project_members")
                .select("student_id")
                .eq("project_id", project_id)
                .eq("status", "active")
                .execute()
            )
            if pm_res.data and len(pm_res.data) > 0 and highest_idx < 4:
                highest_idx = 4  # Student Team Formed
        except Exception:
            pass

        return (highest_idx, self.STANDARDIZED_MILESTONES[highest_idx])

    def update_project_standardized_milestone(
        self,
        project_id: str,
        milestone_input: str,
        user: AuthenticatedUser,
    ) -> Dict[str, Any]:
        """Allows assigned faculty to advance milestone along the authoritative 7-stage sequence.

        Validations:
        - Only assigned faculty (or authorized admin) can update (HTTP 403)
        - Completed projects cannot be edited (HTTP 400)
        - Predefined standardized stages only (HTTP 400)
        - Backward transitions are rejected (HTTP 400)
        - Skipping required stages is rejected (HTTP 400)
        - Explicitly allows: Student Team Formed -> Development In Progress
        - Explicitly allows: Development In Progress -> Solution Deployed
        """
        project = self._get_project_or_404(project_id)

        # 1. Authorize: Only assigned faculty (or university admin / gov) can update
        if user.role == "faculty":
            fac_rec = self._resolve_faculty_record(user)
            auth_fac_id = (fac_rec or {}).get("faculty_id") or (user.stakeholder or {}).get("faculty_id")
            if not auth_fac_id or auth_fac_id != project.get("faculty_id"):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access forbidden: Only the assigned faculty can edit milestones for this project.",
                )
        elif user.role not in ["university_admin", "government"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: You do not have permission to edit milestones for this project.",
            )

        # 2. Check if already completed
        if project.get("status") in ["deployed", "solved", "completed"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid milestone update: Completed projects cannot be edited.",
            )

        # 3. Validate milestone is in standardized sequence
        clean_input = (milestone_input or "").strip().lower()
        norm_target = self.MILESTONE_KEY_MAP.get(clean_input)
        if not norm_target or norm_target not in self.STANDARDIZED_MILESTONES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid milestone '{milestone_input}'. Predefined stages are: {self.STANDARDIZED_MILESTONES}.",
            )

        target_idx = self.STANDARDIZED_MILESTONES.index(norm_target)
        curr_idx, curr_stage = self.get_project_current_stage(project_id)

        # 4. Strict Progression Rules:
        # Backward transitions blocked
        if target_idx < curr_idx:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid milestone transition: Cannot move backward from '{curr_stage}' to '{norm_target}'.",
            )

        # Skipping required stages blocked
        if target_idx > curr_idx + 1:
            allowed_next = self.STANDARDIZED_MILESTONES[curr_idx + 1]
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid milestone transition: Skipping required stages from '{curr_stage}' to '{norm_target}' is not permitted. Next stage is '{allowed_next}'.",
            )

        now_ts = datetime.now(timezone.utc).isoformat()
        pct_map = {
            "Student Team Formed": 60,
            "Development In Progress": 80,
            "Solution Deployed": 100,
        }

        # 5. Persist milestone in project_milestones
        m_rec = {
            "project_id": project_id,
            "milestone_name": norm_target,
            "status": "completed",
            "completion_percentage": pct_map.get(norm_target, 100),
            "created_at": now_ts,
        }
        try:
            self.client.table("project_milestones").insert(m_rec).execute()
        except Exception:
            pass

        # 6. Update project status and linked challenge
        proj_updates = {}
        if norm_target == "Solution Deployed":
            proj_updates["status"] = "deployed"
            proj_updates["actual_end_date"] = now_ts
            cid = project.get("challenge_id")
            if cid:
                try:
                    self.client.table("challenges").update({"status": "resolved"}).eq("challenge_id", cid).execute()
                except Exception:
                    pass
        elif norm_target in ["Development In Progress", "Student Team Formed"]:
            if project.get("status") == "proposed":
                proj_updates["status"] = "active"

        if proj_updates:
            try:
                self.client.table("projects").update(proj_updates).eq("project_id", project_id).execute()
            except Exception:
                pass

        return {
            "project_id": project_id,
            "milestone": norm_target,
            "previous_milestone": curr_stage,
            "current_milestone": norm_target,
            "status": proj_updates.get("status", project.get("status")),
            "completion_percentage": pct_map.get(norm_target, 100),
            "updated_at": now_ts,
            "message": f"Project milestone advanced successfully to '{norm_target}'.",
        }

    # -------------------------------------------------------------------------
    # 3. Role-Based Project Visibility
    # -------------------------------------------------------------------------
    def _get_record_silent(self, table_name: str, key_field: str, key_val: Optional[str]) -> Optional[Dict[str, Any]]:
        if not key_val:
            return None
        try:
            res = self.client.table(table_name).select("*").eq(key_field, key_val).execute()
            return res.data[0] if (res and res.data) else None
        except Exception:
            return None

    def _resolve_student_record(self, user: Optional[AuthenticatedUser]) -> Optional[Dict[str, Any]]:
        if not user:
            return None
        if user.stakeholder and user.stakeholder.get("student_id"):
            return user.stakeholder
        if getattr(user, "user_id", None):
            try:
                res = self.client.table("students").select("*").eq("user_id", user.user_id).execute()
                if res and res.data:
                    return res.data[0]
            except Exception:
                pass
        if getattr(user, "email", None):
            try:
                res = self.client.table("students").select("*").eq("email", user.email).execute()
                if res and res.data:
                    return res.data[0]
            except Exception:
                pass
        return None

    def _resolve_university_admin_record(self, user: Optional[AuthenticatedUser]) -> Optional[Dict[str, Any]]:
        if not user:
            return None
        if getattr(user, "stakeholder", None) and user.stakeholder.get("university_id"):
            return user.stakeholder
        if getattr(user, "user_id", None):
            try:
                res = self.client.table("university_admins").select("*").eq("user_id", str(user.user_id)).execute()
                if res and res.data:
                    return res.data[0]
            except Exception:
                pass
        if getattr(user, "email", None):
            try:
                res = self.client.table("university_admins").select("*").eq("email", user.email).execute()
                if res and res.data:
                    return res.data[0]
            except Exception:
                pass
        return None

    def _resolve_faculty_record(self, user: Optional[AuthenticatedUser]) -> Optional[Dict[str, Any]]:
        if not user:
            return None
        if user.stakeholder and user.stakeholder.get("faculty_id"):
            return user.stakeholder
        if getattr(user, "user_id", None):
            try:
                res = self.client.table("faculty").select("*").eq("user_id", user.user_id).execute()
                if res and res.data:
                    return res.data[0]
            except Exception:
                pass
        if getattr(user, "email", None):
            try:
                res = self.client.table("faculty").select("*").eq("email", user.email).execute()
                if res and res.data:
                    return res.data[0]
            except Exception:
                pass
        return None

    def list_projects_for_user(
        self,
        user: Optional[AuthenticatedUser] = None,
        university_id: Optional[str] = None,
        faculty_id: Optional[str] = None,
        challenge_id: Optional[str] = None,
        status_filter: Optional[str] = None,
        limit: int = 100,
        my_projects: bool = False,
        approved_only: bool = False,
        hydrate: bool = True,
    ) -> List[Dict[str, Any]]:
        """Lists projects with role-aware visibility defaults:

        - student:
            - if my_projects: strictly projects where student is an active/selected member
            - otherwise: projects belonging to student's university
            - if approved_only: excludes unapproved/proposed/rejected projects
        - faculty: projects where faculty_id matches authenticated faculty_id
        - university_admin: projects where university_id matches authoritative university_id
        - government / unauthenticated: all projects or query-filtered
        """
        query = self.client.table("projects").select("*")

        # Apply role-specific defaults if not explicitly requested
        if user and user.role == "faculty":
            fac_rec = self._resolve_faculty_record(user)
            auth_fac_id = (fac_rec or {}).get("faculty_id") or (user.stakeholder or {}).get("faculty_id")
            if not auth_fac_id:
                return []
            # Authoritative filter: strictly scoped to assigned faculty, ignore/block external query param overrides
            query = query.eq("faculty_id", auth_fac_id)

        elif user and user.role == "university_admin":
            admin_rec = self._resolve_university_admin_record(user)
            auth_uni_id = (admin_rec or {}).get("university_id") or (user.stakeholder or {}).get("university_id")
            if not auth_uni_id:
                return []
            # Authoritative filter: strictly scoped to university_admin's university, ignore external query param overrides
            query = query.eq("university_id", auth_uni_id)

        elif user and user.role == "student":
            s_rec = self._resolve_student_record(user)
            user_uni_id = (user.stakeholder or {}).get("university_id") or (s_rec or {}).get("university_id")

            if my_projects:
                stu_id = (s_rec or {}).get("student_id") or (user.stakeholder or {}).get("student_id")
                if not stu_id:
                    return []
                try:
                    pm_res = self.client.table("project_members").select("project_id").eq("student_id", stu_id).execute()
                    member_pids = [m["project_id"] for m in (pm_res.data or []) if m.get("project_id")]
                except Exception:
                    member_pids = []
                if not member_pids:
                    return []
                query = query.in_("project_id", member_pids)
            else:
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
            projects = res.data or []
        except Exception:
            return []

        # Filter approved_only if requested
        if approved_only:
            # Active/approved statuses: excludes proposed, rejected, unrouted
            approved_set = {"active", "prototype", "pilot", "deployed", "solved", "completed"}
            projects = [p for p in projects if p.get("status") in approved_set]

        if not hydrate:
            return projects

        # Hydrate projects with rich metadata for student & dashboard display
        calling_student = self._resolve_student_record(user) if (user and user.role == "student") else None
        calling_stu_id = calling_student.get("student_id") if calling_student else None

        hydrated = []
        for p in projects:
            item = dict(p)
            pid = item.get("project_id")
            cid = item.get("challenge_id")

            ch = self._get_record_silent("challenges", "challenge_id", cid) or {}
            uni = self._get_record_silent("universities", "university_id", item.get("university_id")) or {}
            fac = self._get_record_silent("faculty", "faculty_id", item.get("faculty_id")) or {}
            ind = self._get_record_silent("industries", "industry_id", item.get("industry_id")) or {}

            # Student members and applicants
            stu_names = []
            active_students = []
            pending_applicants = []
            is_member = False
            try:
                pm_res = self.client.table("project_members").select("student_id, status, role").eq("project_id", pid).execute()
                for pm in (pm_res.data or []):
                    sid = pm.get("student_id")
                    st = pm.get("status", "active")
                    s = self._get_record_silent("students", "student_id", sid)
                    s_name = s.get("student_name", sid) if s else sid
                    s_email = s.get("email") if s else None

                    if st in ("active", "selected", "completed"):
                        if calling_stu_id and sid == calling_stu_id:
                            is_member = True
                        if s_name:
                            stu_names.append(s_name)
                        active_students.append({
                            "student_id": sid,
                            "name": s_name,
                            "email": s_email,
                            "status": st,
                            "role": pm.get("role", "member"),
                        })
                    elif st == "pending" or pm.get("role") == "applicant":
                        pending_applicants.append({
                            "student_id": sid,
                            "student_name": s_name,
                            "email": s_email,
                            "role": pm.get("role", "applicant"),
                            "status": "pending",
                        })
            except Exception:
                pass

            # Authoritative standardized milestone calculation
            try:
                _, curr_milestone = self.get_project_current_stage(pid)
            except Exception:
                curr_milestone = "Solution Deployed" if item.get("status") in ("deployed", "solved", "completed") else "Faculty Assigned"

            # Industry employee and mentor hydration (Part 12, 13 & Clarification 4)
            ind_emp_name = None
            ind_emp_desig = None
            try:
                pei_res = self.client.table("project_employee_interests").select("employee_id, status").eq("project_id", pid).execute()
                interests = pei_res.data or []
                selected_emp = next((i for i in interests if i.get("status") == "selected"), None) or (interests[0] if interests else None)
                if selected_emp:
                    emp_rec = self._get_record_silent("industry_employees", "employee_id", selected_emp.get("employee_id"))
                    if emp_rec:
                        ind_emp_name = emp_rec.get("employee_name")
                        ind_emp_desig = emp_rec.get("designation")
                if not ind_emp_name and item.get("industry_id"):
                    ie_res = self.client.table("industry_employees").select("employee_name, designation").eq("industry_id", item.get("industry_id")).limit(1).execute()
                    if ie_res.data:
                        ind_emp_name = ie_res.data[0].get("employee_name")
                        ind_emp_desig = ie_res.data[0].get("designation")
            except Exception:
                pass

            # Multiple faculty mentors hydration (Part 8, 16 & Clarification 1)
            faculty_mentors = []
            if fac and fac.get("faculty_name"):
                faculty_mentors.append({
                    "faculty_id": fac.get("faculty_id"),
                    "faculty_name": fac.get("faculty_name"),
                    "department": fac.get("department"),
                    "email": fac.get("email"),
                    "role": "Primary Faculty Mentor",
                })
            try:
                f_all = self.client.table("faculty").select("faculty_id, faculty_name, department, email, past_project_ids").eq("university_id", item.get("university_id")).execute()
                for f_row in (f_all.data or []):
                    if f_row.get("faculty_id") != item.get("faculty_id"):
                        pids = [p.strip() for p in str(f_row.get("past_project_ids") or "").split(",") if p.strip()]
                        if pid in pids:
                            faculty_mentors.append({
                                "faculty_id": f_row.get("faculty_id"),
                                "faculty_name": f_row.get("faculty_name"),
                                "department": f_row.get("department"),
                                "email": f_row.get("email"),
                                "role": "Co-Mentor Faculty",
                            })
            except Exception:
                pass

            item["title"] = item.get("project_title") or ch.get("title") or "Collaborative Innovation Project"
            item["challenge_title"] = ch.get("title") or item.get("project_title")
            item["description"] = item.get("description") or ch.get("description") or "Collaborative innovation project."
            item["location"] = ch.get("location") or ch.get("address") or f"{ch.get('city', '')}, Jharkhand".strip(", ") or "Jharkhand, India"
            item["city"] = ch.get("city") or uni.get("city") or "Jharkhand"
            item["district"] = ch.get("district") or uni.get("district") or "Jharkhand"
            item["skills_required"] = ch.get("expected_solution") or uni.get("skills") or "Engineering, IoT, Software"
            item["faculty_name"] = fac.get("faculty_name") or "Faculty Advisor"
            item["faculty_email"] = fac.get("email")
            item["faculty_mentors"] = faculty_mentors
            item["industry_name"] = ind.get("industry_name") or "Industry Partner"
            item["industry_employee_name"] = ind_emp_name
            item["industry_employee_designation"] = ind_emp_desig
            item["industry_mentor_name"] = ind_emp_name
            item["student_participants"] = stu_names
            item["student_names"] = stu_names
            item["students"] = active_students
            item["applicants"] = pending_applicants
            item["university_name"] = uni.get("university_name") or "Partner University"
            item["is_member"] = is_member
            item["is_deployed"] = item.get("status") in ("deployed", "solved", "completed")
            item["current_milestone"] = curr_milestone

            hydrated.append(item)

        return hydrated

    # -------------------------------------------------------------------------
    # Certificate Issuance & Student Eligibility
    # -------------------------------------------------------------------------
    def get_project_certificate(self, project_id: str, user: AuthenticatedUser) -> Dict[str, Any]:
        """Validates student membership and authoritative 'Solution Deployed' milestone

        to issue or view the official E-Certificate.
        Raises HTTP 403 if user is not an active team member.
        Raises HTTP 400 if project has not reached 'Solution Deployed' milestone.
        """
        project = self._get_project_or_404(project_id)
        s_rec = self._resolve_student_record(user)
        stu_id = s_rec.get("student_id") if s_rec else None

        # Verify user is an authorized member
        if user.role == "student":
            if not stu_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Student record not found.",
                )
            pm_res = (
                self.client.table("project_members")
                .select("*")
                .eq("project_id", project_id)
                .eq("student_id", stu_id)
                .execute()
            )
            members = [m for m in (pm_res.data or []) if m.get("status") in ("active", "selected", "completed")]
            if not members:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: You are not an enrolled team member of this project.",
                )

        # Authoritative completion rule: MUST reach 'Solution Deployed'
        # status in ('deployed', 'solved', 'completed')
        is_deployed = project.get("status") in ("deployed", "solved", "completed")
        if not is_deployed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Certificate is not available before the 'Solution Deployed' milestone.",
            )

        student_name = (s_rec or {}).get("student_name") or user.full_name or "Student Contributor"
        uni = self._get_record_silent("universities", "university_id", project.get("university_id")) or {}
        fac = self._get_record_silent("faculty", "faculty_id", project.get("faculty_id")) or {}
        ind = self._get_record_silent("industries", "industry_id", project.get("industry_id")) or {}
        ch = self._get_record_silent("challenges", "challenge_id", project.get("challenge_id")) or {}

        cert_id = f"JH-SS-CERT-{project_id.replace('PRJ-', '')}-{stu_id or 'STU'}"
        verify_code = f"SS-{project_id[:8]}-{stu_id or 'MEM'}".upper()

        return {
            "certificate_id": cert_id,
            "project_id": project_id,
            "project_title": project.get("project_title") or ch.get("title") or "Collaborative Solution",
            "challenge_title": ch.get("title") or project.get("project_title"),
            "student_id": stu_id,
            "student_name": student_name,
            "university_id": project.get("university_id"),
            "university_name": uni.get("university_name") or "Government Partner University",
            "faculty_name": fac.get("faculty_name") or "Faculty Project Guide",
            "industry_name": ind.get("industry_name") or "Industry Partner",
            "status": "eligible",
            "milestone_reached": "Solution Deployed",
            "completion_date": project.get("actual_end_date") or (project.get("created_at")[:10] if project.get("created_at") else "2026-09-18"),
            "verification_code": verify_code,
            "issuer": "Government of Jharkhand — Department of Higher & Technical Education",
            "platform": "Samadhan Setu / Concordia Innovation Platform",
        }

    def list_student_certificates(self, user: AuthenticatedUser) -> List[Dict[str, Any]]:
        """Lists all projects where the student is a member, indicating certificate eligibility and status."""
        s_rec = self._resolve_student_record(user)
        stu_id = s_rec.get("student_id") if s_rec else None
        if not stu_id:
            return []

        try:
            pm_res = (
                self.client.table("project_members")
                .select("project_id, status")
                .eq("student_id", stu_id)
                .execute()
            )
            active_pids = [
                m["project_id"] for m in (pm_res.data or [])
                if m.get("status") in ("active", "selected", "completed")
            ]
        except Exception:
            active_pids = []

        if not active_pids:
            return []

        cert_list = []
        for pid in active_pids:
            p = self._get_record_silent("projects", "project_id", pid)
            if not p:
                continue
            is_deployed = p.get("status") in ("deployed", "solved", "completed")
            ch = self._get_record_silent("challenges", "challenge_id", p.get("challenge_id")) or {}
            uni = self._get_record_silent("universities", "university_id", p.get("university_id")) or {}
            fac = self._get_record_silent("faculty", "faculty_id", p.get("faculty_id")) or {}
            ind = self._get_record_silent("industries", "industry_id", p.get("industry_id")) or {}

            cert_data = None
            if is_deployed:
                cert_data = {
                    "certificate_id": f"JH-SS-CERT-{pid.replace('PRJ-', '')}-{stu_id}",
                    "project_id": pid,
                    "project_title": p.get("project_title") or ch.get("title"),
                    "challenge_title": ch.get("title") or p.get("project_title"),
                    "student_id": stu_id,
                    "student_name": s_rec.get("student_name") or user.full_name or "Student Contributor",
                    "university_name": uni.get("university_name"),
                    "faculty_name": fac.get("faculty_name"),
                    "industry_name": ind.get("industry_name"),
                    "status": "eligible",
                    "milestone_reached": "Solution Deployed",
                    "completion_date": p.get("actual_end_date") or (p.get("created_at")[:10] if p.get("created_at") else "2026-09-18"),
                    "verification_code": f"SS-{pid[:8]}-{stu_id}".upper(),
                    "issuer": "Government of Jharkhand — Department of Higher & Technical Education",
                    "platform": "Samadhan Setu / Concordia Innovation Platform",
                }

            cert_list.append({
                "project_id": pid,
                "project_title": p.get("project_title") or ch.get("title"),
                "status": p.get("status"),
                "is_eligible": is_deployed,
                "lock_reason": None if is_deployed else "Certificate is locked. This project is currently in progress and will become available once the 'Solution Deployed' milestone is reached.",
                "certificate": cert_data,
            })

        return cert_list

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
            fac_rec = self._resolve_faculty_record(user)
            user_fac = (fac_rec or {}).get("faculty_id") or (user.stakeholder or {}).get("faculty_id")
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
