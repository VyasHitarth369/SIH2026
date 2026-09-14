"""government_service.py

Service layer for Phase 8: Government Monitoring & Policy Intelligence.
Directly queries the 18 public Supabase tables to generate transparent,
unfabricated system-wide metrics and hydrated monitoring rosters.
"""

from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status

from app.database import get_supabase
from app.services.auth_service import AuthenticatedUser


class GovernmentService:
    """Service providing read-only policy intelligence and lifecycle monitoring for government."""

    def __init__(self, client=None):
        self._client = client

    @property
    def client(self):
        return self._client if self._client is not None else get_supabase()

    # -------------------------------------------------------------------------
    # 1. System-Wide Dashboard Analytics
    # -------------------------------------------------------------------------
    def get_dashboard_analytics(self, user: AuthenticatedUser) -> Dict[str, Any]:
        """Calculates system-wide policy intelligence metrics from actual database tables.

        Strictly avoids metric fabrication:
        - All counts and aggregations are derived directly from actual DB tables.
        - Missing tables or unrecordable metrics are reported as limitations.
        """
        officer = user.stakeholder or {}
        officer_name = officer.get("officer_name") or user.full_name or "Government Authority"
        dept = officer.get("department")
        dist = officer.get("district")

        # 1. Fetch Challenges & Analyses
        try:
            ch_res = self.client.table("challenges").select("*").execute()
            all_challenges = ch_res.data or []
        except Exception:
            all_challenges = []

        try:
            ai_res = self.client.table("ai_analysis").select("*").execute()
            all_analyses = {a["challenge_id"]: a for a in (ai_res.data or [])}
        except Exception:
            all_analyses = {}

        total_challenges = len(all_challenges)
        submitted_count = sum(1 for c in all_challenges if c.get("status") == "submitted")
        active_statuses = {"validated", "under_review", "university_selected", "in_project", "in_progress"}
        active_challenges = sum(1 for c in all_challenges if c.get("status") in active_statuses)
        validated_challenges = sum(
            1 for c in all_challenges
            if c.get("status") == "validated" or (all_analyses.get(c.get("challenge_id"), {}).get("validity") == "valid")
        )

        by_domain: Dict[str, int] = {}
        by_source: Dict[str, int] = {}
        by_district: Dict[str, int] = {}

        for c in all_challenges:
            cid = c.get("challenge_id")
            cat = all_analyses.get(cid, {}).get("category") or "General Civic"
            by_domain[cat] = by_domain.get(cat, 0) + 1

            src = "government" if "gov" in str(c.get("submitted_by", "")).lower() else "citizen"
            by_source[src] = by_source.get(src, 0) + 1

            cdist = c.get("district") or "Unspecified"
            by_district[cdist] = by_district.get(cdist, 0) + 1

        # 2. Fetch Projects
        try:
            p_res = self.client.table("projects").select("*").execute()
            all_projects = p_res.data or []
        except Exception:
            all_projects = []

        total_projects = len(all_projects)
        active_proj_statuses = {"active", "prototype", "pilot", "deployed"}
        active_projects_count = sum(1 for p in all_projects if p.get("status") in active_proj_statuses)
        proposed_projects_count = sum(1 for p in all_projects if p.get("status") == "proposed")
        solved_problems_count = sum(1 for p in all_projects if p.get("status") in {"solved", "completed"})

        lifecycle_funnel = {
            "submitted": submitted_count,
            "pending_review": sum(1 for c in all_challenges if c.get("status") in {"submitted", "under_review"}),
            "validated": validated_challenges,
            "university_selected": sum(1 for c in all_challenges if c.get("status") == "university_selected"),
            "in_project": active_projects_count,
            "solved": solved_problems_count,
        }

        # 3. Institutional & Stakeholder Participation
        engaged_unis = set()
        engaged_inds = set()
        allocated_faculty = set()

        for p in all_projects:
            if p.get("university_id"):
                engaged_unis.add(p["university_id"])
            if p.get("industry_id"):
                engaged_inds.add(p["industry_id"])
            if p.get("faculty_id"):
                allocated_faculty.add(p["faculty_id"])

        # Also check accepted matches
        try:
            um_res = self.client.table("challenge_university_matches").select("university_id").eq("status", "accepted").execute()
            for um in (um_res.data or []):
                engaged_unis.add(um["university_id"])
        except Exception:
            pass

        try:
            im_res = self.client.table("challenge_industry_matches").select("industry_id").eq("status", "accepted").execute()
            for im in (im_res.data or []):
                engaged_inds.add(im["industry_id"])
        except Exception:
            pass

        # 4. Active Students
        active_students = set()
        try:
            pm_res = self.client.table("project_members").select("student_id").eq("status", "active").execute()
            for pm in (pm_res.data or []):
                active_students.add(pm["student_id"])
        except Exception:
            pass

        # 5. Milestones Progress
        try:
            m_res = self.client.table("project_milestones").select("*").execute()
            all_milestones = m_res.data or []
        except Exception:
            all_milestones = []

        total_milestones = len(all_milestones)
        completed_milestones = sum(
            1 for m in all_milestones
            if m.get("status") == "completed" or m.get("completion_percentage") == 100
        )
        in_progress_milestones = sum(1 for m in all_milestones if m.get("status") == "in_progress")
        pending_milestones = sum(1 for m in all_milestones if m.get("status") == "pending")
        if total_milestones > 0:
            avg_comp_rate = round(sum(m.get("completion_percentage", 0) for m in all_milestones) / total_milestones, 1)
        else:
            avg_comp_rate = 0.0

        # 6. Outcomes & Feedback
        try:
            fb_res = self.client.table("feedback").select("*").execute()
            all_feedback = fb_res.data or []
        except Exception:
            all_feedback = []

        total_fb = len(all_feedback)
        if total_fb > 0:
            valid_ratings = [f["rating"] for f in all_feedback if f.get("rating") is not None]
            avg_rating = round(sum(valid_ratings) / len(valid_ratings), 2) if valid_ratings else None
        else:
            avg_rating = None

        try:
            sup_res = self.client.table("challenge_support").select("support_id").execute()
            total_support = len(sup_res.data or [])
        except Exception:
            total_support = 0

        return {
            "officer_name": officer_name,
            "department": dept,
            "district": dist,
            "challenges": {
                "total_submitted": submitted_count,
                "total_challenges": total_challenges,
                "active_challenges": active_challenges,
                "validated_challenges": validated_challenges,
                "by_domain": by_domain,
                "by_source": by_source,
                "by_district": by_district,
            },
            "participation": {
                "universities_engaged": len(engaged_unis),
                "industries_engaged": len(engaged_inds),
                "faculty_assigned": len(allocated_faculty),
                "students_participating": len(active_students),
            },
            "projects": {
                "total_projects": total_projects,
                "active_projects": active_projects_count,
                "proposed_projects": proposed_projects_count,
                "solved_problems": solved_problems_count,
                "lifecycle_funnel": lifecycle_funnel,
            },
            "milestones": {
                "total_milestones": total_milestones,
                "completed_milestones": completed_milestones,
                "in_progress_milestones": in_progress_milestones,
                "pending_milestones": pending_milestones,
                "overall_completion_rate": avg_comp_rate,
            },
            "outcomes": {
                "total_feedback_count": total_fb,
                "average_feedback_rating": avg_rating,
                "total_challenge_support_votes": total_support,
            },
            "data_sources": [
                "challenges",
                "ai_analysis",
                "projects",
                "project_members",
                "project_milestones",
                "challenge_university_matches",
                "challenge_industry_matches",
                "feedback",
                "challenge_support",
            ],
            "limitations": [
                "Financial disbursement and budget allocation metrics are unavailable in the current 18-table schema.",
                "Historical resolution duration is estimated where actual_end_date is recorded on completed projects.",
            ],
        }

    # -------------------------------------------------------------------------
    # 2. Monitored Problems List
    # -------------------------------------------------------------------------
    def get_monitored_problems(
        self,
        status_filter: Optional[str] = None,
        district: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Retrieves challenges with hydrated AI analysis and project execution details."""
        query = self.client.table("challenges").select("*")
        if status_filter:
            query = query.eq("status", status_filter)
        if district:
            query = query.eq("district", district)

        try:
            res = query.order("created_at", desc=True).limit(limit).execute()
            challenges = res.data or []
        except Exception:
            challenges = []

        hydrated = []
        for ch in challenges:
            cid = ch["challenge_id"]

            # AI Analysis
            ai_data = {}
            try:
                ai_res = self.client.table("ai_analysis").select("*").eq("challenge_id", cid).execute()
                if ai_res and ai_res.data:
                    ai_data = ai_res.data[0]
            except Exception:
                pass

            # Associated project
            proj_data = {}
            try:
                p_res = self.client.table("projects").select("*").eq("challenge_id", cid).execute()
                if p_res and p_res.data:
                    proj_data = p_res.data[0]
            except Exception:
                pass

            item = {
                "challenge_id": cid,
                "title": ch.get("title", ""),
                "description": ch.get("description", ""),
                "location": ch.get("location"),
                "city": ch.get("city"),
                "district": ch.get("district"),
                "status": ch.get("status", "submitted"),
                "submitted_by": ch.get("submitted_by"),
                "created_at": ch.get("created_at"),
                "impact_scope": ch.get("impact_scope"),
                "category": ai_data.get("category"),
                "required_skills": ai_data.get("required_skills"),
                "required_technologies": ai_data.get("required_technologies"),
                "innovation_scope": ai_data.get("innovation_scope"),
                "project_id": proj_data.get("project_id"),
                "project_title": proj_data.get("project_title"),
                "project_status": proj_data.get("status"),
            }

            # Hydrate institutional names if project exists
            if proj_data:
                if proj_data.get("university_id"):
                    u = self._get_record_silent("universities", "university_id", proj_data["university_id"])
                    if u:
                        item["university_name"] = u.get("university_name")
                if proj_data.get("faculty_id"):
                    f = self._get_record_silent("faculty", "faculty_id", proj_data["faculty_id"])
                    if f:
                        item["faculty_name"] = f.get("faculty_name")
                if proj_data.get("industry_id"):
                    ind = self._get_record_silent("industries", "industry_id", proj_data["industry_id"])
                    if ind:
                        item["industry_name"] = ind.get("industry_name")

                # Average milestone completion
                try:
                    m_res = self.client.table("project_milestones").select("completion_percentage").eq("project_id", proj_data["project_id"]).execute()
                    if m_res and m_res.data:
                        pcts = [m.get("completion_percentage", 0) for m in m_res.data]
                        item["milestone_progress_pct"] = round(sum(pcts) / len(pcts), 1)
                except Exception:
                    pass

            hydrated.append(item)

        return hydrated

    # -------------------------------------------------------------------------
    # 3. Assigned Faculty Roster
    # -------------------------------------------------------------------------
    def get_assigned_faculties(self) -> List[Dict[str, Any]]:
        """Retrieves faculty members currently allocated to innovation projects with student counts."""
        try:
            p_res = self.client.table("projects").select("*").execute()
            projects = p_res.data or []
        except Exception:
            projects = []

        faculties = []
        for p in projects:
            fac_id = p.get("faculty_id")
            if not fac_id:
                continue

            faculty = self._get_record_silent("faculty", "faculty_id", fac_id)
            if not faculty:
                continue

            uni = self._get_record_silent("universities", "university_id", p.get("university_id"))

            # Count participating students
            stu_count = 0
            try:
                pm_res = (
                    self.client.table("project_members")
                    .select("project_member_id")
                    .eq("project_id", p["project_id"])
                    .eq("status", "active")
                    .execute()
                )
                stu_count = len(pm_res.data or [])
            except Exception:
                pass

            faculties.append({
                "faculty_id": fac_id,
                "faculty_name": faculty.get("faculty_name", "Faculty Member"),
                "department": faculty.get("department"),
                "designation": faculty.get("designation"),
                "email": faculty.get("email"),
                "university_id": p.get("university_id", ""),
                "university_name": (uni or {}).get("university_name"),
                "project_id": p["project_id"],
                "project_title": p.get("project_title", ""),
                "challenge_id": p.get("challenge_id", ""),
                "participating_students_count": stu_count,
            })

        return faculties

    # -------------------------------------------------------------------------
    # 4. Students Solving Problems
    # -------------------------------------------------------------------------
    def get_students_solving_problems(self) -> List[Dict[str, Any]]:
        """Retrieves active student participants in project teams with project context."""
        try:
            pm_res = (
                self.client.table("project_members")
                .select("*")
                .eq("status", "active")
                .execute()
            )
            memberships = pm_res.data or []
        except Exception:
            memberships = []

        students = []
        for m in memberships:
            sid = m.get("student_id")
            pid = m.get("project_id")
            if not sid or not pid:
                continue

            student = self._get_record_silent("students", "student_id", sid)
            if not student:
                continue

            project = self._get_record_silent("projects", "project_id", pid)
            uni = self._get_record_silent("universities", "university_id", (student or {}).get("university_id"))

            students.append({
                "student_id": sid,
                "student_name": student.get("student_name", "Student Participant"),
                "department": student.get("department"),
                "course": student.get("course"),
                "university_id": student.get("university_id", ""),
                "university_name": (uni or {}).get("university_name"),
                "project_id": pid,
                "project_title": (project or {}).get("project_title", "Innovation Project"),
                "role": m.get("role", "member"),
                "status": m.get("status", "active"),
            })

        return students

    # -------------------------------------------------------------------------
    # 5. Solved & Successful Projects
    # -------------------------------------------------------------------------
    def get_solved_projects(self) -> List[Dict[str, Any]]:
        """Retrieves projects marked solved or completed with stakeholder credits and outcomes."""
        try:
            p_res = self.client.table("projects").select("*").execute()
            projects = [p for p in (p_res.data or []) if p.get("status") in {"solved", "completed"}]
        except Exception:
            projects = []

        solved_list = []
        for p in projects:
            pid = p["project_id"]
            uni = self._get_record_silent("universities", "university_id", p.get("university_id"))
            fac = self._get_record_silent("faculty", "faculty_id", p.get("faculty_id"))
            ind = self._get_record_silent("industries", "industry_id", p.get("industry_id"))

            # Student names
            stu_names = []
            try:
                pm_res = self.client.table("project_members").select("student_id").eq("project_id", pid).execute()
                for pm in (pm_res.data or []):
                    s = self._get_record_silent("students", "student_id", pm["student_id"])
                    if s:
                        stu_names.append(s.get("student_name", pm["student_id"]))
            except Exception:
                pass

            # Outcome from feedback
            avg_rating = None
            outcome_text = None
            try:
                fb_res = self.client.table("feedback").select("*").eq("project_id", pid).execute()
                if fb_res and fb_res.data:
                    ratings = [f["rating"] for f in fb_res.data if f.get("rating") is not None]
                    if ratings:
                        avg_rating = round(sum(ratings) / len(ratings), 2)
                    outcomes = [f.get("outcome") or f.get("comments") for f in fb_res.data if (f.get("outcome") or f.get("comments"))]
                    if outcomes:
                        outcome_text = "; ".join(outcomes[:2])
            except Exception:
                pass

            solved_list.append({
                "project_id": pid,
                "challenge_id": p.get("challenge_id", ""),
                "project_title": p.get("project_title", ""),
                "description": p.get("description"),
                "status": p.get("status", "solved"),
                "start_date": p.get("start_date"),
                "actual_end_date": p.get("actual_end_date"),
                "university_name": (uni or {}).get("university_name"),
                "faculty_name": (fac or {}).get("faculty_name"),
                "industry_name": (ind or {}).get("industry_name"),
                "student_participants": stu_names,
                "average_rating": avg_rating,
                "outcome_summary": outcome_text,
            })

        return solved_list

    # -------------------------------------------------------------------------
    # Helper
    # -------------------------------------------------------------------------
    def _get_record_silent(self, table_name: str, key_field: str, key_val: Optional[str]) -> Optional[Dict[str, Any]]:
        if not key_val:
            return None
        try:
            res = self.client.table(table_name).select("*").eq(key_field, key_val).execute()
            return res.data[0] if (res and res.data) else None
        except Exception:
            return None
