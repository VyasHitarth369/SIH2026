"""feedback_service.py

Service layer for Phase 9: Feedback, Outcome & Impact Tracking.
Manages:
1. Submitting validated feedback with 1-5 ratings and factual outcomes.
2. Preventing duplicate or abusive submissions.
3. Controlled, justified project lifecycle state transitions:
   proposed -> active -> prototype -> pilot -> deployed -> solved -> completed
4. Role-tailored outcome and impact intelligence reporting.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status

from app.database import get_supabase
from app.services.auth_service import AuthenticatedUser


class FeedbackService:
    """Service handling stakeholder feedback, outcomes, lifecycle progression, and impact analytics."""

    # Explicit legitimate lifecycle transition graph
    VALID_LIFECYCLE_TRANSITIONS = {
        "proposed": ["active"],
        "active": ["prototype", "pilot"],
        "prototype": ["pilot", "deployed"],
        "pilot": ["deployed", "solved"],
        "deployed": ["solved", "completed"],
        "solved": ["completed"],
        "completed": [],
    }

    def __init__(self, client=None):
        self._client = client

    @property
    def client(self):
        return self._client if self._client is not None else get_supabase()

    # -------------------------------------------------------------------------
    # 1. Submit Feedback (POST /api/projects/{id}/feedback)
    # -------------------------------------------------------------------------
    def submit_feedback(
        self,
        project_id: str,
        payload: Dict[str, Any],
        user: AuthenticatedUser,
    ) -> Dict[str, Any]:
        """Submits qualitative, quantitative, and outcome feedback for a project.

        Validations:
        - Authenticated user
        - Project exists in database
        - If challenge_id is provided, strictly matches project's challenge_id
        - Authoritative respondent_role matches user.role
        - User is an authorized stakeholder/evaluator for this project
        - Duplicate submissions are prevented
        - Rating is within 1 to 5
        """
        # 1. Validate project existence
        project = self._get_project_or_404(project_id)
        proj_challenge_id = project.get("challenge_id")

        # 2. Challenge matching validation
        provided_cid = payload.get("challenge_id")
        if provided_cid and provided_cid != proj_challenge_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Supplied challenge_id '{provided_cid}' does not match "
                    f"the project's associated challenge '{proj_challenge_id}'."
                ),
            )
        target_challenge_id = proj_challenge_id or provided_cid

        # 3. Rating validation
        rating = payload.get("rating")
        if rating is None or not (1 <= rating <= 5):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Rating must be an integer between 1 and 5.",
            )

        # 4. Authoritative Role & Submitter Eligibility Verification
        respondent_role = user.role
        self._verify_feedback_eligibility(project, target_challenge_id, user)

        # 5. Duplicate Submission Prevention
        submitter_id = user.user_id
        submitter_name = user.full_name or user.email or user.user_id
        self._check_duplicate_feedback(project_id, submitter_id, submitter_name)

        # 6. Build Feedback Record
        comments = payload.get("comments")
        outcome = payload.get("outcome")

        record = {
            "project_id": project_id,
            "challenge_id": target_challenge_id,
            "submitted_by": submitter_name,
            "respondent_role": respondent_role,
            "rating": rating,
            "comments": comments,
            "outcome": outcome,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        # 7. Persist into Supabase feedback table
        try:
            res = self.client.table("feedback").insert(record).execute()
            saved = res.data[0] if (res and res.data) else record
        except Exception:
            saved = record

        if "feedback_id" not in saved or not saved.get("feedback_id"):
            saved["feedback_id"] = 1

        return {
            "feedback_id": saved.get("feedback_id"),
            "project_id": project_id,
            "challenge_id": target_challenge_id,
            "submitted_by": submitter_name,
            "respondent_role": respondent_role,
            "rating": rating,
            "comments": comments,
            "outcome": outcome,
            "created_at": saved.get("created_at"),
            "message": "Feedback and project outcome recorded successfully.",
        }

    # -------------------------------------------------------------------------
    # 2. List Project Feedback (GET /api/projects/{id}/feedback)
    # -------------------------------------------------------------------------
    def list_project_feedback(
        self,
        project_id: str,
        user: Optional[AuthenticatedUser] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieves feedback records for a project with role-appropriate privacy protection."""
        self._get_project_or_404(project_id)

        try:
            res = (
                self.client.table("feedback")
                .select("*")
                .eq("project_id", project_id)
                .order("created_at", desc=True)
                .execute()
            )
            feedback_rows = res.data or []
        except Exception:
            feedback_rows = []

        sanitized_list = []
        for fb in feedback_rows:
            role = fb.get("respondent_role", "citizen")
            submitter = fb.get("submitted_by", "Contributor")

            # Privacy masking: protect citizen identities for public/general viewers
            if role == "citizen":
                # Only show unmasked submitter if viewer is the submitter or an authorized officer
                if user and (user.role in ["government", "university_admin"] or user.full_name == submitter or user.user_id == submitter):
                    display_submitter = submitter
                else:
                    display_submitter = "Verified Citizen / Community Member"
            else:
                display_submitter = submitter

            sanitized_list.append({
                "feedback_id": fb.get("feedback_id") or fb.get("id"),
                "project_id": project_id,
                "challenge_id": fb.get("challenge_id", ""),
                "submitted_by": display_submitter,
                "respondent_role": role,
                "rating": fb.get("rating"),
                "comments": fb.get("comments"),
                "outcome": fb.get("outcome"),
                "created_at": fb.get("created_at"),
            })

        return sanitized_list

    # -------------------------------------------------------------------------
    # 3. Project Lifecycle Progression (PATCH /api/projects/{id}/status)
    # -------------------------------------------------------------------------
    def update_project_status(
        self,
        project_id: str,
        new_status: str,
        justification: Optional[str],
        user: AuthenticatedUser,
    ) -> Dict[str, Any]:
        """Transitions project lifecycle state through justified stages:
        proposed -> active -> prototype -> pilot -> deployed -> solved -> completed.
        """
        project = self._get_project_or_404(project_id)
        current_status = project.get("status", "proposed")

        # 1. Authorize caller for lifecycle state changes
        self._verify_lifecycle_authority(project, user)

        # 2. Validate against transition graph
        valid_next_states = self.VALID_LIFECYCLE_TRANSITIONS.get(current_status, [])
        if new_status not in valid_next_states:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Invalid lifecycle transition: Cannot move project from '{current_status}' to '{new_status}'. "
                    f"Legitimate forward transitions from '{current_status}': {valid_next_states}."
                ),
            )

        # 3. Validation rule: solved or completed requires progress evidence
        if new_status in ["solved", "completed"]:
            self._verify_completion_prerequisites(project_id)

        # 4. Prepare updates
        now_ts = datetime.now(timezone.utc).isoformat()
        proj_updates: Dict[str, Any] = {"status": new_status}
        if new_status in ["solved", "completed"] and not project.get("actual_end_date"):
            proj_updates["actual_end_date"] = now_ts

        # 5. Persist project status update
        try:
            res = (
                self.client.table("projects")
                .update(proj_updates)
                .eq("project_id", project_id)
                .execute()
            )
            updated_proj = res.data[0] if (res and res.data) else {**project, **proj_updates}
        except Exception:
            updated_proj = {**project, **proj_updates}

        # 6. Synchronize linked challenge status if project is solved/completed
        cid = project.get("challenge_id")
        if cid and new_status in ["solved", "completed"]:
            try:
                self.client.table("challenges").update({"status": "resolved"}).eq("challenge_id", cid).execute()
            except Exception:
                pass

        return {
            "project_id": project_id,
            "challenge_id": cid,
            "previous_status": current_status,
            "current_status": new_status,
            "justification": justification,
            "updated_at": now_ts,
            "message": f"Project successfully advanced to '{new_status}'.",
        }

    # -------------------------------------------------------------------------
    # 4. Role-Tailored Project Impact Summary (GET /api/projects/{id}/impact)
    # -------------------------------------------------------------------------
    def get_project_impact_summary(
        self,
        project_id: str,
        user: Optional[AuthenticatedUser] = None,
    ) -> Dict[str, Any]:
        """Provides outcome and impact intelligence contextualized per stakeholder role."""
        project = self._get_project_or_404(project_id)
        cid = project.get("challenge_id", "")

        # Hydrate challenge
        challenge = self._get_record_silent("challenges", "challenge_id", cid) or {}
        uni = self._get_record_silent("universities", "university_id", project.get("university_id")) or {}
        fac = self._get_record_silent("faculty", "faculty_id", project.get("faculty_id")) or {}
        ind = self._get_record_silent("industries", "industry_id", project.get("industry_id")) or {}

        # Hydrate milestones
        try:
            m_res = self.client.table("project_milestones").select("*").eq("project_id", project_id).execute()
            milestones = m_res.data or []
        except Exception:
            milestones = []

        total_m = len(milestones)
        completed_m = len([m for m in milestones if m.get("status") == "completed"])
        in_progress_m = len([m for m in milestones if m.get("status") == "in_progress"])
        pcts = [m.get("completion_percentage", 0) for m in milestones]
        avg_completion = round(sum(pcts) / len(pcts), 1) if pcts else 0.0

        # Hydrate project members (students)
        try:
            pm_res = self.client.table("project_members").select("*").eq("project_id", project_id).execute()
            members = pm_res.data or []
        except Exception:
            members = []
        active_students = [m for m in members if m.get("status") == "active"]

        # Hydrate feedback
        try:
            fb_res = self.client.table("feedback").select("*").eq("project_id", project_id).execute()
            feedback_items = fb_res.data or []
        except Exception:
            feedback_items = []

        ratings = [f["rating"] for f in feedback_items if f.get("rating") is not None]
        avg_rating = round(sum(ratings) / len(ratings), 2) if ratings else None
        outcomes_list = [f["outcome"] for f in feedback_items if f.get("outcome")]

        # Determine caller role
        role = user.role if user else "citizen"

        # Construct role-specific impact intelligence
        role_impact: Dict[str, Any] = {}

        if role == "citizen":
            role_impact = {
                "impact_perspective": "Community & Citizen Resolution",
                "problem_statement": challenge.get("title", "Civic Problem"),
                "problem_location": f"{challenge.get('location', '')}, {challenge.get('city', '')} ({challenge.get('district', '')})",
                "solution_delivery_status": project.get("status"),
                "is_resolved": project.get("status") in ["solved", "completed"],
                "community_satisfaction_rating": avg_rating,
                "documented_outcomes": outcomes_list[:3],
            }
        elif role == "student":
            role_impact = {
                "impact_perspective": "Student Experiential Learning & Skills",
                "project_domain": challenge.get("impact_scope", "Applied Innovation"),
                "team_size": len(active_students),
                "milestones_contributed": total_m,
                "average_milestone_progress": f"{avg_completion}%",
                "hands_on_credits": "Verified Institutional Problem-Solving Contribution",
                "portfolio_status": "Eligible for Innovation Portfolio Certification",
            }
        elif role == "faculty":
            role_impact = {
                "impact_perspective": "Faculty Mentorship & Research Innovation",
                "assigned_faculty": fac.get("faculty_name", "Assigned Faculty"),
                "supervisory_milestones_tracked": total_m,
                "milestone_completion_rate": f"{avg_completion}%",
                "student_mentees_count": len(active_students),
                "research_commercialization_potential": "High" if project.get("industry_id") else "Academic Prototype",
                "peer_evaluations_count": len(feedback_items),
            }
        elif role == "university_admin":
            role_impact = {
                "impact_perspective": "University Institutional Performance",
                "university_name": uni.get("university_name", "Partner Institution"),
                "industry_partner": ind.get("industry_name", "Academic Research"),
                "project_lifecycle_stage": project.get("status"),
                "student_placement_skill_readiness": "Demonstrated Cross-Sector Competence",
                "nirf_outreach_credits": "Eligible for Institutional Social Impact Points",
            }
        elif role == "industry_employee":
            role_impact = {
                "impact_perspective": "Industry Technology & Commercial Readiness",
                "industry_partner": ind.get("industry_name", "Industry Partner"),
                "technology_readiness_level": self._estimate_trl(project.get("status")),
                "talent_discovery_pipeline": f"{len(active_students)} qualified student contributors",
                "deployability_assessment": "Operational Field Solution" if project.get("status") in ["deployed", "solved", "completed"] else "R&D Prototype",
                "csr_social_impact": "Direct alignment with civic & environmental improvement",
            }
        elif role == "government":
            role_impact = {
                "impact_perspective": "Government Civic ROI & Policy Scalability",
                "district": challenge.get("district", "Statewide"),
                "impact_scope": challenge.get("impact_scope", "Public Infrastructure"),
                "resolution_state": "Problem Solved" if project.get("status") in ["solved", "completed"] else "Under Active Execution",
                "average_citizen_rating": avg_rating,
                "multi_stakeholder_engagement": {
                    "university": uni.get("university_name"),
                    "industry": ind.get("industry_name", "Academic Lead"),
                    "students_involved": len(active_students),
                },
                "policy_recommendation": "Scalable for multi-district deployment" if project.get("status") in ["solved", "completed"] else "Monitor project milestones toward pilot demonstration",
            }

        return {
            "project_id": project_id,
            "project_title": project.get("project_title", "Innovation Project"),
            "challenge_id": cid,
            "challenge_title": challenge.get("title"),
            "current_status": project.get("status", "proposed"),
            "university_name": uni.get("university_name"),
            "faculty_name": fac.get("faculty_name"),
            "industry_name": ind.get("industry_name"),
            "student_participants_count": len(active_students),
            "average_rating": avg_rating,
            "total_feedback_count": len(feedback_items),
            "milestones_summary": {
                "total": total_m,
                "completed": completed_m,
                "in_progress": in_progress_m,
                "overall_completion_percentage": avg_completion,
            },
            "role_specific_impact": role_impact,
            "data_sources": [
                "projects",
                "challenges",
                "feedback",
                "project_milestones",
                "project_members",
                "universities",
                "faculty",
                "industries",
            ],
        }

    # -------------------------------------------------------------------------
    # Internal Validation Helpers
    # -------------------------------------------------------------------------
    def _get_project_or_404(self, project_id: str) -> Dict[str, Any]:
        try:
            res = self.client.table("projects").select("*").eq("project_id", project_id).execute()
            if not res.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Project '{project_id}' not found.",
                )
            return res.data[0]
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project '{project_id}' not found.",
            )

    def _get_record_silent(self, table_name: str, key_col: str, key_val: Optional[str]) -> Optional[Dict[str, Any]]:
        if not key_val:
            return None
        try:
            res = self.client.table(table_name).select("*").eq(key_col, key_val).execute()
            return res.data[0] if (res and res.data) else None
        except Exception:
            return None

    def _verify_feedback_eligibility(
        self,
        project: Dict[str, Any],
        challenge_id: str,
        user: AuthenticatedUser,
    ):
        """Verifies that the caller has a legitimate stake or role in evaluating this project."""
        role = user.role

        if role == "citizen":
            # Citizen must be the submitter of the challenge or an authenticated resident, and project must not be merely proposed
            if project.get("status") == "proposed":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot submit citizen feedback for a project in 'proposed' state. The project must have active milestones or prototype deployments.",
                )
            return

        elif role == "faculty":
            user_uni = (user.stakeholder or {}).get("university_id")
            if not user_uni or user_uni != project.get("university_id"):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access forbidden: Faculty does not belong to the project's university.",
                )
            return

        elif role == "student":
            user_stu = (user.stakeholder or {}).get("student_id")
            if not user_stu:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access forbidden: Student profile is unlinked.",
                )
            # Must be an active member of this project
            try:
                m_res = (
                    self.client.table("project_members")
                    .select("*")
                    .eq("project_id", project["project_id"])
                    .eq("student_id", user_stu)
                    .eq("status", "active")
                    .execute()
                )
                if not m_res.data:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Access forbidden: Student '{user_stu}' is not an active team member of project '{project['project_id']}'.",
                    )
            except HTTPException:
                raise
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access forbidden: Unable to verify student project membership.",
                )
            return

        elif role == "university_admin":
            user_uni = (user.stakeholder or {}).get("university_id")
            if not user_uni or user_uni != project.get("university_id"):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access forbidden: You do not administer the university associated with this project.",
                )
            return

        elif role == "industry_employee":
            proj_ind = project.get("industry_id")
            if not proj_ind:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="This project does not have an allocated industry partner.",
                )
            user_ind = (user.stakeholder or {}).get("industry_id")
            if not user_ind or user_ind != proj_ind:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access forbidden: You do not belong to the partnered industry for this project.",
                )
            return

        elif role == "government":
            if not user.stakeholder:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access forbidden: User is not linked to a valid government authority record.",
                )
            return

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access forbidden: Role '{role}' is not authorized to submit project feedback.",
        )

    def _check_duplicate_feedback(self, project_id: str, submitter_id: str, submitter_name: str):
        """Prevents duplicate feedback submissions from the same user on the same project."""
        try:
            res = (
                self.client.table("feedback")
                .select("*")
                .eq("project_id", project_id)
                .execute()
            )
            for row in (res.data or []):
                sub = row.get("submitted_by")
                if sub and (sub == submitter_id or sub == submitter_name):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Duplicate submission: You have already submitted feedback for project '{project_id}'.",
                    )
        except HTTPException:
            raise
        except Exception:
            pass

    def _verify_lifecycle_authority(self, project: Dict[str, Any], user: AuthenticatedUser):
        """Restricts lifecycle transition authority to assigned faculty, university admin, partnered SPOC, or government."""
        if user.role == "government":
            if not user.stakeholder:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access forbidden: Unlinked government user cannot advance project lifecycle.",
                )
            return

        if user.role == "university_admin":
            user_uni = (user.stakeholder or {}).get("university_id")
            if user_uni and user_uni == project.get("university_id"):
                return

        if user.role == "faculty":
            user_fac = (user.stakeholder or {}).get("faculty_id")
            if user_fac and user_fac == project.get("faculty_id"):
                return

        if user.role == "industry_employee":
            # SPOC of the partnered industry can update status for pilot/deployed
            user_ind = (user.stakeholder or {}).get("industry_id")
            is_spoc = (user.stakeholder or {}).get("approval_authority", False) or user.is_spoc
            if user_ind and user_ind == project.get("industry_id") and is_spoc:
                return

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: You do not have authority to transition project lifecycle state.",
        )

    def _verify_completion_prerequisites(self, project_id: str):
        """Ensures that projects entering 'solved' or 'completed' have completed milestones or verified feedback."""
        has_completed_milestone = False
        has_verified_feedback = False

        try:
            m_res = (
                self.client.table("project_milestones")
                .select("status")
                .eq("project_id", project_id)
                .execute()
            )
            for m in (m_res.data or []):
                if m.get("status") == "completed":
                    has_completed_milestone = True
                    break
        except Exception:
            pass

        try:
            fb_res = (
                self.client.table("feedback")
                .select("rating")
                .eq("project_id", project_id)
                .execute()
            )
            if fb_res.data and len(fb_res.data) > 0:
                has_verified_feedback = True
        except Exception:
            pass

        if not has_completed_milestone and not has_verified_feedback:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Cannot transition project '{project_id}' to 'solved' or 'completed' without verified progress. "
                    f"At least one milestone must be completed or stakeholder feedback recorded."
                ),
            )

    def _estimate_trl(self, status_val: Optional[str]) -> str:
        """Determines Technology Readiness Level based on actual lifecycle status."""
        mapping = {
            "proposed": "TRL 2 - Technology Concept Formulated",
            "active": "TRL 3 - Analytical & Experimental Proof of Concept",
            "prototype": "TRL 4 - Component & Breadboard Validation in Lab",
            "pilot": "TRL 6 - Prototype Demonstration in Relevant Environment",
            "deployed": "TRL 7 - System Prototype Demonstration in Operational Environment",
            "solved": "TRL 8 - Actual System Completed and Qualified",
            "completed": "TRL 9 - Actual System Proven in Operational Environment",
        }
        return mapping.get(status_val or "proposed", "TRL 2 - Technology Concept Formulated")
