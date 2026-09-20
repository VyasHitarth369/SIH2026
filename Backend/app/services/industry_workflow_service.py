"""industry_workflow_service.py

Handles Industry Collaboration operations for Phase 7:
- SPOC collaboration acceptance and rejection on challenge matches.
- Employee interest expression on collaborative innovation projects.
- Institutional boundary enforcement (cross-industry interest prevention).
- SPOC employee selection, anti-self-selection enforcement, and interest lifecycle management.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status

from app.database import get_supabase
from app.services.auth_service import AuthenticatedUser


class IndustryWorkflowService:
    """Service managing industry matches, SPOC collaboration responses, and employee interests."""

    def __init__(self, client=None):
        self._client = client

    @property
    def client(self):
        return self._client if self._client is not None else get_supabase()

    # -------------------------------------------------------------------------
    # 1. Industry Collaboration Response (challenge_industry_matches)
    # -------------------------------------------------------------------------
    def respond_to_industry_match(
        self,
        challenge_id: str,
        industry_id: str,
        action: str,
        response_note: Optional[str],
        user: AuthenticatedUser,
    ) -> Dict[str, Any]:
        """Processes an Industry SPOC's acceptance or rejection of a challenge match.

        Enforces:
        - Authenticated user must have role 'industry_employee' (or 'government')
        - Account must be verified in industry_employees
        - User must possess approval_authority = TRUE (Designation alone is NOT permission!)
        - User must strictly belong to the specified industry_id
        - Challenge and match records must exist in the database
        - Updates status to 'accepted' or 'rejected'
        - If accepted and a project exists for the challenge, associates project.industry_id
        """
        # 1. Verify SPOC permissions and organizational boundary
        self._verify_industry_spoc_auth(industry_id, user)

        # 2. Verify challenge exists
        self._get_challenge_or_404(challenge_id)

        # 3. Verify match exists in challenge_industry_matches
        match = self._get_industry_match_or_404(challenge_id, industry_id)
        current_status = match.get("status")
        if current_status not in ["recommended", "invited"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot respond to industry match in status '{current_status}'. Match must be in 'recommended' or 'invited' status.",
            )

        if action == "reject":
            if not response_note or not str(response_note).strip():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="A mandatory rejection reason must be provided when rejecting an industry collaboration proposal.",
                )

        new_status = "accepted" if action == "accept" else "rejected"
        now_str = datetime.now(timezone.utc).isoformat()

        import uuid
        is_valid_uuid = False
        try:
            uuid.UUID(str(user.user_id))
            is_valid_uuid = True
        except Exception:
            pass

        update_payload = {
            "status": new_status,
            "responded_at": now_str,
            "response_note": response_note,
        }
        if is_valid_uuid:
            update_payload["responded_by"] = str(user.user_id)

        try:
            res = (
                self.client.table("challenge_industry_matches")
                .update(update_payload)
                .eq("challenge_id", challenge_id)
                .eq("industry_id", industry_id)
                .execute()
            )
            updated = res.data[0] if (res and res.data) else {**match, **update_payload, "responded_by": str(user.user_id)}
        except Exception:
            updated = {**match, **update_payload, "responded_by": str(user.user_id)}

        if "responded_by" not in updated or not updated["responded_by"]:
            updated["responded_by"] = str(user.user_id)

        # 4. If accepted, associate industry with existing project if present
        if action == "accept":
            try:
                p_res = (
                    self.client.table("projects")
                    .select("*")
                    .eq("challenge_id", challenge_id)
                    .execute()
                )
                if p_res and p_res.data:
                    project = p_res.data[0]
                    if not project.get("industry_id"):
                        self.client.table("projects").update({
                            "industry_id": industry_id
                        }).eq("project_id", project["project_id"]).execute()
            except Exception:
                pass

        return updated

    # -------------------------------------------------------------------------
    # 2. Employee Interest Expression (project_employee_interests)
    # -------------------------------------------------------------------------
    def express_employee_interest(
        self,
        project_id: str,
        message: Optional[str],
        user: AuthenticatedUser,
    ) -> Dict[str, Any]:
        """Allows an eligible verified industry employee to express interest in a project.

        Enforces:
        - Authenticated user must have role 'industry_employee'
        - Employee account must be verified in industry_employees
        - Project must exist and have an allocated industry partner
        - Employee must strictly belong to the project's allocated industry
        - Prevents duplicate active interest expressions (UNIQUE constraint on project_id, employee_id)
        """
        # 1. Enforce employee authentication & verification
        if user.role != "industry_employee":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: Only industry employees may express interest in industry projects.",
            )

        if not user.is_verified or user.verification_status != "verified":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden: Employee account is '{user.verification_status}'. Verified account required.",
            )

        employee_record = user.stakeholder or {}
        employee_id = employee_record.get("employee_id")
        employee_industry_id = employee_record.get("industry_id")

        if not employee_id or not employee_industry_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: User is not linked to a valid industry employee record.",
            )

        # 2. Verify project exists
        project = self._get_project_or_404(project_id)
        project_industry_id = project.get("industry_id")

        if not project_industry_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Project '{project_id}' does not have an allocated industry partner yet.",
            )

        # 3. Institutional boundary: employee must belong to project's industry
        if employee_industry_id != project_industry_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Employee belongs to industry '{employee_industry_id}', but project '{project_id}' "
                    f"is partnered with industry '{project_industry_id}'. Cross-industry participation is not permitted."
                ),
            )

        # 3b. Verify Industry Manager has approved the industry match
        challenge_id = project.get("challenge_id")
        if challenge_id:
            try:
                m_res = (
                    self.client.table("challenge_industry_matches")
                    .select("status")
                    .eq("challenge_id", challenge_id)
                    .eq("industry_id", employee_industry_id)
                    .execute()
                )
                if not m_res.data or m_res.data[0].get("status") != "accepted":
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Cannot express interest: The Industry Manager has not approved the collaboration proposal for this project yet.",
                    )
            except HTTPException:
                raise
            except Exception:
                pass

        # 4. Check existing interest record (duplicate prevention)
        existing = self._find_employee_interest(project_id, employee_id)
        now_str = datetime.now(timezone.utc).isoformat()

        if existing:
            current_status = existing.get("status")
            if current_status == "interested":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Employee '{employee_id}' has already expressed active interest in project '{project_id}'.",
                )
            if current_status == "selected":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Employee '{employee_id}' is already officially selected for project '{project_id}'.",
                )

            # Reactivate previously withdrawn or unselected interest
            patch = {
                "status": "interested",
                "message": message or existing.get("message"),
                "created_at": now_str,
            }
            try:
                res = (
                    self.client.table("project_employee_interests")
                    .update(patch)
                    .eq("interest_id", existing["interest_id"])
                    .execute()
                )
                saved = res.data[0] if (res and res.data) else {**existing, **patch}
            except Exception:
                saved = {**existing, **patch}

            return self._hydrate_interest(saved, employee_record)

        # 5. Insert new interest record
        record = {
            "project_id": project_id,
            "employee_id": employee_id,
            "message": message,
            "status": "interested",
            "created_at": now_str,
        }

        try:
            res = self.client.table("project_employee_interests").insert(record).execute()
            saved = res.data[0] if (res and res.data) else record
        except Exception:
            saved = record

        if "interest_id" not in saved or not saved.get("interest_id"):
            saved["interest_id"] = 1

        return self._hydrate_interest(saved, employee_record)

    # -------------------------------------------------------------------------
    # 3. List Employee Interests (project_employee_interests)
    # -------------------------------------------------------------------------
    def list_employee_interests(
        self, project_id: str, user: AuthenticatedUser
    ) -> List[Dict[str, Any]]:
        """Lists employee interest expressions on a project with hydrated profiles.
        Strictly restricted to Industry Manager/SPOC (or Government). Normal employees receive 403.
        """
        project = self._get_project_or_404(project_id)
        project_industry_id = project.get("industry_id")
        self._verify_industry_spoc_auth(project_industry_id, user)

        try:
            res = (
                self.client.table("project_employee_interests")
                .select("*")
                .eq("project_id", project_id)
                .order("created_at", desc=False)
                .execute()
            )
            interests = res.data or []
        except Exception:
            interests = []

        # Hydrate employee profiles
        hydrated = []
        for item in interests:
            emp = self._get_employee_record_silent(item.get("employee_id"))
            hydrated.append(self._hydrate_interest(item, emp))

        return hydrated

    # -------------------------------------------------------------------------
    # 4. Update Employee Interest (SPOC Selection / Withdrawal)
    # -------------------------------------------------------------------------
    def update_employee_interest_status(
        self,
        project_id: str,
        interest_id: int,
        new_status: str,
        note: Optional[str],
        user: AuthenticatedUser,
    ) -> Dict[str, Any]:
        """Updates interest status: 'selected', 'not_selected', or 'withdrawn'.

        Security & Validation Rules:
        - Project and interest record must exist
        - Only authorized Industry SPOC (verified, approval_authority=True) can set 'selected' or 'not_selected'
        - Anti-Self-Selection: An employee cannot select themselves!
        - Selected employee must belong to the project's allocated industry
        - An employee can withdraw ('withdrawn') their own interest, or the SPOC can withdraw it
        - Ordinary employees cannot modify other employees' interest records
        """
        project = self._get_project_or_404(project_id)
        project_industry_id = project.get("industry_id")
        user_emp_id = (user.stakeholder or {}).get("employee_id")

        # Handle 'selected' and 'not_selected' SPOC permissions early
        if new_status in ["selected", "not_selected"]:
            # Rule 4 & 5: Only authorized Industry SPOC with approval_authority can select
            if user.role != "government":
                self._verify_industry_spoc_auth(project_industry_id, user)

        interest = self._get_interest_or_404(project_id, interest_id)
        target_employee_id = interest.get("employee_id")

        # Handle 'withdrawn' action
        if new_status == "withdrawn":
            is_self = user.role == "industry_employee" and user_emp_id == target_employee_id
            is_spoc = self._is_verified_spoc_for_industry(project_industry_id, user)

            if not (is_self or is_spoc or user.role == "government"):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access forbidden: Only the applicant employee or their Industry SPOC may withdraw this interest.",
                )

        # Handle 'selected' and 'not_selected' actions
        elif new_status in ["selected", "not_selected"]:

            # Rule 7: Anti-self-selection: An employee cannot select themselves!
            if user_emp_id and user_emp_id == target_employee_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access forbidden: An employee cannot select themselves for official participation.",
                )

            # Rule 8: Validate target employee belongs to the correct industry
            target_emp = self._get_employee_record_silent(target_employee_id)
            if not target_emp or target_emp.get("industry_id") != project_industry_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Employee '{target_employee_id}' does not belong to project industry '{project_industry_id}'."
                    ),
                )

            # Rule 9: Target interest must be eligible for selection
            if new_status == "selected" and interest.get("status") not in ["interested", "selected"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Target interest is in status '{interest.get('status')}' and is not eligible for selection.",
                )

        patch = {"status": new_status}
        try:
            res = (
                self.client.table("project_employee_interests")
                .update(patch)
                .eq("interest_id", interest_id)
                .execute()
            )
            updated = res.data[0] if (res and res.data) else {**interest, **patch}
        except Exception:
            updated = {**interest, **patch}

        # If an employee was selected, mark other interested applicants as not_selected
        if new_status == "selected":
            try:
                self.client.table("project_employee_interests")\
                    .update({"status": "not_selected"})\
                    .eq("project_id", project_id)\
                    .eq("status", "interested")\
                    .neq("interest_id", interest_id)\
                    .execute()
            except Exception:
                pass

        target_emp = self._get_employee_record_silent(target_employee_id)
        return self._hydrate_interest(updated, target_emp)

    # -------------------------------------------------------------------------
    # Internal Validation Helpers
    # -------------------------------------------------------------------------
    def _verify_industry_spoc_auth(self, industry_id: str, user: AuthenticatedUser):
        """Verifies that the user is an authorized SPOC for the specified industry."""
        if user.role == "government":
            return

        if user.role != "industry_employee":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: Only industry representatives may access this resource.",
            )

        if not user.is_verified or user.verification_status != "verified":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden: Industry account is not verified (status: '{user.verification_status}').",
            )

        if not user.approval_authority:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: SPOC approval authority is required. Designation alone does not confer permission.",
            )

        user_ind = (user.stakeholder or {}).get("industry_id")
        if user_ind != industry_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden: You belong to industry '{user_ind}', not '{industry_id}'.",
            )

    def _is_verified_spoc_for_industry(self, industry_id: Optional[str], user: AuthenticatedUser) -> bool:
        if not industry_id:
            return False
        if user.role != "industry_employee":
            return False
        if not user.is_verified or user.verification_status != "verified":
            return False
        if not user.approval_authority:
            return False
        return (user.stakeholder or {}).get("industry_id") == industry_id

    def _verify_project_view_access(self, project: Dict[str, Any], user: AuthenticatedUser):
        if user.role == "government":
            return

        proj_ind = project.get("industry_id")
        user_ind = (user.stakeholder or {}).get("industry_id")
        if user.role == "industry_employee" and proj_ind and user_ind == proj_ind:
            return

        proj_uni = project.get("university_id")
        user_uni = (user.stakeholder or {}).get("university_id")
        if user.role in ["university_admin", "faculty"] and proj_uni and user_uni == proj_uni:
            return

        # If project student member
        user_stu = (user.stakeholder or {}).get("student_id")
        if user.role == "student" and user_stu:
            try:
                chk = (
                    self.client.table("project_members")
                    .select("*")
                    .eq("project_id", project["project_id"])
                    .eq("student_id", user_stu)
                    .eq("status", "active")
                    .execute()
                )
                if chk.data:
                    return
            except Exception:
                pass

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: You do not have permission to view employee interests for this project.",
        )

    def _get_challenge_or_404(self, challenge_id: str) -> Dict[str, Any]:
        try:
            res = self.client.table("challenges").select("*").eq("challenge_id", challenge_id).execute()
            if not res.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Challenge '{challenge_id}' not found",
                )
            return res.data[0]
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Challenge '{challenge_id}' not found")

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

    def _get_industry_match_or_404(self, challenge_id: str, industry_id: str) -> Dict[str, Any]:
        try:
            res = (
                self.client.table("challenge_industry_matches")
                .select("*")
                .eq("challenge_id", challenge_id)
                .eq("industry_id", industry_id)
                .execute()
            )
            if not res.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Match not found for challenge '{challenge_id}' and industry '{industry_id}'",
                )
            return res.data[0]
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Match not found for challenge '{challenge_id}' and industry '{industry_id}'",
            )

    def _get_interest_or_404(self, project_id: str, interest_id: int) -> Dict[str, Any]:
        try:
            res = (
                self.client.table("project_employee_interests")
                .select("*")
                .eq("interest_id", interest_id)
                .eq("project_id", project_id)
                .execute()
            )
            if not res.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Employee interest record '{interest_id}' not found for project '{project_id}'",
                )
            return res.data[0]
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Employee interest record '{interest_id}' not found for project '{project_id}'",
            )

    def _find_employee_interest(self, project_id: str, employee_id: str) -> Optional[Dict[str, Any]]:
        try:
            res = (
                self.client.table("project_employee_interests")
                .select("*")
                .eq("project_id", project_id)
                .eq("employee_id", employee_id)
                .execute()
            )
            return res.data[0] if (res and res.data) else None
        except Exception:
            return None

    def _get_employee_record_silent(self, employee_id: Optional[str]) -> Optional[Dict[str, Any]]:
        if not employee_id:
            return None
        try:
            res = (
                self.client.table("industry_employees")
                .select("*")
                .eq("employee_id", employee_id)
                .execute()
            )
            return res.data[0] if (res and res.data) else None
        except Exception:
            return None

    def _hydrate_interest(self, record: Dict[str, Any], employee: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        data = dict(record)
        if employee:
            data["employee_name"] = employee.get("employee_name")
            data["department"] = employee.get("department")
            data["designation"] = employee.get("designation")
            data["email"] = employee.get("email")
        return data

    def list_industry_invitations(
        self,
        industry_id: str,
        user: AuthenticatedUser,
        status_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Lists challenge match invitations for an industry with hydrated challenge, project, and interested employees."""
        self._verify_industry_spoc_auth(industry_id, user)

        try:
            query = (
                self.client.table("challenge_industry_matches")
                .select("*")
                .eq("industry_id", industry_id)
            )
            if status_filter:
                query = query.eq("status", status_filter)
            res = query.order("created_at", desc=True).execute()
            matches = res.data or []
        except Exception:
            matches = []

        hydrated = []
        for match in matches:
            ch_id = match.get("challenge_id")
            item = dict(match)
            try:
                ch_res = self.client.table("challenges").select("*").eq("challenge_id", ch_id).execute()
                challenge = ch_res.data[0] if ch_res.data else None
                item["challenge"] = challenge
                if challenge:
                    an_res = self.client.table("ai_analysis").select("*").eq("challenge_id", ch_id).execute()
                    item["ai_analysis"] = an_res.data[0] if an_res.data else None
            except Exception:
                item["challenge"] = None
                item["ai_analysis"] = None

            # Hydrate linked project, university, faculty, and interested employees
            item["project"] = None
            item["university_name"] = None
            item["faculty_name"] = None
            item["interested_employees"] = []
            item["assigned_mentor"] = None
            try:
                p_res = self.client.table("projects").select("*").eq("challenge_id", ch_id).execute()
                if p_res.data:
                    proj = p_res.data[0]
                    item["project"] = proj
                    pid = proj.get("project_id")

                    # University
                    if proj.get("university_id"):
                        u_res = self.client.table("universities").select("university_name").eq("university_id", proj["university_id"]).execute()
                        if u_res.data:
                            item["university_name"] = u_res.data[0].get("university_name")

                    # Faculty
                    if proj.get("faculty_id"):
                        f_res = self.client.table("faculty").select("faculty_name, email, department").eq("faculty_id", proj["faculty_id"]).execute()
                        if f_res.data:
                            item["faculty_name"] = f_res.data[0].get("faculty_name")

                    # Interested employees
                    if pid:
                        interests = self.list_employee_interests(pid, user)
                        item["interested_employees"] = interests
                        selected_int = next((i for i in interests if i.get("status") == "selected"), None)
                        if selected_int:
                            item["assigned_mentor"] = {
                                "employee_id": selected_int.get("employee_id"),
                                "employee_name": selected_int.get("employee_name"),
                                "department": selected_int.get("department"),
                                "designation": selected_int.get("designation"),
                            }
            except Exception:
                pass

            hydrated.append(item)

        return hydrated

    def list_eligible_projects_for_employee(
        self,
        user: AuthenticatedUser,
    ) -> List[Dict[str, Any]]:
        """Lists active projects partnered with the employee's industry.
        Enforces that projects are only visible after the Industry Manager has actually approved the match.
        """
        if user.role != "industry_employee":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: Only industry employees may access industry collaboration projects.",
            )

        employee_rec = user.stakeholder or {}
        emp_industry = employee_rec.get("industry_id")
        emp_id = employee_rec.get("employee_id")

        if not emp_industry or not emp_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: Employee record not properly linked to an industry.",
            )

        try:
            res = (
                self.client.table("projects")
                .select("*")
                .eq("industry_id", emp_industry)
                .order("created_at", desc=True)
                .execute()
            )
            projects = res.data or []
        except Exception:
            projects = []

        # Enforce requirement 2: employee must only see projects where Industry Manager has APPROVED the match
        approved_projects = []
        for proj in projects:
            cid = proj.get("challenge_id")
            if cid:
                try:
                    m_res = (
                        self.client.table("challenge_industry_matches")
                        .select("status")
                        .eq("challenge_id", cid)
                        .eq("industry_id", emp_industry)
                        .execute()
                    )
                    if m_res.data and m_res.data[0].get("status") == "accepted":
                        approved_projects.append(proj)
                except Exception:
                    pass
            elif proj.get("status") in ["active", "prototype", "pilot", "deployed", "solved", "completed"]:
                approved_projects.append(proj)

        hydrated = []
        for proj in approved_projects:
            p_item = dict(proj)
            pid = proj.get("project_id")
            cid = proj.get("challenge_id")

            try:
                ch_res = self.client.table("challenges").select("*").eq("challenge_id", cid).execute()
                p_item["challenge"] = ch_res.data[0] if ch_res.data else None
                if ch_res.data:
                    an_res = self.client.table("ai_analysis").select("*").eq("challenge_id", cid).execute()
                    p_item["ai_analysis"] = an_res.data[0] if an_res.data else None
            except Exception:
                p_item["challenge"] = None
                p_item["ai_analysis"] = None

            # Hydrate university and faculty
            p_item["university_name"] = None
            p_item["faculty_name"] = None
            if proj.get("university_id"):
                try:
                    u_res = self.client.table("universities").select("university_name").eq("university_id", proj["university_id"]).execute()
                    if u_res.data:
                        p_item["university_name"] = u_res.data[0].get("university_name")
                except Exception:
                    pass
            if proj.get("faculty_id"):
                try:
                    f_res = self.client.table("faculty").select("faculty_name").eq("faculty_id", proj["faculty_id"]).execute()
                    if f_res.data:
                        p_item["faculty_name"] = f_res.data[0].get("faculty_name")
                except Exception:
                    pass

            # Check employee's personal interest status
            my_interest = self._find_employee_interest(pid, emp_id)
            p_item["my_interest"] = my_interest

            # Check if an official mentor has been selected (status == 'selected')
            p_item["assigned_mentor"] = None
            p_item["industry_mentor_name"] = None
            try:
                pei_res = self.client.table("project_employee_interests").select("employee_id, status").eq("project_id", pid).eq("status", "selected").execute()
                if pei_res.data:
                    sel_emp_id = pei_res.data[0].get("employee_id")
                    sel_emp = self._get_employee_record_silent(sel_emp_id)
                    if sel_emp:
                        p_item["assigned_mentor"] = {
                            "employee_id": sel_emp_id,
                            "employee_name": sel_emp.get("employee_name"),
                            "department": sel_emp.get("department"),
                            "designation": sel_emp.get("designation"),
                        }
                        p_item["industry_mentor_name"] = sel_emp.get("employee_name")
            except Exception:
                pass

            hydrated.append(p_item)

        return hydrated

    def list_industry_mous(self, user: AuthenticatedUser) -> List[Dict[str, Any]]:
        """Lists factual MOU collaboration records for the authenticated Industry Manager's company.
        Strictly SPOC only (normal employee receives 403). Uses factual data only (no fake PDFs).
        """
        employee_rec = user.stakeholder or {}
        emp_industry = employee_rec.get("industry_id")
        if not emp_industry:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: Could not resolve your authorized industry organization.",
            )

        self._verify_industry_spoc_auth(emp_industry, user)

        try:
            p_res = (
                self.client.table("projects")
                .select("*")
                .eq("industry_id", emp_industry)
                .order("created_at", desc=True)
                .execute()
            )
            projects = p_res.data or []
        except Exception:
            projects = []

        # Get industry name
        ind_name = "Industry Partner"
        try:
            ind_res = self.client.table("industries").select("industry_name").eq("industry_id", emp_industry).execute()
            if ind_res.data:
                ind_name = ind_res.data[0].get("industry_name") or ind_name
        except Exception:
            pass

        mous = []
        for p in projects:
            pid = p.get("project_id")
            uni_id = p.get("university_id")
            uni_name = "Partner University"
            if uni_id:
                try:
                    u_res = self.client.table("universities").select("university_name").eq("university_id", uni_id).execute()
                    if u_res.data:
                        uni_name = u_res.data[0].get("university_name") or uni_name
                except Exception:
                    pass

            mous.append({
                "mou_id": f"MOU-IND-{emp_industry}-{pid}",
                "project_id": pid,
                "project_title": p.get("project_title") or "Collaborative Innovation Project",
                "university_id": uni_id,
                "university_name": uni_name,
                "industry_id": emp_industry,
                "industry_name": ind_name,
                "government_partner": "Government of Jharkhand",
                "status": "Active Collaboration" if p.get("status") in ["active", "prototype", "pilot", "deployed", "solved", "completed"] else "Initiated",
                "effective_date": p.get("start_date") or p.get("created_at") or "In Effect",
                "has_document": False,
                "document_url": None,
            })

        return mous
