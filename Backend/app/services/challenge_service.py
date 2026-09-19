"""challenge_service.py

Handles citizen challenge submission, status lifecycle, ownership enforcement,
and coordinates with AIService to persist review results into the Supabase
challenges and ai_analysis tables.
"""

import uuid
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status

from app.database import get_supabase
from app.services.ai_service import AIService
from app.services.auth_service import AuthenticatedUser


class ChallengeService:
    """Service managing challenge submissions, state transitions, and AI review workflows."""

    def __init__(self, ai_service: Optional[AIService] = None, client=None):
        self.ai_service = ai_service or AIService()
        self._client = client

    @property
    def client(self):
        return self._client if self._client is not None else get_supabase()


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

    def get_challenge(self, challenge_id: str) -> Dict[str, Any]:
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
            challenge["ai_analysis"] = analysis_res.data[0] if analysis_res.data else None
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

        # Hydrate university rejections (Part 10 & Clarification 3)
        rejections = []
        try:
            m_res = self.client.table("challenge_university_matches").select("*").eq("challenge_id", challenge_id).eq("status", "rejected").execute()
            for m in (m_res.data or []):
                u_res = self.client.table("universities").select("university_name").eq("university_id", m.get("university_id")).execute()
                u_name = u_res.data[0].get("university_name") if (u_res and u_res.data) else m.get("university_id")
                rejections.append({
                    "university_id": m.get("university_id"),
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
                ai_map[a["challenge_id"]] = a
        except Exception:
            pass

        # Batch hydrate projects
        proj_map: Dict[str, Any] = {}
        try:
            p_res = (
                self.client.table("projects")
                .select("project_id, challenge_id, project_title, status, university_id, industry_id")
                .in_("challenge_id", challenge_ids)
                .execute()
            )
            for p in (p_res.data or []):
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
            c["ai_analysis"] = ai_map.get(cid)
            c["project"] = proj_map.get(cid)
            c["votes_count"] = vote_counts.get(cid, 0)
            c["university_rejections"] = rejection_map.get(cid, [])

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

        # Fetch candidate challenges for duplicate detection
        existing_candidates = []
        try:
            cand_res = self.client.table("challenges").select("challenge_id,title,description").neq("challenge_id", challenge_id).limit(15).execute()
            existing_candidates = cand_res.data or []
        except Exception:
            existing_candidates = []

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
        except Exception:
            saved_analysis = analysis_data

        # Determine status transitions adhering strictly to User Clarifications:
        # Clarification #3:
        # Ineligible -> rejected
        # Uncertain -> clarification
        # Eligible + no solution -> validated
        # Image mismatch -> image_mismatch (prompt better evidence, do NOT permanently reject)
        # Solution found -> existing_solution_found
        validity = call_1_result.get("validity", "valid")
        solution_found = call_1_result.get("solution_found", False)
        img_status = call_1_result.get("image_evidence_status")

        if validity == "invalid":
            new_status = "rejected"
            action_msg = "Problem flagged as ineligible or safety concern."
        elif validity == "uncertain":
            new_status = "uncertain_eligibility"
            action_msg = "Problem statement requires further clarification."
        elif img_status == "mismatch":
            new_status = "image_mismatch"
            action_msg = "Uploaded image does not appear to match the problem description. Please upload clearer evidence."
        elif solution_found:
            new_status = "existing_solution_found"
            action_msg = "Existing verified solution discovered. Awaiting citizen confirmation."
        else:
            new_status = "validated"
            action_msg = "No existing solution found. Challenge classified and validated for matching."

        try:
            self.client.table("challenges").update({"status": new_status}).eq("challenge_id", challenge_id).execute()
        except Exception:
            pass

        return {
            "challenge_id": challenge_id,
            "status": new_status,
            "action_taken": "call_1_completed",
            "llm_calls_made": 1,
            "solution_found": solution_found,
            "existing_solution": call_1_result.get("existing_solution"),
            "solution_gap_valid": call_1_result.get("solution_gap_valid"),
            "analysis": saved_analysis,
            "search_grounding_used": call_1_result.get("search_grounding_used", False),
            "image_evidence_status": img_status,
            "solutions": call_1_result.get("solutions", []),
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
            msg = "Gap validation complete. Problem validated and classified for university/industry matching."
        elif gap_status == "UNCERTAIN_GAP":
            new_status = "gap_uncertain"
            msg = "Gap validation uncertain. Additional clarification required."
        else:
            new_status = "gap_invalid"
            msg = "Gap validation concluded that the existing solution is sufficient; reason provided was not valid."

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

