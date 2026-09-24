"""challenge_service.py

Handles citizen challenge submission, status lifecycle, ownership enforcement,
and coordinates with AIService to persist review results into the Supabase
challenges and ai_analysis tables.
"""

import json
import logging
import uuid
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status

from app.database import get_supabase
from app.services.ai_service import AIService, compute_jaccard_similarity, compute_multi_signal_similarity
from app.services.auth_service import AuthenticatedUser
from app.services.project_workflow_service import ProjectWorkflowService

logger = logging.getLogger("challenge_service")


class ChallengeService:
    """Service managing challenge submissions, state transitions, and AI review workflows."""

    def __init__(self, ai_service: Optional[AIService] = None, client=None):
        if ai_service is not None and not isinstance(ai_service, AIService) and hasattr(ai_service, "table"):
            client = ai_service
            ai_service = None
        self.ai_service = ai_service or AIService()
        self._client = client

    @property
    def client(self):
        return self._client if self._client is not None else get_supabase()

    def _unpack_ai_analysis(self, analysis: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Unpacks the namespaced Call 1 evidence envelope stored in similar_challenges."""
        if not analysis or not isinstance(analysis, dict):
            return analysis
        res = dict(analysis)
        sim_raw = res.get("similar_challenges")
        if sim_raw and isinstance(sim_raw, str):
            try:
                parsed = json.loads(sim_raw)
                if isinstance(parsed, dict) and parsed.get("schema_version") == 1:
                    obj = parsed.get("objective_evidence") or {}
                    for k, v in obj.items():
                        if k not in res or res[k] is None:
                            res[k] = v
                    if "validity_raw" in obj and obj["validity_raw"]:
                        res["validity"] = obj["validity_raw"]
                        res["validity_raw"] = obj["validity_raw"]
                    if "innovation_scope_raw" in obj and obj["innovation_scope_raw"]:
                        res["innovation_scope"] = obj["innovation_scope_raw"]
                        res["innovation_scope_raw"] = obj["innovation_scope_raw"]
                    img = parsed.get("image_evidence") or {}
                    if "image_evidence_status" not in res:
                        res["image_evidence_status"] = img.get("status")
                        res["image_evidence_confidence"] = img.get("confidence")
                        res["image_observations"] = img.get("observations")
                    ext = parsed.get("external_search") or {}
                    if "external_search_status" not in res:
                        res["external_search_status"] = ext.get("search_status")
                        res["existing_solution_found"] = ext.get("existing_solution_found")
                    internal = parsed.get("internal_search") or {}
                    if "internal_search_status" not in res:
                        res["internal_search_status"] = internal.get("search_status")
                    if "internal_solutions" not in res:
                        res["internal_solutions"] = internal.get("solutions", [])
                    if "solutions" not in res:
                        res["solutions"] = internal.get("solutions", []) + ext.get("solutions", [])
                    res["candidate_relationships"] = parsed.get("similar_challenges", [])
                    res["similar_challenges_list"] = parsed.get("similar_challenges", [])
            except Exception:
                pass
        return res


    # -------------------------------------------------------------------------
    # 1. Challenge Submission & Queries
    # -------------------------------------------------------------------------
    def create_challenge(
        self,
        payload: Dict[str, Any],
        user: Optional[AuthenticatedUser] = None,
    ) -> Dict[str, Any]:
        """Creates and persists a new challenge in public.challenges."""
        title = payload.get("title", "").strip()
        description = payload.get("description", "").strip()

        if not title:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Challenge title cannot be empty",
            )
        if not description:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Challenge description cannot be empty",
            )

        # Generate standard transactional text ID if not provided
        challenge_id = payload.get("challenge_id") or f"CHL-{uuid.uuid4().hex[:8].upper()}"

        # Strictly enforce impact_scope (never impact_score)
        impact_scope = payload.get("impact_scope") or "Area Specific"

        # Authoritatively associate with authenticated user ID if provided
        if user and user.user_id:
            raw_uid = user.user_id
            submitted_by = user.full_name or user.email or payload.get("submitted_by") or "Citizen"
        else:
            raw_uid = payload.get("user_id")
            submitted_by = payload.get("submitted_by") or "Citizen"
        valid_uid = None
        if raw_uid:
            try:
                uuid.UUID(str(raw_uid))
                valid_uid = str(raw_uid)
            except (ValueError, AttributeError):
                # If mock string provided in tests, generate valid deterministic UUID
                valid_uid = str(uuid.uuid5(uuid.NAMESPACE_DNS, str(raw_uid)))

        record = {
            "challenge_id": challenge_id,
            "title": title,
            "description": description,
            "location": payload.get("location"),
            "city": payload.get("city"),
            "district": payload.get("district") or payload.get("city"),
            "address": payload.get("address"),
            "pincode": payload.get("pincode"),
            "impact_scope": impact_scope,
            "photo": payload.get("photo"),
            "video": payload.get("video"),
            "document": payload.get("document"),
            "expected_solution": payload.get("expected_solution"),
            "submitted_by": submitted_by,
            "status": "submitted",
            "user_id": valid_uid,
        }

        # Filter out None values to let Postgres defaults handle unset fields
        clean_record = {k: v for k, v in record.items() if v is not None}

        res = self.client.table("challenges").insert(clean_record).execute()
        return res.data[0] if res.data else clean_record

    def get_challenge(self, challenge_id: str, user: Optional[AuthenticatedUser] = None) -> Dict[str, Any]:
        """Retrieves a single challenge and hydrates its associated ai_analysis if available."""
        res = (
            self.client.table("challenges")
            .select("*")
            .eq("challenge_id", challenge_id)
            .execute()
        )
        if not res.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Challenge '{challenge_id}' not found",
            )

        challenge = res.data[0]

        # Hydrate ai_analysis
        try:
            analysis_res = (
                self.client.table("ai_analysis")
                .select("*")
                .eq("challenge_id", challenge_id)
                .execute()
            )
            raw_ai = analysis_res.data[0] if analysis_res.data else None
            challenge["ai_analysis"] = self._unpack_ai_analysis(raw_ai)
        except Exception:
            challenge["ai_analysis"] = None

        # Hydrate project progress safely (without private personal details)
        try:
            p_res = (
                self.client.table("projects")
                .select("project_id, project_title, status, university_id, industry_id")
                .eq("challenge_id", challenge_id)
                .execute()
            )
            if p_res.data and len(p_res.data) > 0:
                proj = p_res.data[0]
                u_res = self.client.table("universities").select("university_name").eq("university_id", proj.get("university_id")).execute()
                proj["university_name"] = u_res.data[0].get("university_name") if (u_res and u_res.data) else proj.get("university_id")
                if proj.get("industry_id"):
                    i_res = self.client.table("industries").select("industry_name").eq("industry_id", proj.get("industry_id")).execute()
                    proj["industry_name"] = i_res.data[0].get("industry_name") if (i_res and i_res.data) else proj.get("industry_id")
                challenge["project"] = proj
            else:
                challenge["project"] = None
        except Exception:
            challenge["project"] = None

        # Hydrate university rejections with server-side authorization (Amendment 4)
        rejections = []
        try:
            m_res = self.client.table("challenge_university_matches").select("*").eq("challenge_id", challenge_id).eq("status", "rejected").execute()
            raw_matches = m_res.data or []
            if raw_matches and user:
                user_role = getattr(user, "role", None)
                user_uuid = str(getattr(user, "user_id", ""))
                sub_by = str(challenge.get("submitted_by") or "").lower()
                ch_uid = str(challenge.get("user_id") or "")
                user_email = str(getattr(user, "email", "")).lower()

                is_gov = user_role == "government"
                is_submitter = bool(
                    (user_uuid and user_uuid == ch_uid)
                    or (user_email and user_email == sub_by)
                )
                if not is_submitter and user_uuid:
                    try:
                        dns_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, user_uuid))
                        if dns_uuid == ch_uid:
                            is_submitter = True
                    except Exception:
                        pass

                admin_uni = None
                if user_role == "university_admin":
                    from app.services.university_workflow_service import UniversityWorkflowService
                    admin_rec = UniversityWorkflowService(self.client)._resolve_university_admin_record(user)
                    admin_uni = (admin_rec or {}).get("university_id") or getattr(user, "university_id", None)

                for m in raw_matches:
                    match_uni = m.get("university_id")
                    is_rejecting_uni = (user_role == "university_admin" and admin_uni and admin_uni == match_uni)

                    if is_gov or is_submitter or is_rejecting_uni:
                        u_res = self.client.table("universities").select("university_name").eq("university_id", match_uni).execute()
                        u_name = u_res.data[0].get("university_name") if (u_res and u_res.data) else match_uni
                        rejections.append({
                            "university_id": match_uni,
                            "university_name": u_name,
                            "rejection_reason": m.get("response_note") or "Problem statement declined by university administration.",
                            "rejected_at": m.get("responded_at"),
                        })
        except Exception:
            pass
        challenge["university_rejections"] = rejections

        return challenge

    def list_challenges(
        self,
        status_filter: Optional[str] = None,
        city_filter: Optional[str] = None,
        user_id_filter: Optional[str] = None,
        limit: int = 100,
        user: Optional[AuthenticatedUser] = None,
    ) -> List[Dict[str, Any]]:
        """Lists challenges with optional filtering by status, city, or user_id.

        Sanitizes data for public listing, hydrates vote counts, and identifies if user has voted.
        """
        query = self.client.table("challenges").select("*")
        if status_filter:
            query = query.eq("status", status_filter)
        if city_filter:
            query = query.eq("city", city_filter)
        if user_id_filter:
            query = query.eq("user_id", user_id_filter)

        query = query.order("created_at", desc=True, nullsfirst=False).limit(limit)
        res = query.execute()
        challenges = res.data or []
        if not challenges:
            return []

        # Batch hydrate votes and project info
        challenge_ids = [c["challenge_id"] for c in challenges]
        vote_counts: Dict[str, int] = {}
        voted_challenges = set()
        user_uuid = str(user.user_id) if user and user.user_id else None

        try:
            v_res = self.client.table("challenge_support").select("challenge_id, user_id").in_("challenge_id", challenge_ids).execute()
            for row in (v_res.data or []):
                cid = row.get("challenge_id")
                vote_counts[cid] = vote_counts.get(cid, 0) + 1
                if user_uuid and str(row.get("user_id")) == user_uuid:
                    voted_challenges.add(cid)
        except Exception:
            pass

        # Batch hydrate project summaries
        proj_map: Dict[str, Any] = {}
        try:
            p_res = self.client.table("projects").select("project_id, challenge_id, project_title, status, university_id, industry_id").in_("challenge_id", challenge_ids).execute()
            for p in (p_res.data or []):
                proj_map[p["challenge_id"]] = p
        except Exception:
            pass

        # Batch hydrate university rejections for government monitoring (Amendment 4)
        rejection_map: Dict[str, List[Dict[str, Any]]] = {}
        if user and getattr(user, "role", None) == "government":
            try:
                m_res = self.client.table("challenge_university_matches").select("*").in_("challenge_id", challenge_ids).eq("status", "rejected").execute()
                for m in (m_res.data or []):
                    cid = m.get("challenge_id")
                    u_res = self.client.table("universities").select("university_name").eq("university_id", m.get("university_id")).execute()
                    u_name = u_res.data[0].get("university_name") if (u_res and u_res.data) else m.get("university_id")
                    rejection_map.setdefault(cid, []).append({
                        "university_id": m.get("university_id"),
                        "university_name": u_name,
                        "rejection_reason": m.get("response_note") or "Problem statement declined by university administration.",
                        "rejected_at": m.get("responded_at"),
                    })
            except Exception:
                pass

        sanitized: List[Dict[str, Any]] = []
        for c in challenges:
            cid = c.get("challenge_id")
            raw_sub = c.get("submitted_by") or "Citizen"
            # Sanitize email or sensitive identifiers
            if "@" in str(raw_sub):
                display_sub = str(raw_sub).split("@")[0]
            else:
                display_sub = raw_sub

            item = {
                "challenge_id": cid,
                "title": c.get("title"),
                "description": c.get("description"),
                "location": c.get("location"),
                "city": c.get("city"),
                "district": c.get("district") or c.get("city"),
                "address": c.get("address"),
                "pincode": c.get("pincode"),
                "impact_scope": c.get("impact_scope"),
                "photo": c.get("photo"),
                "video": c.get("video"),
                "document": c.get("document"),
                "expected_solution": c.get("expected_solution"),
                "status": c.get("status"),
                "created_at": c.get("created_at"),
                "submitted_by": display_sub,
                "votes_count": vote_counts.get(cid, 0),
                "has_voted": cid in voted_challenges,
                "project": proj_map.get(cid),
                "university_rejections": rejection_map.get(cid, []),
            }
            # Only include user_id if specifically requested by user_id_filter query
            if user_id_filter:
                item["user_id"] = c.get("user_id")
            sanitized.append(item)

        return sanitized

    def list_my_challenges(self, user: AuthenticatedUser) -> List[Dict[str, Any]]:
        """Lists challenges submitted strictly by the authenticated user.

        Server-side ownership is verified against the authenticated user_id.
        """
        user_uuid = str(user.user_id)
        valid_uids = [user_uuid]
        try:
            uuid.UUID(user_uuid)
        except (ValueError, AttributeError):
            valid_uids.append(str(uuid.uuid5(uuid.NAMESPACE_DNS, user_uuid)))

        res = (
            self.client.table("challenges")
            .select("*")
            .in_("user_id", valid_uids)
            .order("created_at", desc=True, nullsfirst=False)
            .execute()
        )
        challenges = res.data or []
        if not challenges:
            return []

        challenge_ids = [c["challenge_id"] for c in challenges]

        # Batch hydrate ai_analysis
        ai_map: Dict[str, Any] = {}
        try:
            ai_res = self.client.table("ai_analysis").select("*").in_("challenge_id", challenge_ids).execute()
            for a in (ai_res.data or []):
                ai_map[a["challenge_id"]] = self._unpack_ai_analysis(a)
        except Exception:
            pass

        # Batch hydrate projects with authoritative milestone progression
        proj_map: Dict[str, Any] = {}
        try:
            p_res = (
                self.client.table("projects")
                .select("project_id, challenge_id, project_title, status, university_id, faculty_id, industry_id")
                .in_("challenge_id", challenge_ids)
                .execute()
            )
            proj_service = ProjectWorkflowService(client=self.client)
            for p in (p_res.data or []):
                pid = p.get("project_id")
                try:
                    _, curr_m = proj_service.get_project_current_stage(pid)
                    p["current_milestone"] = curr_m
                except Exception:
                    p["current_milestone"] = (
                        "Solution Deployed"
                        if p.get("status") in ["deployed", "solved", "completed"]
                        else "Faculty Assigned"
                    )

                # Hydrate institutional names
                if p.get("university_id"):
                    u = proj_service._get_record_silent("universities", "university_id", p["university_id"])
                    if u:
                        p["university_name"] = u.get("university_name")
                if p.get("faculty_id"):
                    f = proj_service._get_record_silent("faculty", "faculty_id", p["faculty_id"])
                    if f:
                        p["faculty_name"] = f.get("faculty_name")
                if p.get("industry_id"):
                    ind = proj_service._get_record_silent("industries", "industry_id", p["industry_id"])
                    if ind:
                        p["industry_name"] = ind.get("industry_name")

                proj_map[p["challenge_id"]] = p
        except Exception:
            pass

        # Batch hydrate vote counts
        vote_counts: Dict[str, int] = {}
        try:
            v_res = self.client.table("challenge_support").select("challenge_id").in_("challenge_id", challenge_ids).execute()
            for v in (v_res.data or []):
                cid = v.get("challenge_id")
                vote_counts[cid] = vote_counts.get(cid, 0) + 1
        except Exception:
            pass

        # Batch hydrate university rejections for submitter visibility (Part 10 & Clarification 3)
        rejection_map: Dict[str, List[Dict[str, Any]]] = {}
        try:
            m_res = self.client.table("challenge_university_matches").select("*").in_("challenge_id", challenge_ids).eq("status", "rejected").execute()
            for m in (m_res.data or []):
                cid = m.get("challenge_id")
                u_res = self.client.table("universities").select("university_name").eq("university_id", m.get("university_id")).execute()
                u_name = u_res.data[0].get("university_name") if (u_res and u_res.data) else m.get("university_id")
                rejection_map.setdefault(cid, []).append({
                    "university_id": m.get("university_id"),
                    "university_name": u_name,
                    "rejection_reason": m.get("response_note") or "Problem statement declined by university administration.",
                    "rejected_at": m.get("responded_at"),
                })
        except Exception:
            pass

        for c in challenges:
            cid = c["challenge_id"]
            proj = proj_map.get(cid)
            c["ai_analysis"] = ai_map.get(cid)
            c["project"] = proj
            c["votes_count"] = vote_counts.get(cid, 0)
            c["university_rejections"] = rejection_map.get(cid, [])
            if proj:
                c["current_milestone"] = proj.get("current_milestone")
                c["university_name"] = proj.get("university_name")
                c["faculty_name"] = proj.get("faculty_name")
                c["industry_name"] = proj.get("industry_name")
            else:
                c["current_milestone"] = (
                    "Routed to Universities"
                    if c.get("status") in ["routed", "university_selected"]
                    else "Problem Submitted"
                )

        return challenges

    def vote_challenge(self, challenge_id: str, user: AuthenticatedUser) -> Dict[str, Any]:
        """Records a citizen's vote for a challenge in challenge_support. Enforces 1 vote per user."""
        self.get_challenge(challenge_id)

        user_uuid = str(user.user_id)
        try:
            uuid.UUID(user_uuid)
        except (ValueError, AttributeError):
            user_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, user_uuid))

        # Check for existing vote
        existing = (
            self.client.table("challenge_support")
            .select("support_id")
            .eq("challenge_id", challenge_id)
            .eq("user_id", user_uuid)
            .execute()
        )
        if existing.data and len(existing.data) > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You have already voted for this problem.",
            )

        # Insert vote
        self.client.table("challenge_support").insert({
            "challenge_id": challenge_id,
            "user_id": user_uuid,
        }).execute()

        # Count total votes
        cnt_res = (
            self.client.table("challenge_support")
            .select("support_id", count="exact")
            .eq("challenge_id", challenge_id)
            .execute()
        )
        votes_count = cnt_res.count if cnt_res.count is not None else 1

        return {
            "challenge_id": challenge_id,
            "votes_count": votes_count,
            "has_voted": True,
        }

    def get_challenge_milestones(self, challenge_id: str) -> List[Dict[str, Any]]:
        """Retrieves read-only milestone progress for the project linked to a challenge."""
        try:
            p_res = (
                self.client.table("projects")
                .select("project_id, project_title, status")
                .eq("challenge_id", challenge_id)
                .execute()
            )
            if not p_res.data:
                return []
            project_id = p_res.data[0]["project_id"]

            m_res = (
                self.client.table("project_milestones")
                .select("milestone_id, milestone_name, description, deadline, status, completion_percentage, created_at")
                .eq("project_id", project_id)
                .order("deadline", desc=False)
                .execute()
            )
            milestones = []
            for m in (m_res.data or []):
                milestones.append({
                    "milestone_id": m.get("milestone_id"),
                    "name": m.get("milestone_name") or "Milestone",
                    "description": m.get("description"),
                    "deadline": m.get("deadline"),
                    "status": m.get("status") or "pending",
                    "completion_percentage": m.get("completion_percentage", 0),
                    "created_at": m.get("created_at"),
                })
            return milestones
        except Exception:
            return []

    # -------------------------------------------------------------------------
    # -------------------------------------------------------------------------
    # Targeted Candidate Retrieval (VidySetu Solutions + Challenges)
    # -------------------------------------------------------------------------
    def retrieve_targeted_candidates(
        self, challenge: Dict[str, Any], limit: int = 15
    ) -> List[Dict[str, Any]]:
        """Retrieves bounded set of completed VidySetu projects and relevant challenges for Call 1 relationship analysis.

        Prioritizes:
        1. Completed/deployed VidySetu projects (joined with solved challenges, universities, industries, and milestone evidence).
        2. Relevant challenges in the same district/city or same category.
        3. Active and resolved challenges scored deterministically via multi-signal similarity.
        """
        curr_cid = challenge.get("challenge_id")
        curr_title = (challenge.get("title") or "").strip()
        curr_desc = (challenge.get("description") or "").strip()
        curr_dist = (challenge.get("district") or challenge.get("city") or "").strip()
        curr_cat = (challenge.get("category") or "").strip()

        candidates: List[Dict[str, Any]] = []
        seen_cids: Set[str] = set()
        if curr_cid:
            seen_cids.add(curr_cid)

        # 1. Retrieve completed or deployed VidySetu projects
        try:
            p_res = (
                self.client.table("projects")
                .select("project_id, challenge_id, project_title, description, status, university_id, industry_id, faculty_id")
                .in_("status", ["completed", "deployed"])
                .limit(50)
                .execute()
            )
            raw_projects = p_res.data or []
            if raw_projects:
                proj_cids = [p["challenge_id"] for p in raw_projects if p.get("challenge_id")]
                u_ids = list({p["university_id"] for p in raw_projects if p.get("university_id")})
                i_ids = list({p["industry_id"] for p in raw_projects if p.get("industry_id")})
                p_ids = [p["project_id"] for p in raw_projects if p.get("project_id")]

                # Batch hydrate challenge info including location and category
                ch_map: Dict[str, Any] = {}
                if proj_cids:
                    try:
                        c_res = (
                            self.client.table("challenges")
                            .select("challenge_id, title, description, status, city, district, location")
                            .in_("challenge_id", proj_cids)
                            .execute()
                        )
                        ch_map = {c["challenge_id"]: c for c in (c_res.data or [])}
                    except Exception:
                        pass

                # Batch hydrate universities
                u_map: Dict[str, str] = {}
                if u_ids:
                    try:
                        u_res = (
                            self.client.table("universities")
                            .select("university_id, university_name")
                            .in_("university_id", u_ids)
                            .execute()
                        )
                        u_map = {row["university_id"]: row.get("university_name") for row in (u_res.data or [])}
                    except Exception:
                        pass

                # Batch hydrate industries
                i_map: Dict[str, str] = {}
                if i_ids:
                    try:
                        i_res = (
                            self.client.table("industries")
                            .select("industry_id, industry_name")
                            .in_("industry_id", i_ids)
                            .execute()
                        )
                        i_map = {row["industry_id"]: row.get("industry_name") for row in (i_res.data or [])}
                    except Exception:
                        pass

                # Batch hydrate milestone evidence and milestones
                ev_map: Dict[str, str] = {}
                p_milestones_map: Dict[str, List[Dict[str, Any]]] = {}
                if p_ids:
                    try:
                        m_res = (
                            self.client.table("project_milestones")
                            .select("project_id, milestone_name, status, completion_percentage, evidence_url")
                            .in_("project_id", p_ids)
                            .order("deadline", desc=False)
                            .execute()
                        )
                        for m in (m_res.data or []):
                            pid_m = m.get("project_id")
                            if pid_m:
                                if pid_m not in p_milestones_map:
                                    p_milestones_map[pid_m] = []
                                p_milestones_map[pid_m].append({
                                    "name": m.get("milestone_name") or "Milestone",
                                    "status": m.get("status") or "completed",
                                    "completion_percentage": m.get("completion_percentage", 100),
                                    "evidence_url": m.get("evidence_url"),
                                })
                                if m.get("evidence_url") and pid_m not in ev_map:
                                    ev_map[pid_m] = m.get("evidence_url")
                    except Exception:
                        pass

                for p in raw_projects:
                    c_info = ch_map.get(p.get("challenge_id")) or {}
                    p_title = p.get("project_title") or c_info.get("title") or "Applied Solution"
                    p_desc = p.get("description") or c_info.get("description") or ""

                    cand = {
                        "challenge_id": p.get("challenge_id") or f"CHL-PRJ-{p['project_id']}",
                        "project_id": p.get("project_id"),
                        "title": p_title,
                        "description": p_desc,
                        "source": "vidysetu_project",
                        "status": p.get("status") or "completed",
                        "university_name": u_map.get(p.get("university_id")),
                        "industry_name": i_map.get(p.get("industry_id")),
                        "evidence_url": ev_map.get(p.get("project_id")),
                        "city": c_info.get("city"),
                        "district": c_info.get("district"),
                        "location": c_info.get("location"),
                        "category": c_info.get("category"),
                        "solved_problem_title": c_info.get("title") or p_title,
                        "milestones": p_milestones_map.get(p.get("project_id"), []),
                    }
                    multi_sig = compute_multi_signal_similarity(challenge, cand)
                    cand["similarity_score"] = multi_sig["composite_score"]
                    cand["multi_signal"] = multi_sig
                    candidates.append(cand)

                    # Mark challenge_id as covered by project
                    if p.get("challenge_id"):
                        seen_cids.add(p["challenge_id"])
        except Exception as e:
            logger.warning(f"Error querying completed projects for candidate retrieval: {e}")

        # 2. Retrieve existing challenges with multi-factor targeting (location, category, general pool)
        ch_raw_candidates: List[Dict[str, Any]] = []

        # A. Same District / City match
        if curr_dist:
            try:
                q_loc = self.client.table("challenges").select("challenge_id, title, description, status, location, city, district")
                if curr_cid:
                    q_loc = q_loc.neq("challenge_id", curr_cid)
                q_loc = q_loc.ilike("district", f"%{curr_dist}%").limit(50)
                loc_res = q_loc.execute()
                for c in (loc_res.data or []):
                    if c["challenge_id"] not in seen_cids:
                        seen_cids.add(c["challenge_id"])
                        ch_raw_candidates.append(c)
            except Exception as e:
                logger.warning(f"Error fetching district candidates: {e}")

        # B. Same Category match from ai_analysis
        if curr_cat:
            try:
                ai_cat_res = self.client.table("ai_analysis").select("challenge_id").ilike("category", f"%{curr_cat}%").limit(50).execute()
                cat_cids = [r["challenge_id"] for r in (ai_cat_res.data or []) if r.get("challenge_id") and r["challenge_id"] not in seen_cids]
                if cat_cids:
                    q_cat = self.client.table("challenges").select("challenge_id, title, description, status, location, city, district").in_("challenge_id", cat_cids)
                    if curr_cid:
                        q_cat = q_cat.neq("challenge_id", curr_cid)
                    cat_res = q_cat.execute()
                    for c in (cat_res.data or []):
                        if c["challenge_id"] not in seen_cids:
                            seen_cids.add(c["challenge_id"])
                            ch_raw_candidates.append(c)
            except Exception as e:
                logger.warning(f"Error fetching category candidates: {e}")

        # C. General recent challenge pool
        try:
            q_all = self.client.table("challenges").select("challenge_id, title, description, status, location, city, district")
            if curr_cid:
                q_all = q_all.neq("challenge_id", curr_cid)
            all_res = q_all.order("created_at", desc=True).limit(100).execute()
            for c in (all_res.data or []):
                if c["challenge_id"] not in seen_cids:
                    seen_cids.add(c["challenge_id"])
                    ch_raw_candidates.append(c)
        except Exception as e:
            logger.warning(f"Error fetching general challenge pool: {e}")

        # Batch hydrate category from ai_analysis
        cat_lookup: Dict[str, str] = {}
        if ch_raw_candidates:
            all_raw_cids = [c["challenge_id"] for c in ch_raw_candidates]
            try:
                ai_cat_batch = self.client.table("ai_analysis").select("challenge_id, category").in_("challenge_id", all_raw_cids).execute()
                cat_lookup = {r["challenge_id"]: r.get("category") for r in (ai_cat_batch.data or [])}
            except Exception:
                pass

        # Score all retrieved challenges using multi-signal similarity
        for c in ch_raw_candidates:
            cand = {
                "challenge_id": c["challenge_id"],
                "project_id": None,
                "title": c.get("title") or "",
                "description": c.get("description") or "",
                "source": "vidysetu_challenge",
                "status": c.get("status"),
                "city": c.get("city"),
                "district": c.get("district"),
                "location": c.get("location") or c.get("city"),
                "category": cat_lookup.get(c["challenge_id"]),
            }
            multi_sig = compute_multi_signal_similarity(challenge, cand)
            cand["similarity_score"] = multi_sig["composite_score"]
            cand["multi_signal"] = multi_sig
            candidates.append(cand)

        # 3. Sort candidates by multi-signal similarity_score descending and return Top limit
        candidates.sort(key=lambda x: x.get("similarity_score", 0.0), reverse=True)
        return candidates[:limit]

    # -------------------------------------------------------------------------
    # 2. AI Review & Existing-Solution Discovery (Call 1)
    # -------------------------------------------------------------------------
    def analyze_challenge(
        self, challenge_id: str, user: AuthenticatedUser
    ) -> Dict[str, Any]:
        """Executes Call 1: Evaluates problem, checks image, checks existing solutions, and persists to ai_analysis.

        Strictly enforces maximum 2 AI calls per challenge and blocks any third call.
        """
        challenge = self.get_challenge(challenge_id)
        self._verify_ownership(challenge, user)

        current_status = challenge.get("status", "submitted")
        existing_analysis = challenge.get("ai_analysis")

        # Hard limit enforcement: Block any 3rd call
        if existing_analysis and current_status in [
            "validated", "accepted_existing_solution", "rejected", "gap_invalid", "gap_uncertain"
        ]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum 2 AI analysis calls per challenge exceeded. Third call blocked.",
            )

        # Idempotency check: If already awaiting citizen response after Call 1, return existing analysis
        if existing_analysis and current_status in ["existing_solution_found", "image_mismatch"]:
            return {
                "challenge_id": challenge_id,
                "status": current_status,
                "action_taken": "awaiting_citizen_response",
                "llm_calls_made": 1,
                "solution_found": existing_analysis.get("solution_found", False),
                "existing_solution": existing_analysis.get("existing_solution"),
                "solution_gap_valid": existing_analysis.get("solution_gap_valid"),
                "analysis": existing_analysis,
                "search_grounding_used": False,
                "image_evidence_status": existing_analysis.get("validity"),
                "message": "Challenge has already completed Call 1 analysis.",
            }

        # Targeted Candidate Retrieval (Part 1 & 2): Solved projects + relevant challenges
        existing_candidates = self.retrieve_targeted_candidates(challenge, limit=10)

        # Run Call 1 via AIService
        call_1_result = self.ai_service.analyze_call_1(challenge, existing_challenges=existing_candidates)

        # Map to the exact 20 columns of public.ai_analysis
        analysis_data = {
            "challenge_id": challenge_id,
            "category": call_1_result.get("category"),
            "subcategory": call_1_result.get("subcategory"),
            "ai_summary": call_1_result.get("ai_summary"),
            "required_skills": call_1_result.get("required_skills"),
            "required_technologies": call_1_result.get("required_technologies"),
            "severity": call_1_result.get("severity"),
            "priority": call_1_result.get("priority"),
            "duplicate_group": call_1_result.get("duplicate_group"),
            "similar_challenges": call_1_result.get("similar_challenges"),
            "solution_found": call_1_result.get("solution_found", False),
            "existing_solution": call_1_result.get("existing_solution"),
            "confidence_score": call_1_result.get("confidence_score"),
            "validity": call_1_result.get("validity", "valid"),
            "innovation_scope": call_1_result.get("innovation_scope", "medium"),
            "feasibility": call_1_result.get("feasibility", "high"),
            "solution_gap": call_1_result.get("solution_gap"),
            "solution_gap_valid": call_1_result.get("solution_gap_valid"),
        }

        clean_analysis = {k: v for k, v in analysis_data.items() if v is not None}

        try:
            persisted = (
                self.client.table("ai_analysis")
                .upsert(clean_analysis, on_conflict="challenge_id")
                .execute()
            )
            saved_analysis = persisted.data[0] if persisted.data else analysis_data
        except Exception as e:
            logger.error(f"Failed to persist ai_analysis for challenge {challenge_id}: {e}", exc_info=True)
            raise

        # Determine status transitions adhering strictly to User Clarifications & Phase LLM-1 rules:
        # Ineligible / Innovation Scope None / University Not Suitable -> rejected
        # Uncertain -> uncertain_eligibility (Never sent to Government)
        # Image mismatch -> image_mismatch (Never sent to Government)
        # Existing solution found -> existing_solution_found
        # Search failed -> uncertain_solution_search (Never sent to Government)
        # Search succeeded with no solution found -> validated
        validity = call_1_result.get("validity", "valid")
        raw_innovation = call_1_result.get("innovation_scope_raw") or call_1_result.get("innovation_scope")
        uni_suitable = call_1_result.get("university_suitable")
        solution_found = call_1_result.get("solution_found", False)
        existing_solution_found = call_1_result.get("existing_solution_found")
        search_status = call_1_result.get("external_search_status", "not_searched")
        img_status = call_1_result.get("image_evidence_status")
        duplicate_group = call_1_result.get("duplicate_group")

        has_existing_sol = (
            solution_found
            or existing_solution_found is True
            or bool(call_1_result.get("internal_solutions"))
        )

        if validity in ("ineligible", "invalid") or raw_innovation == "none" or uni_suitable is False:
            new_status = "rejected"
            action_msg = "Problem flagged as routine municipal maintenance, ineligible, or non-innovation."
        elif has_existing_sol:
            new_status = "existing_solution_found"
            action_msg = "Existing verified solution discovered. Awaiting citizen confirmation."
        elif duplicate_group:
            new_status = "duplicate_detected"
            action_msg = "A strongly similar challenge already exists in your area. Awaiting citizen confirmation via Duplicate Gate."
        elif validity == "uncertain":
            new_status = "uncertain_eligibility"
            action_msg = "Problem statement requires further clarification."
        elif img_status == "mismatch":
            new_status = "image_mismatch"
            action_msg = "Uploaded image does not appear to match the problem description. Please upload clearer evidence."
        elif search_status == "search_failed":
            new_status = "uncertain_solution_search"
            action_msg = "External solution search failed or offline. Challenge pending verification."
        elif search_status == "searched" and existing_solution_found is False:
            new_status = "validated"
            action_msg = "No existing solution found via search grounding. Challenge classified and validated for matching."
        else:
            new_status = "validated"
            action_msg = "Challenge classified and validated."

        try:
            self.client.table("challenges").update({"status": new_status}).eq("challenge_id", challenge_id).execute()
        except Exception as e:
            logger.error(f"Failed to update status for challenge {challenge_id} to '{new_status}': {e}", exc_info=True)
            raise

        unpacked_analysis = self._unpack_ai_analysis(dict(saved_analysis))

        return {
            "challenge_id": challenge_id,
            "status": new_status,
            "action_taken": "call_1_completed",
            "llm_calls_made": 1,
            "solution_found": bool(existing_solution_found) if existing_solution_found is not None else solution_found,
            "existing_solution_found": existing_solution_found,
            "existing_solution": call_1_result.get("existing_solution"),
            "solution_gap_valid": call_1_result.get("solution_gap_valid"),
            "analysis": unpacked_analysis,
            "provider_used": call_1_result.get("provider_used", "backend"),
            "provider_failure_reason": call_1_result.get("provider_failure_reason"),
            "search_grounding_used": call_1_result.get("search_grounding_used", False),
            "external_search_status": search_status,
            "image_evidence_status": img_status,
            "image_observations": call_1_result.get("image_observations", []),
            "solutions": call_1_result.get("solutions", []),
            "duplicate_group": call_1_result.get("duplicate_group"),
            "duplicate_candidates": [
                cand.model_dump() if hasattr(cand, "model_dump") else cand
                for cand in call_1_result.get("duplicate_candidates", [])
            ],
            "candidate_relationships": call_1_result.get("candidate_relationships", []),
            "similar_challenges_list": unpacked_analysis.get("similar_challenges_list", []),
            "internal_search_status": call_1_result.get("internal_search_status", "searched"),
            "internal_solutions": call_1_result.get("internal_solutions", []),
            "objective_evidence": {
                "secondary_categories": call_1_result.get("secondary_categories", []),
                "severity_level": call_1_result.get("severity_level"),
                "population_scale": call_1_result.get("population_scale"),
                "life_safety_threat": call_1_result.get("life_safety_threat"),
                "essential_service_disrupted": call_1_result.get("essential_service_disrupted"),
                "priority_evidence": call_1_result.get("priority_evidence"),
                "university_suitable": call_1_result.get("university_suitable"),
                "university_suitability_reason": call_1_result.get("university_suitability_reason"),
            },
            "message": action_msg,
        }

    # -------------------------------------------------------------------------
    # 3. Existing-Solution Response & Gap Validation (Call 2)
    # -------------------------------------------------------------------------
    def handle_existing_solution_response(
        self,
        challenge_id: str,
        user: AuthenticatedUser,
        accepted: bool,
        rejection_reason: Optional[str] = None,
        rejection_category: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Handles citizen acceptance or rejection of an existing solution.

        - If accepted: marks challenge accepted_existing_solution. Closes workflow. (0 extra calls)
        - If rejected: triggers Call 2 for gap validation and full classification. (1 extra call)
        - Enforces strict 2-call maximum budget.
        """
        challenge = self.get_challenge(challenge_id)
        self._verify_ownership(challenge, user)

        current_status = challenge.get("status")
        existing_analysis = challenge.get("ai_analysis")

        # Hard limit enforcement: Block any 3rd call
        if current_status in ["accepted_existing_solution", "gap_invalid", "gap_uncertain"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum 2 AI analysis calls per challenge exceeded. Third call blocked.",
            )

        # Validate that challenge is awaiting citizen decision
        if current_status != "existing_solution_found" or not existing_analysis:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Challenge '{challenge_id}' is in status '{current_status}'. "
                    f"It is not awaiting an existing solution response."
                ),
            )

        # ---------------------------------------------------------
        # Case A: Citizen Accepts Existing Solution
        # ---------------------------------------------------------
        if accepted:
            new_status = "accepted_existing_solution"
            note = "Citizen confirmed existing solution resolves the challenge."

            try:
                self.client.table("challenges").update({"status": new_status}).eq("challenge_id", challenge_id).execute()
                self.client.table("ai_analysis").update({
                    "solution_gap": note,
                    "solution_gap_valid": False,
                }).eq("challenge_id", challenge_id).execute()
            except Exception:
                pass

            return {
                "challenge_id": challenge_id,
                "status": new_status,
                "action_taken": "solution_accepted",
                "llm_calls_made": 1,
                "solution_found": True,
                "existing_solution": existing_analysis.get("existing_solution"),
                "solution_gap_valid": False,
                "analysis": existing_analysis,
                "message": "Existing solution accepted. Challenge resolved successfully without new project creation.",
            }

        # ---------------------------------------------------------
        # Case B: Citizen Rejects Existing Solution -> Trigger Call 2
        # ---------------------------------------------------------
        if not rejection_reason or not rejection_reason.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="A non-empty rejection_reason explaining why the existing solution does not work locally is required.",
            )

        existing_sol_text = existing_analysis.get("existing_solution") or "Discovered Public Solution"

        # Execute Call 2 (Gap Validation + Refined Classification)
        call_2_result = self.ai_service.analyze_call_2_gap_validation(
            challenge=challenge,
            existing_solution=existing_sol_text,
            rejection_reason=rejection_reason.strip(),
            rejection_category=rejection_category,
        )

        gap_status = call_2_result.get("gap_status", "VALID_GAP")
        is_gap_valid = call_2_result.get("solution_gap_valid", False)

        if gap_status == "VALID_GAP":
            new_status = "validated"
            msg = "Gap validation complete. Problem validated and routed for Government approval."
        elif gap_status == "UNCERTAIN_GAP":
            new_status = "gap_uncertain"
            msg = "Gap validation uncertain. Additional clarification required."
        else:
            new_status = "gap_invalid"
            msg = "The provided difference does not establish a sufficient unmet need for a new project."

        update_data = {
            "solution_gap": call_2_result.get("solution_gap"),
            "solution_gap_valid": is_gap_valid,
            "ai_summary": call_2_result.get("ai_summary"),
            "category": call_2_result.get("category"),
            "subcategory": call_2_result.get("subcategory"),
            "required_skills": call_2_result.get("required_skills"),
            "required_technologies": call_2_result.get("required_technologies"),
            "severity": call_2_result.get("severity"),
            "priority": call_2_result.get("priority"),
            "innovation_scope": call_2_result.get("innovation_scope"),
            "feasibility": call_2_result.get("feasibility"),
            "confidence_score": call_2_result.get("confidence_score"),
        }

        try:
            self.client.table("ai_analysis").update(update_data).eq("challenge_id", challenge_id).execute()
            self.client.table("challenges").update({"status": new_status}).eq("challenge_id", challenge_id).execute()
        except Exception:
            pass

        return {
            "challenge_id": challenge_id,
            "status": new_status,
            "action_taken": "call_2_gap_validated",
            "llm_calls_made": 2,
            "solution_found": True,
            "existing_solution": existing_sol_text,
            "solution_gap_valid": is_gap_valid,
            "gap_status": gap_status,
            "analysis": {**existing_analysis, **update_data},
            "message": msg,
        }

    # -------------------------------------------------------------------------
    # 4. Duplicate Gate Response & Gap Validation
    # -------------------------------------------------------------------------
    def handle_duplicate_response(
        self,
        challenge_id: str,
        user: AuthenticatedUser,
        action: str,
        existing_challenge_id: Optional[str] = None,
        gap_reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Handles citizen response to the Citizen Duplicate Gate.

        Actions:
        - 'support_existing': citizen acknowledges existing problem/solution, upvotes existing challenge,
          and merges current challenge (new_status = 'duplicate_merged').
        - 'claim_different': citizen claims their problem has a distinct gap. Triggers Call 2 gap validation.
          If valid gap -> new_status = 'validated'.
          If invalid gap -> new_status = 'duplicate_confirmed'.
          If uncertain -> new_status = 'gap_uncertain'.
        """
        challenge = self.get_challenge(challenge_id)
        self._verify_ownership(challenge, user)

        current_status = challenge.get("status")
        existing_analysis = challenge.get("ai_analysis") or {}

        if current_status not in ["duplicate_detected", "submitted", "uncertain_eligibility", "existing_solution_found"]:
            if current_status in ["duplicate_merged", "duplicate_confirmed", "validated"]:
                return {
                    "challenge_id": challenge_id,
                    "status": current_status,
                    "action_taken": f"already_{current_status}",
                    "message": f"Challenge is already in status '{current_status}'.",
                }

        target_cid = existing_challenge_id or existing_analysis.get("duplicate_group")

        if action == "support_existing":
            # 1. Citizen supports / upvotes the existing challenge
            if target_cid:
                try:
                    self.vote_challenge(target_cid, user)
                except Exception as e:
                    logger.info(f"Vote for existing challenge {target_cid} note: {e}")

            new_status = "duplicate_merged"
            note = f"Citizen supported existing challenge {target_cid or 'candidate'}. Submission merged."

            try:
                self.client.table("challenges").update({"status": new_status}).eq("challenge_id", challenge_id).execute()
                self.client.table("ai_analysis").update({
                    "solution_gap": note,
                    "solution_gap_valid": False,
                }).eq("challenge_id", challenge_id).execute()
            except Exception as e:
                logger.error(f"Failed to update challenge {challenge_id} to duplicate_merged: {e}")

            return {
                "challenge_id": challenge_id,
                "status": new_status,
                "action_taken": "duplicate_merged",
                "target_challenge_id": target_cid,
                "message": "Thank you for supporting the existing challenge! Your endorsement has been counted.",
            }

        elif action == "claim_different":
            if not gap_reason or not gap_reason.strip():
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Please explain how your problem is different or what gap exists in the existing problem.",
                )

            # Retrieve existing challenge details to frame the gap check
            ref_text = "Existing Civic Problem Statement"
            if target_cid:
                try:
                    target_ch = self.get_challenge(target_cid)
                    ref_text = f"{target_ch.get('title', '')}: {target_ch.get('description', '')}".strip()
                except Exception:
                    pass

            # Run Call 2 gap validation
            call_2_result = self.ai_service.analyze_call_2_gap_validation(
                challenge=challenge,
                existing_solution=ref_text,
                rejection_reason=gap_reason.strip(),
            )

            gap_status = call_2_result.get("gap_status", "VALID_GAP")
            is_gap_valid = call_2_result.get("solution_gap_valid", False)

            if gap_status == "VALID_GAP":
                new_status = "validated"
                msg = "Gap validated. Your distinct problem has been approved for university and industry matching!"
            elif gap_status == "UNCERTAIN_GAP":
                new_status = "gap_uncertain"
                msg = "The difference provided requires further clarification."
            else:
                new_status = "duplicate_confirmed"
                msg = "Review concluded that this issue is already covered by the existing challenge."

            update_data = {
                "solution_gap": call_2_result.get("solution_gap") or gap_reason.strip(),
                "solution_gap_valid": is_gap_valid,
                "ai_summary": call_2_result.get("ai_summary"),
                "category": call_2_result.get("category"),
                "subcategory": call_2_result.get("subcategory"),
                "required_skills": call_2_result.get("required_skills"),
                "required_technologies": call_2_result.get("required_technologies"),
                "severity": call_2_result.get("severity"),
                "priority": call_2_result.get("priority"),
                "innovation_scope": call_2_result.get("innovation_scope"),
                "feasibility": call_2_result.get("feasibility"),
                "confidence_score": call_2_result.get("confidence_score"),
            }

            try:
                self.client.table("ai_analysis").update(update_data).eq("challenge_id", challenge_id).execute()
                self.client.table("challenges").update({"status": new_status}).eq("challenge_id", challenge_id).execute()
            except Exception:
                pass

            return {
                "challenge_id": challenge_id,
                "status": new_status,
                "action_taken": "duplicate_gap_evaluated",
                "gap_status": gap_status,
                "solution_gap_valid": is_gap_valid,
                "analysis": {**existing_analysis, **update_data},
                "message": msg,
            }

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown duplicate response action '{action}'. Must be 'support_existing' or 'claim_different'.",
            )

    # -------------------------------------------------------------------------
    # Helper: Ownership Verification
    # -------------------------------------------------------------------------
    def _verify_ownership(self, challenge: Dict[str, Any], user: AuthenticatedUser):
        """Verifies that the user owns the challenge or is a privileged administrator/authority."""
        challenge_owner_id = str(challenge.get("user_id", ""))
        user_id = str(user.user_id)

        # Allow if user is challenge creator (direct match or deterministic uuid)
        if challenge_owner_id and (
            challenge_owner_id == user_id
            or challenge_owner_id == str(uuid.uuid5(uuid.NAMESPACE_DNS, user_id))
        ):
            return

        # Allow privileged roles
        if user.role in ["government", "university_admin"]:
            return

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: You do not have permission to modify or analyze this challenge.",
        )

