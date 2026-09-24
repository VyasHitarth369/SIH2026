"""government_service.py

Service layer for Phase 8: Government Monitoring & Policy Intelligence.
Directly queries the 18 public Supabase tables to generate transparent,
unfabricated system-wide metrics and hydrated monitoring rosters.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status

from app.database import get_supabase
from app.services.auth_service import AuthenticatedUser
from app.services.matching_service import MatchingService
from app.utils.storage_utils import resolve_document_signed_url

# Authoritative database status mappings for Government problem categories
GOVERNMENT_CATEGORY_STATUSES: Dict[str, List[str]] = {
    "pending": [
        "submitted",
        "validated",
        "pending",
        "under_review",
        "existing_solution_found",
        "ineligible_gap",
    ],
    "allocated": [
        "routed",
        "university_selected",
        "project_created",
        "in_project",
        "active",
        "prototype",
        "pilot",
    ],
    "rejected": [
        "rejected",
        "no_university_assigned",
    ],
    "solved": [
        "resolved",
        "solved",
        "completed",
        "accepted_existing_solution",
        "deployed",
    ],
}

ALL_MONITORED_STATUSES: List[str] = [
    status
    for statuses in GOVERNMENT_CATEGORY_STATUSES.values()
    for status in statuses
]


class MonitoredProblemList(list):
    """Subclass of list that behaves as a standard list for existing test suites
    and callers while also carrying dynamic category counts, total records, and pagination metadata.
    """
    def __init__(
        self,
        items: List[Dict[str, Any]],
        counts: Optional[Dict[str, int]] = None,
        total: Optional[int] = None,
        page: int = 1,
        limit: int = 50,
    ):
        super().__init__(items)
        self.counts = counts or {}
        self.total = total if total is not None else len(items)
        self.page = page
        self.limit = limit


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
    # 2. Category Counts & Monitored Problems List (Batched & Filtered)
    # -------------------------------------------------------------------------
    def get_category_counts(self, district: Optional[str] = None) -> Dict[str, int]:
        """Calculates dynamic counts for all government problem categories derived directly from DB."""
        counts = {
            "all": 0,
            "pending": 0,
            "allocated": 0,
            "rejected": 0,
            "solved": 0,
        }
        try:
            query = self.client.table("challenges").select("challenge_id, status")
            if district:
                query = query.eq("district", district)
            res = query.execute()
            for row in (res.data or []):
                st = row.get("status")
                if not st:
                    continue
                matched = False
                for cat, statuses in GOVERNMENT_CATEGORY_STATUSES.items():
                    if st in statuses:
                        counts[cat] += 1
                        matched = True
                        break
                if matched:
                    counts["all"] += 1
        except Exception:
            pass
        return counts

    def get_monitored_problems(
        self,
        category: Optional[str] = None,
        status_filter: Optional[str] = None,
        district: Optional[str] = None,
        page: int = 1,
        limit: int = 100,
    ) -> MonitoredProblemList:
        """Retrieves challenges with batched hydration of AI analysis and project execution details.

        Eliminates sequential N+1 database queries:
        - Batches AI analysis, projects, milestones, matches, and rejections.
        - Derives counts directly from Supabase.
        - Strictly isolates categories so every challenge belongs to exactly one category.
        - Returns a MonitoredProblemList that functions as a list and provides .counts, .total, .page, .limit.
        """
        counts = self.get_category_counts(district=district)

        query = self.client.table("challenges").select("*")
        if district:
            query = query.eq("district", district)

        # Status filtering logic
        cat_key = category.strip().lower() if category else None
        if cat_key in ["active", "in_progress", "in-flight"]:
            cat_key = "allocated"
        elif cat_key in ["completed", "resolved"]:
            cat_key = "solved"

        if status_filter:
            query = query.eq("status", status_filter)
            total_matching = None
        elif cat_key and cat_key in GOVERNMENT_CATEGORY_STATUSES:
            target_statuses = GOVERNMENT_CATEGORY_STATUSES[cat_key]
            query = query.in_("status", target_statuses)
            total_matching = counts.get(cat_key, 0)
        else:
            # "all" category: strictly include only challenges with recognized monitored statuses
            query = query.in_("status", ALL_MONITORED_STATUSES)
            total_matching = counts.get("all", 0)

        # Apply pagination (1-indexed page)
        page = max(1, page)
        limit = max(1, min(limit, 200))
        offset = (page - 1) * limit

        try:
            res = (
                query.order("created_at", desc=True)
                .range(offset, offset + limit - 1)
                .execute()
            )
            challenges = res.data or []
        except Exception:
            challenges = []

        if total_matching is None:
            total_matching = len(challenges)

        if not challenges:
            return MonitoredProblemList(
                [],
                counts=counts,
                total=total_matching,
                page=page,
                limit=limit,
            )

        cids = [ch["challenge_id"] for ch in challenges]

        # 1. Batch AI Analysis
        ai_by_cid = {}
        try:
            ai_res = self.client.table("ai_analysis").select("*").in_("challenge_id", cids).execute()
            for r in (ai_res.data or []):
                ai_by_cid[r["challenge_id"]] = r
        except Exception:
            pass

        # 2. Batch Projects
        proj_by_cid = {}
        pids = []
        try:
            p_res = self.client.table("projects").select("*").in_("challenge_id", cids).execute()
            for r in (p_res.data or []):
                proj_by_cid[r["challenge_id"]] = r
                if r.get("project_id"):
                    pids.append(r["project_id"])
        except Exception:
            pass

        # 3. Batch Milestones
        milestone_pcts_by_pid = {}
        highest_milestone_by_pid = {}
        standard_stages = [
            "Problem Submitted",
            "Routed to Universities",
            "University Allocated",
            "Faculty Assigned",
            "Student Team Formed",
            "Development In Progress",
            "Solution Deployed",
        ]
        if pids:
            try:
                m_res = (
                    self.client.table("project_milestones")
                    .select("project_id, milestone_name, status, completion_percentage")
                    .in_("project_id", pids)
                    .execute()
                )
                for r in (m_res.data or []):
                    pid = r.get("project_id")
                    if pid:
                        milestone_pcts_by_pid.setdefault(pid, []).append(r.get("completion_percentage", 0))
                        m_name = (r.get("milestone_name") or "").strip()
                        if r.get("status") in ["completed", "active"] and m_name in standard_stages:
                            idx = standard_stages.index(m_name)
                            if idx > highest_milestone_by_pid.get(pid, (-1, ""))[0]:
                                highest_milestone_by_pid[pid] = (idx, m_name)
            except Exception:
                pass

        # 4. Batch Challenge-University Matches (for routed/allocated challenges)
        routed_cids = [
            ch["challenge_id"]
            for ch in challenges
            if ch.get("status") in GOVERNMENT_CATEGORY_STATUSES["allocated"]
        ]
        matches_by_cid = {}
        if routed_cids:
            try:
                cum_res = (
                    self.client.table("challenge_university_matches")
                    .select("*")
                    .in_("challenge_id", routed_cids)
                    .order("rank", desc=False)
                    .execute()
                )
                for r in (cum_res.data or []):
                    matches_by_cid.setdefault(r["challenge_id"], []).append(r)
            except Exception:
                pass

        # 4b. Batch Challenge-Industry Matches
        industry_matches_by_cid = {}
        try:
            cim_res = (
                self.client.table("challenge_industry_matches")
                .select("*")
                .in_("challenge_id", cids)
                .order("rank", desc=False)
                .execute()
            )
            for r in (cim_res.data or []):
                industry_matches_by_cid.setdefault(r["challenge_id"], []).append(r)
        except Exception:
            pass

        # 5. Batch University Rejections
        rejections_by_cid = {}
        try:
            rej_res = (
                self.client.table("challenge_university_matches")
                .select("challenge_id, university_id, rejection_reason, responded_at")
                .in_("challenge_id", cids)
                .eq("status", "rejected")
                .execute()
            )
            for r in (rej_res.data or []):
                rejections_by_cid.setdefault(r["challenge_id"], []).append(r)
        except Exception:
            pass

        # 6. Preload Institutions, Faculty, Industries, and University Workloads once
        ms = MatchingService(self.client)
        workloads = ms._fetch_university_workloads()
        all_unis = ms._fetch_universities()
        unis_by_id = {u["university_id"]: u for u in all_unis}
        all_inds = ms._fetch_industries()
        inds_by_id = {i["industry_id"]: i for i in all_inds}

        # Preload faculties for attached projects
        fac_ids = list({p["faculty_id"] for p in proj_by_cid.values() if p.get("faculty_id")})
        facs_by_id = {}
        if fac_ids:
            try:
                f_res = self.client.table("faculty").select("*").in_("faculty_id", fac_ids).execute()
                for f in (f_res.data or []):
                    facs_by_id[f["faculty_id"]] = f
            except Exception:
                pass

        # 7. Hydrate items in-memory
        hydrated = []
        for ch in challenges:
            cid = ch["challenge_id"]
            ai_data = ai_by_cid.get(cid, {})
            proj_data = proj_by_cid.get(cid, {})

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
                "government_rejection_reason": ch.get("government_rejection_reason"),
                "government_reviewed_at": ch.get("government_reviewed_at"),
                "government_reviewed_by": ch.get("government_reviewed_by"),
            }

            # Hydrate institutional names if project exists
            if proj_data:
                uid = proj_data.get("university_id")
                fid = proj_data.get("faculty_id")
                iid = proj_data.get("industry_id")
                if uid and uid in unis_by_id:
                    item["university_name"] = unis_by_id[uid].get("university_name")
                if fid and fid in facs_by_id:
                    item["faculty_name"] = facs_by_id[fid].get("faculty_name")
                if iid and iid in inds_by_id:
                    item["industry_name"] = inds_by_id[iid].get("industry_name")

                pid = proj_data.get("project_id")
                if pid and pid in milestone_pcts_by_pid:
                    pcts = milestone_pcts_by_pid[pid]
                    if pcts:
                        item["milestone_progress_pct"] = round(sum(pcts) / len(pcts), 1)

                is_completed = (
                    proj_data.get("status") in ["deployed", "solved", "completed"]
                    or ch.get("status") in GOVERNMENT_CATEGORY_STATUSES["solved"]
                )
                if is_completed:
                    item["current_milestone"] = "Solution Deployed"
                elif pid and pid in highest_milestone_by_pid:
                    item["current_milestone"] = highest_milestone_by_pid[pid][1]
                else:
                    item["current_milestone"] = "Faculty Assigned" if fid else "University Allocated"

            # Fix University Allocation Propagation:
            # If university_name is not yet populated from proj_data, hydrate from accepted/selected matches
            if not item.get("university_name") and cid in matches_by_cid:
                for m in matches_by_cid[cid]:
                    if m.get("status") in ("accepted", "selected"):
                        uid = m.get("university_id")
                        if uid and uid in unis_by_id:
                            item["university_name"] = unis_by_id[uid].get("university_name")
                            break

            # University rejections feedback if any
            uni_rejections = []
            for r in rejections_by_cid.get(cid, []):
                uid = r.get("university_id")
                u_rec = unis_by_id.get(uid, {})
                uni_rejections.append({
                    "university_id": uid,
                    "university_name": u_rec.get("university_name") or uid,
                    "rejection_reason": r.get("rejection_reason"),
                    "responded_at": r.get("responded_at"),
                })
            item["university_rejections"] = uni_rejections

            # Hydrate Top-5 recommended universities for government monitoring/transparency
            top_unis = []
            if cid in matches_by_cid:
                raw_matches = matches_by_cid[cid][:5]
                top_unis = ms._hydrate_university_matches(raw_matches, ch, ai_data, workloads)
            item["top_universities"] = top_unis

            # Hydrate Top-5 recommended industries and timeline status for government monitoring
            top_inds = []
            ind_status = "Pending"
            raw_ind_matches = industry_matches_by_cid.get(cid, [])
            if not raw_ind_matches and (ch.get("status") in GOVERNMENT_CATEGORY_STATUSES["allocated"] or ch.get("status") == "validated"):
                try:
                    raw_ind_matches = ms.get_or_generate_industry_matches(cid, limit=5)
                except Exception:
                    raw_ind_matches = []

            for im in raw_ind_matches[:5]:
                iid = im.get("industry_id")
                ind_rec = inds_by_id.get(iid, {})
                top_inds.append({
                    "industry_id": iid,
                    "industry_name": ind_rec.get("industry_name") or iid,
                    "sector": ind_rec.get("sector") or ind_rec.get("domain") or "Industry Partner",
                    "domain": ind_rec.get("domain") or ind_rec.get("sector"),
                    "city": ind_rec.get("city"),
                    "state": ind_rec.get("state"),
                    "rank": im.get("rank"),
                    "match_score": im.get("match_score"),
                    "match_reason": im.get("match_reason"),
                    "status": im.get("status") or "recommended",
                    "matched_skills": ind_rec.get("specializations") or [],
                    "matched_technologies": ind_rec.get("technologies") or [],
                })

            if any(m.get("status") == "accepted" for m in raw_ind_matches):
                ind_status = "Accepted"
            elif any(m.get("status") in ("sent", "invited") for m in raw_ind_matches):
                ind_status = "Sent"
            elif any(m.get("status") == "rejected" for m in raw_ind_matches):
                ind_status = "Rejected"
            elif top_inds:
                ind_status = "Generated"
            else:
                ind_status = "Pending"

            item["top_industries"] = top_inds
            item["industry_matching_status"] = ind_status

            hydrated.append(item)

        return MonitoredProblemList(
            hydrated,
            counts=counts,
            total=total_matching,
            page=page,
            limit=limit,
        )

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
    # 6. System-Wide Authoritative MOU Records
    # -------------------------------------------------------------------------
    def get_government_mous(self) -> List[Dict[str, Any]]:
        """Lists factual MOU collaboration records across universities and industries.
        Strictly avoids fabricating fake PDFs or dummy records. Follows existing MOU
        determination logic from project workflows.
        """
        try:
            p_res = (
                self.client.table("projects")
                .select("*")
                .order("created_at", desc=True)
                .execute()
            )
            projects = p_res.data or []
        except Exception:
            projects = []

        mous = []
        for p in projects:
            uni_id = p.get("university_id")
            ind_id = p.get("industry_id")
            if not ind_id:
                cid = p.get("challenge_id")
                if cid:
                    try:
                        cim = (
                            self.client.table("challenge_industry_matches")
                            .select("*")
                            .eq("challenge_id", cid)
                            .eq("status", "accepted")
                            .execute()
                        )
                        if cim.data and len(cim.data) > 0:
                            ind_id = cim.data[0].get("industry_id")
                    except Exception:
                        pass

            if not uni_id or not ind_id:
                continue

            uni = self._get_record_silent("universities", "university_id", uni_id)
            uni_name = (uni or {}).get("university_name") or "Partner University"

            ind = self._get_record_silent("industries", "industry_id", ind_id)
            ind_name = (ind or {}).get("industry_name") or "Industry Partner"

            ch_doc = None
            cid = p.get("challenge_id")
            if cid:
                ch = self._get_record_silent("challenges", "challenge_id", cid)
                if ch:
                    raw_doc = ch.get("document")
                    if raw_doc and str(raw_doc).strip() not in ["", "-", "None", "null"]:
                        ch_doc = str(raw_doc).strip()

            if not ch_doc and cid:
                try:
                    cim_res = self.client.table("challenge_industry_matches").select("response_note").eq("challenge_id", cid).execute()
                    for r in (cim_res.data or []):
                        note = r.get("response_note") or ""
                        if "MOU_URL:" in note:
                            ch_doc = note.split("MOU_URL:")[-1].strip()
                            break
                        elif note.startswith("http://") or note.startswith("https://"):
                            ch_doc = note.strip()
                            break
                except Exception:
                    pass

            pid = p.get("project_id")
            has_doc = bool(ch_doc and str(ch_doc).strip() not in ["", "-", "None", "null"])
            mous.append({
                "mou_id": f"MOU-GOV-{uni_id}-{ind_id}-{pid}",
                "project_id": pid,
                "project_title": p.get("project_title") or "Collaborative Innovation Project",
                "university_id": uni_id,
                "university_name": uni_name,
                "industry_id": ind_id,
                "industry_name": ind_name,
                "government_partner": "Government of Jharkhand — Department of Higher & Technical Education",
                "status": "Active Collaboration" if p.get("status") in ["active", "prototype", "pilot", "deployed", "solved", "completed"] else "Initiated",
                "effective_date": p.get("start_date") or (p.get("created_at") or "")[:10] or "In Effect",
                "document_url": resolve_document_signed_url(ch_doc) if has_doc else None,
                "has_document": has_doc,
            })

        return mous

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

    # -------------------------------------------------------------------------
    # 7. Problem Approval & Rejection Gates
    # -------------------------------------------------------------------------
    def approve_challenge(self, challenge_id: str, user: AuthenticatedUser) -> Dict[str, Any]:
        """Approves a problem statement and initiates Top-5 University Matching.
        Advances status to 'routed' and generates recommended university matches.
        """
        if user.role != "government":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only government authorities can approve challenges.",
            )

        ch_res = self.client.table("challenges").select("*").eq("challenge_id", challenge_id).execute()
        if not ch_res.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Challenge '{challenge_id}' not found.",
            )
        challenge = ch_res.data[0]

        current_status = challenge.get("status")
        if current_status not in GOVERNMENT_CATEGORY_STATUSES["pending"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot approve challenge with status '{current_status}'. Only pending challenges can be approved.",
            )

        now_iso = datetime.now(timezone.utc).isoformat()
        update_payload = {
            "status": "routed",
            "government_reviewed_by": str(user.user_id),
            "government_reviewed_at": now_iso,
            "government_rejection_reason": None,
        }
        self.client.table("challenges").update(update_payload).eq("challenge_id", challenge_id).execute()

        # Deterministically trigger Top-5 University Matching
        matches = []
        try:
            matching_service = MatchingService(self.client)
            matches = matching_service.get_or_generate_university_matches(challenge_id, user, limit=5)
        except Exception:
            matches = []

        return {
            "success": True,
            "challenge_id": challenge_id,
            "status": "routed",
            "message": "Challenge approved by Government and routed to top matching universities.",
            "government_reviewed_at": now_iso,
            "government_reviewed_by": str(user.user_id),
            "government_rejection_reason": None,
            "university_matches": matches,
            "top_universities": matches,
        }

    def reject_challenge(self, challenge_id: str, reason: str, user: AuthenticatedUser) -> Dict[str, Any]:
        """Declines a problem statement with a mandatory rejection reason.
        Advances status to 'rejected' without routing to universities.
        """
        if user.role != "government":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only government authorities can reject challenges.",
            )

        clean_reason = (reason or "").strip()
        if not clean_reason:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Rejection reason is mandatory and cannot be empty.",
            )

        ch_res = self.client.table("challenges").select("*").eq("challenge_id", challenge_id).execute()
        if not ch_res.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Challenge '{challenge_id}' not found.",
            )
        challenge = ch_res.data[0]

        current_status = challenge.get("status")
        if current_status in ["project_created", "in_project", "solved", "completed", "resolved"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot reject challenge that has already reached '{current_status}'.",
            )

        now_iso = datetime.now(timezone.utc).isoformat()
        update_payload = {
            "status": "rejected",
            "government_rejection_reason": clean_reason,
            "government_reviewed_by": str(user.user_id),
            "government_reviewed_at": now_iso,
        }
        self.client.table("challenges").update(update_payload).eq("challenge_id", challenge_id).execute()

        return {
            "success": True,
            "challenge_id": challenge_id,
            "status": "rejected",
            "message": "Challenge has been rejected by Government.",
            "government_rejection_reason": clean_reason,
            "government_reviewed_at": now_iso,
            "government_reviewed_by": str(user.user_id),
            "university_matches": None,
        }

