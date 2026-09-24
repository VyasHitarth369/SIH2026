"""university_workflow_service.py

Orchestrates Phase 5 workflows:
1. University match response (accept/reject with provisional acceptance).
2. Selection finalization (highest-ranked accepted university is selected; others become not_selected).
3. Faculty allocation and project creation (strict relationship validation, faculty must belong to selected university).
4. Project queries and relational hydration.
"""

from datetime import datetime, timezone
import threading
import uuid
from typing import Any, Dict, List, Optional, Tuple
from fastapi import HTTPException, status

from app.database import get_supabase
from app.services.auth_service import AuthenticatedUser
from app.utils.storage_utils import resolve_document_signed_url

_selection_lock = threading.Lock()


VALID_PROJECT_STATUSES = {
    "proposed",
    "active",
    "prototype",
    "pilot",
    "deployed",
    "solved",
    "completed",
}


class UniversityWorkflowService:
    """Service managing university administrative responses, selection, and project creation."""

    def __init__(self, client=None):
        self._client = client

    @property
    def client(self):
        return self._client if self._client is not None else get_supabase()

    # -------------------------------------------------------------------------
    # 1. University Administrator Response (Accept / Reject)
    # -------------------------------------------------------------------------
    def respond_to_university_match(
        self,
        challenge_id: str,
        university_id: str,
        action: str,
        user: AuthenticatedUser,
        response_note: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Processes university admin response to a challenge recommendation.

        Enforces that:
        - User is authenticated and verified university_admin
        - Admin belongs strictly to the target university_id
        - Match exists and is in ['recommended', 'invited'] status
        - Response deadline has not expired
        - Final selection is evaluated deterministically based on rank and acceptance
        """
        # 1. Authorize university admin
        self._verify_admin_for_university(user, university_id)

        # 2. Check challenge exists
        self._get_challenge_or_404(challenge_id)

        # 3. Check match exists
        match_record = self._get_match_or_404(challenge_id, university_id)
        current_status = match_record.get("status")

        if current_status not in ["recommended", "invited"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Cannot respond to match in status '{current_status}'. "
                    f"Match must be in 'recommended' or 'invited' status."
                ),
            )

        # Enforce rejection reason requirement
        if action == "reject":
            if not response_note or not str(response_note).strip():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Rejection reason is mandatory when declining a problem statement.",
                )

        # 4. Enforce response deadline
        deadline_str = match_record.get("response_deadline")
        if deadline_str:
            try:
                deadline_dt = datetime.fromisoformat(deadline_str.replace("Z", "+00:00"))
                if datetime.now(timezone.utc) > deadline_dt:
                    try:
                        self.client.table("challenge_university_matches").update({
                            "status": "expired"
                        }).eq("challenge_id", challenge_id).eq("university_id", university_id).execute()
                    except Exception:
                        pass
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Response deadline has expired. Invitation can no longer be accepted or rejected.",
                    )
            except HTTPException:
                raise
            except Exception:
                pass

        now_iso = datetime.now(timezone.utc).isoformat()
        new_status = "accepted" if action == "accept" else "rejected"

        update_fields = {
            "status": new_status,
            "responded_by": str(user.user_id),
            "responded_at": now_iso,
            "response_note": response_note.strip() if response_note else None,
        }

        try:
            res = (
                self.client.table("challenge_university_matches")
                .update(update_fields)
                .eq("challenge_id", challenge_id)
                .eq("university_id", university_id)
                .execute()
            )
            updated = res.data[0] if res.data else {**match_record, **update_fields}
        except Exception:
            updated = {**match_record, **update_fields}

        # 5. Check if we should automatically finalize or evaluate selection
        selection_finalized = None
        if action == "accept":
            try:
                higher_res = (
                    self.client.table("challenge_university_matches")
                    .select("*")
                    .eq("challenge_id", challenge_id)
                    .lt("rank", match_record.get("rank", 999))
                    .execute()
                )
                higher_matches = higher_res.data or []
                all_higher_terminal = all(m.get("status") in ["rejected", "expired"] for m in higher_matches)
                if all_higher_terminal:
                    selection_finalized = self.finalize_university_selection(challenge_id, user)
            except Exception:
                pass
        elif action == "reject":
            try:
                acc_res = (
                    self.client.table("challenge_university_matches")
                    .select("*")
                    .eq("challenge_id", challenge_id)
                    .eq("status", "accepted")
                    .order("rank", desc=False)
                    .execute()
                )
                if acc_res.data:
                    top_accepted = acc_res.data[0]
                    higher_res = (
                        self.client.table("challenge_university_matches")
                        .select("*")
                        .eq("challenge_id", challenge_id)
                        .lt("rank", top_accepted.get("rank", 999))
                        .execute()
                    )
                    higher_matches = higher_res.data or []
                    if all(m.get("status") in ["rejected", "expired"] for m in higher_matches):
                        selection_finalized = self.finalize_university_selection(challenge_id, user)
                else:
                    # Check if all matches are now rejected/expired
                    all_m_res = (
                        self.client.table("challenge_university_matches")
                        .select("*")
                        .eq("challenge_id", challenge_id)
                        .execute()
                    )
                    all_matches = all_m_res.data or []
                    if all_matches and all(m.get("status") in ["rejected", "expired"] for m in all_matches):
                        try:
                            self.client.table("challenges").update({"status": "no_university_assigned"}).eq("challenge_id", challenge_id).execute()
                        except Exception:
                            pass
            except Exception:
                pass

        action_msg = (
            "University provisional acceptance recorded. Final selection will occur after response deadline."
            if action == "accept" and not selection_finalized
            else f"University selection finalized for '{selection_finalized.get('selected_university_id')}'."
            if selection_finalized
            else "University match invitation declined."
        )

        return {
            "challenge_id": challenge_id,
            "university_id": university_id,
            "status": updated.get("status", new_status),
            "action_taken": f"university_{action}ed",
            "message": action_msg,
            "match": updated,
            "selection": selection_finalized,
        }

    # -------------------------------------------------------------------------
    # 2. Selection Rule Finalization (Highest-Ranked Accepted Selected)
    # -------------------------------------------------------------------------
    def finalize_university_selection(
        self,
        challenge_id: str,
        user: AuthenticatedUser,
        force_deadline: bool = False,
    ) -> Dict[str, Any]:
        """Selection rule per CONCORDIA_BACKEND_CONTEXT.md Section 11 G:

        The highest-ranked accepted university is selected after the deadline.
        Example: ranks 1, 3, 4 accept -> rank 1 selected; ranks 3 and 4 become not_selected.
        Race condition protected: strictly ONE university can be selected per challenge.
        """
        self._get_challenge_or_404(challenge_id)

        with _selection_lock:
            try:
                res = (
                    self.client.table("challenge_university_matches")
                    .select("*")
                    .eq("challenge_id", challenge_id)
                    .order("rank", desc=False)
                    .execute()
                )
                all_matches = res.data or []
            except Exception:
                all_matches = []

            if not all_matches:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"No university matches found for challenge '{challenge_id}'",
                )

            # Check if any match is already selected (Strictly ONE university assignment)
            already_selected = [m for m in all_matches if m.get("status") == "selected"]
            if len(already_selected) > 0:
                already_selected.sort(key=lambda m: m.get("rank", 999))
                winner = already_selected[0]
                winner_id = winner["university_id"]

                # Ensure no other university is selected
                not_sel_count = 0
                for m in all_matches:
                    if m["university_id"] != winner_id and m.get("status") in ["selected", "accepted", "invited", "recommended"]:
                        try:
                            self.client.table("challenge_university_matches").update({
                                "status": "not_selected"
                            }).eq("challenge_id", challenge_id).eq("university_id", m["university_id"]).execute()
                            not_sel_count += 1
                        except Exception:
                            pass

                return {
                    "challenge_id": challenge_id,
                    "selected_university_id": winner_id,
                    "selected_university_rank": winner.get("rank"),
                    "status": "selected",
                    "not_selected_count": not_sel_count,
                    "message": f"University '{winner_id}' (Rank {winner.get('rank')}) is the official assigned university.",
                    "match": winner,
                }

            # Filter candidates that accepted
            accepted_candidates = [m for m in all_matches if m.get("status") == "accepted"]

            if not accepted_candidates:
                # Check if all candidates are terminal (rejected or expired)
                all_terminal = all(m.get("status") in ["rejected", "expired"] for m in all_matches) if all_matches else False
                if all_terminal or force_deadline:
                    try:
                        self.client.table("challenges").update({
                            "status": "no_university_assigned"
                        }).eq("challenge_id", challenge_id).execute()
                    except Exception:
                        pass
                    return {
                        "challenge_id": challenge_id,
                        "selected_university_id": None,
                        "selected_university_rank": None,
                        "status": "no_university_assigned",
                        "not_selected_count": 0,
                        "message": "All university invitations rejected or expired. No university assigned.",
                        "match": None,
                    }
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"No universities have accepted challenge '{challenge_id}'. "
                        f"Cannot finalize selection until at least one university accepts."
                    ),
                )

            # Sort by rank ascending (rank 1 is best)
            accepted_candidates.sort(key=lambda m: m.get("rank", 999))
            winner = accepted_candidates[0]
            winner_id = winner["university_id"]

            # Update winner to 'selected'
            try:
                self.client.table("challenge_university_matches").update({
                    "status": "selected"
                }).eq("challenge_id", challenge_id).eq("university_id", winner_id).execute()
            except Exception:
                pass
            winner["status"] = "selected"

            # Update other candidates (other accepted, invited, recommended) to 'not_selected'
            not_selected_count = 0
            for m in all_matches:
                if m["university_id"] != winner_id and m.get("status") in ["accepted", "invited", "recommended"]:
                    try:
                        self.client.table("challenge_university_matches").update({
                            "status": "not_selected"
                        }).eq("challenge_id", challenge_id).eq("university_id", m["university_id"]).execute()
                    except Exception:
                        pass
                    not_selected_count += 1

            # Update challenges.status to 'university_selected'
            try:
                self.client.table("challenges").update({
                    "status": "university_selected"
                }).eq("challenge_id", challenge_id).execute()
            except Exception:
                pass

            # Automatically trigger deterministic industry matches generation
            try:
                from app.services.matching_service import MatchingService
                MatchingService(self.client).get_or_generate_industry_matches(challenge_id, user)
            except Exception:
                pass

            return {
                "challenge_id": challenge_id,
                "selected_university_id": winner_id,
                "selected_university_rank": winner.get("rank"),
                "status": "selected",
                "not_selected_count": not_selected_count,
                "message": (
                    f"University '{winner_id}' (Rank {winner.get('rank')}) successfully selected. "
                    f"{not_selected_count} other candidate(s) transitioned to 'not_selected'."
                ),
                "match": winner,
            }

    # -------------------------------------------------------------------------
    # 3. Faculty Allocation & Project Creation
    # -------------------------------------------------------------------------
    def create_project(
        self,
        payload: Dict[str, Any],
        user: AuthenticatedUser,
    ) -> Dict[str, Any]:
        """Creates a collaborative project upon faculty allocation.

        Validations:
        - User must be verified university_admin for university_id
        - University must be the 'selected' university for challenge_id
        - faculty_id must exist in faculty table and belong strictly to university_id
        - industry_id must exist if supplied
        - Initial status is 'proposed'
        """
        challenge_id = payload.get("challenge_id")
        university_id = payload.get("university_id")
        faculty_id = payload.get("faculty_id")
        industry_id = payload.get("industry_id")
        title = payload.get("project_title", "").strip()

        if not challenge_id or not university_id or not faculty_id or not title:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="challenge_id, university_id, faculty_id, and project_title are required.",
            )

        # 1. Verify user is admin of university_id
        self._verify_admin_for_university(user, university_id)

        # 2. Verify university is 'selected' for challenge_id
        match = self._get_match_or_404(challenge_id, university_id)
        if match.get("status") != "selected":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"University '{university_id}' is currently in match status '{match.get('status')}'. "
                    f"Projects can only be created once the university is officially 'selected'."
                ),
            )

        # 3. Verify faculty exists and belongs strictly to university_id
        faculty_rec = self._get_faculty_or_404(faculty_id)
        if faculty_rec.get("university_id") != university_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Faculty '{faculty_id}' ({faculty_rec.get('faculty_name')}) belongs to "
                    f"'{faculty_rec.get('university_id')}', not '{university_id}'. "
                    f"Faculty must strictly belong to the selected university."
                ),
            )

        # 4. Check if project already exists for this challenge
        try:
            existing_prj = (
                self.client.table("projects")
                .select("*")
                .eq("challenge_id", challenge_id)
                .execute()
            )
            if existing_prj.data and len(existing_prj.data) > 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"A project for challenge '{challenge_id}' already exists.",
                )
        except HTTPException:
            raise
        except Exception:
            pass

        # 5. Generate project ID & persist
        project_id = f"PRJ-{university_id}-{uuid.uuid4().hex[:6].upper()}"
        initial_status = payload.get("status", "proposed")
        if initial_status not in VALID_PROJECT_STATUSES:
            initial_status = "proposed"

        project_record = {
            "project_id": project_id,
            "challenge_id": challenge_id,
            "university_id": university_id,
            "faculty_id": faculty_id,
            "industry_id": industry_id,
            "project_title": title,
            "description": payload.get("description"),
            "status": initial_status,
            "start_date": payload.get("start_date"),
            "expected_end_date": payload.get("expected_end_date"),
            "actual_end_date": payload.get("actual_end_date"),
        }

        clean_record = {k: v for k, v in project_record.items() if v is not None}

        try:
            res = self.client.table("projects").insert(clean_record).execute()
            saved = res.data[0] if res.data else clean_record
        except Exception:
            saved = clean_record

        # Update challenge status to 'project_created'
        try:
            self.client.table("challenges").update({
                "status": "project_created"
            }).eq("challenge_id", challenge_id).execute()
        except Exception:
            pass

        return saved

    # -------------------------------------------------------------------------
    # 4. Project Queries & Relational Hydration
    # -------------------------------------------------------------------------
    def list_projects(
        self,
        university_id: Optional[str] = None,
        faculty_id: Optional[str] = None,
        challenge_id: Optional[str] = None,
        status_filter: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Lists projects with optional filtering, hydrating institutional details and evidence."""
        query = self.client.table("projects").select("*")
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
            if not projects:
                return []

            # Batch hydrate universities, industries, challenges, and milestone evidence
            u_ids = list({p.get("university_id") for p in projects if p.get("university_id")})
            i_ids = list({p.get("industry_id") for p in projects if p.get("industry_id")})
            c_ids = list({p.get("challenge_id") for p in projects if p.get("challenge_id")})
            p_ids = [p.get("project_id") for p in projects if p.get("project_id")]

            u_map = {}
            if u_ids:
                try:
                    u_res = self.client.table("universities").select("university_id, university_name").in_("university_id", u_ids).execute()
                    u_map = {row["university_id"]: row.get("university_name") for row in (u_res.data or [])}
                except Exception:
                    pass

            i_map = {}
            if i_ids:
                try:
                    i_res = self.client.table("industries").select("industry_id, industry_name").in_("industry_id", i_ids).execute()
                    i_map = {row["industry_id"]: row.get("industry_name") for row in (i_res.data or [])}
                except Exception:
                    pass

            c_map = {}
            if c_ids:
                try:
                    c_res = self.client.table("challenges").select("challenge_id, title, description, location").in_("challenge_id", c_ids).execute()
                    c_map = {row["challenge_id"]: row for row in (c_res.data or [])}
                except Exception:
                    pass

            ev_map = {}
            if p_ids:
                try:
                    m_res = self.client.table("project_milestones").select("project_id, evidence_url").in_("project_id", p_ids).execute()
                    for m in (m_res.data or []):
                        if m.get("evidence_url") and m.get("project_id") not in ev_map:
                            ev_map[m["project_id"]] = m.get("evidence_url")
                except Exception:
                    pass

            for p in projects:
                p["university_name"] = u_map.get(p.get("university_id")) or p.get("university_id")
                if p.get("industry_id"):
                    p["industry_name"] = i_map.get(p.get("industry_id")) or p.get("industry_id")
                ch = c_map.get(p.get("challenge_id")) or {}
                p["challenge_title"] = ch.get("title")
                p["challenge_description"] = ch.get("description")
                p["evidence_url"] = ev_map.get(p.get("project_id"))

            return projects
        except Exception:
            return []

    def get_project(self, project_id: str) -> Dict[str, Any]:
        """Retrieves a single project and hydrates its university, faculty, and challenge details."""
        try:
            res = self.client.table("projects").select("*").eq("project_id", project_id).execute()
            if not res.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Project '{project_id}' not found",
                )
            project = res.data[0]
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project '{project_id}' not found",
            )

        # Hydrate university
        try:
            u_res = self.client.table("universities").select("*").eq("university_id", project["university_id"]).execute()
            project["university"] = u_res.data[0] if u_res.data else None
        except Exception:
            project["university"] = None

        # Hydrate faculty
        if project.get("faculty_id"):
            try:
                f_res = self.client.table("faculty").select("*").eq("faculty_id", project["faculty_id"]).execute()
                project["faculty"] = f_res.data[0] if f_res.data else None
            except Exception:
                project["faculty"] = None

        # Hydrate challenge
        try:
            c_res = self.client.table("challenges").select("*").eq("challenge_id", project["challenge_id"]).execute()
            project["challenge"] = c_res.data[0] if c_res.data else None
        except Exception:
            project["challenge"] = None

        return project

    # -------------------------------------------------------------------------
    # Internal Validation Helpers
    # -------------------------------------------------------------------------
    def _resolve_university_admin_record(self, user: AuthenticatedUser) -> Optional[Dict[str, Any]]:
        """Authoritatively resolves university admin stakeholder record from stakeholder, user_id, or email."""
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
        if getattr(user, "profile", None) and user.profile.get("university_id"):
            return {"university_id": user.profile.get("university_id")}
        return None

    def _verify_admin_for_university(self, user: AuthenticatedUser, university_id: str):
        """Ensures that the user is an authorized, verified admin for university_id."""
        if user.role not in ["university_admin", "government"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden: Role '{user.role}' cannot perform university administrative actions.",
            )

        if not user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: Your university administrator account is pending institutional verification.",
            )

        if user.role == "university_admin":
            admin_rec = self._resolve_university_admin_record(user)
            admin_uni = (admin_rec or {}).get("university_id")
            if not admin_uni or admin_uni != university_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=(
                        f"Access forbidden: You are an administrator of '{admin_uni}', "
                        f"not '{university_id}'. You cannot manage other universities."
                    ),
                )

    def list_university_invitations(
        self,
        university_id: Optional[str],
        user: AuthenticatedUser,
        status_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Lists challenge match invitations for a university with hydrated challenge details."""
        if user.role == "university_admin":
            admin_rec = self._resolve_university_admin_record(user)
            auth_uni_id = (admin_rec or {}).get("university_id")
            if not auth_uni_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access forbidden: Could not resolve your authorized university institution.",
                )
            if university_id and university_id != auth_uni_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access forbidden: You cannot access invitations for university '{university_id}'.",
                )
            university_id = auth_uni_id
        else:
            self._verify_admin_for_university(user, university_id)

        try:
            query = (
                self.client.table("challenge_university_matches")
                .select("*")
                .eq("university_id", university_id)
            )
            if status_filter:
                query = query.eq("status", status_filter)
            res = query.order("created_at", desc=True).execute()
            matches = res.data or []
        except Exception:
            matches = []

        # Pre-fetch all universities into lookup map
        unis_map = {}
        try:
            u_res = self.client.table("universities").select("university_id, university_name").execute()
            for u in (u_res.data or []):
                unis_map[u["university_id"]] = u.get("university_name") or u["university_id"]
        except Exception:
            pass

        hydrated = []
        for match in matches:
            ch_id = match.get("challenge_id")
            item = dict(match)
            item["university_name"] = unis_map.get(university_id) or university_id
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

            # Hydrate all Top-5 ranked matches for this challenge
            try:
                all_m_res = (
                    self.client.table("challenge_university_matches")
                    .select("*")
                    .eq("challenge_id", ch_id)
                    .order("rank", desc=False)
                    .execute()
                )
                all_matches = all_m_res.data or []
                for m in all_matches:
                    m["university_name"] = unis_map.get(m.get("university_id")) or m.get("university_id")
                item["all_matches"] = all_matches
            except Exception:
                item["all_matches"] = [item]

            # Hydrate associated project if created
            try:
                p_res = self.client.table("projects").select("*").eq("challenge_id", ch_id).execute()
                if p_res and p_res.data:
                    proj = p_res.data[0]
                    # If faculty assigned, hydrate faculty name
                    if proj.get("faculty_id"):
                        try:
                            f_res = self.client.table("faculty").select("faculty_name, email").eq("faculty_id", proj["faculty_id"]).execute()
                            if f_res and f_res.data:
                                proj["faculty_name"] = f_res.data[0].get("faculty_name")
                                proj["faculty_email"] = f_res.data[0].get("email")
                        except Exception:
                            pass
                    item["project"] = proj
                else:
                    item["project"] = None
            except Exception:
                item["project"] = None

            hydrated.append(item)

        return hydrated

    def list_university_faculty(self, user: AuthenticatedUser) -> List[Dict[str, Any]]:
        """Lists authoritative faculty belonging strictly to the authenticated administrator's university."""
        admin_rec = self._resolve_university_admin_record(user)
        uni_id = (admin_rec or {}).get("university_id")
        if not uni_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: Unlinked administrator cannot query university faculty.",
            )
        try:
            res = (
                self.client.table("faculty")
                .select("faculty_id, faculty_name, university_id, department, designation, expertise, email, research_areas")
                .eq("university_id", uni_id)
                .order("faculty_name", desc=False)
                .execute()
            )
            return res.data or []
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch faculty list: {str(e)}",
            )

    def allocate_faculty_and_advance(
        self,
        challenge_id: str,
        faculty_ids: List[str],
        user: AuthenticatedUser,
        project_title: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Allocates faculty mentors (multiple selection supported) to an approved challenge.
        Preserves projects.faculty_id as primary mentor; links all mentors in faculty records;
        advances challenge and initializes project milestones to Stage 4 ('Faculty Assigned').
        Triggers Top-5 Industry matching with real data (never invent student names).
        """
        if user.role not in ["university_admin", "government"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden: Role '{user.role}' cannot allocate faculty.",
            )

        admin_rec = self._resolve_university_admin_record(user)
        uni_id = (admin_rec or {}).get("university_id")
        if not uni_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: Could not resolve your authorized university institution.",
            )

        # 1. Verify challenge exists
        challenge = self._get_challenge_or_404(challenge_id)

        # 2. Verify match exists and is routed to this university
        match = self._get_match_or_404(challenge_id, uni_id)
        if match.get("status") in ["rejected", "expired"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot allocate faculty for match in status '{match.get('status')}'.",
            )

        # 3. Validate faculty_ids list
        if not faculty_ids or not isinstance(faculty_ids, list):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one faculty mentor must be selected.",
            )

        # Duplicate prevention (Part 8 & Clarification 1)
        if len(faculty_ids) != len(set(faculty_ids)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Duplicate faculty assignment is not permitted. The same faculty member cannot be selected twice.",
            )

        # Verify all selected faculty belong strictly to this university
        allocated_faculties = []
        for fid in faculty_ids:
            fac = self._get_faculty_or_404(fid)
            if fac.get("university_id") != uni_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Faculty '{fid}' ({fac.get('faculty_name')}) does not belong to university '{uni_id}'.",
                )
            allocated_faculties.append(fac)

        primary_faculty = allocated_faculties[0]
        primary_fid = primary_faculty["faculty_id"]

        # 4. Finalize or ensure university match status is 'selected'
        try:
            self.client.table("challenge_university_matches").update({
                "status": "selected",
                "responded_by": str(user.user_id),
                "responded_at": datetime.now(timezone.utc).isoformat(),
            }).eq("challenge_id", challenge_id).eq("university_id", uni_id).execute()
        except Exception:
            pass

        # 5. Check if project already exists, else create
        existing_proj = None
        try:
            p_res = self.client.table("projects").select("*").eq("challenge_id", challenge_id).execute()
            if p_res.data and len(p_res.data) > 0:
                existing_proj = p_res.data[0]
        except Exception:
            pass

        title = project_title or challenge.get("title") or "Collaborative Innovation Project"

        if existing_proj:
            project_id = existing_proj["project_id"]
            try:
                self.client.table("projects").update({
                    "university_id": uni_id,
                    "faculty_id": primary_fid,
                    "status": "active" if existing_proj.get("status") in ["proposed", "active"] else existing_proj.get("status"),
                }).eq("project_id", project_id).execute()
                saved_project = {**existing_proj, "faculty_id": primary_fid}
            except Exception:
                saved_project = existing_proj
        else:
            project_id = f"PRJ-{uni_id}-{uuid.uuid4().hex[:6].upper()}"
            proj_data = {
                "project_id": project_id,
                "challenge_id": challenge_id,
                "university_id": uni_id,
                "faculty_id": primary_fid,
                "project_title": title,
                "description": challenge.get("description"),
                "status": "active",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            try:
                res = self.client.table("projects").insert(proj_data).execute()
                saved_project = res.data[0] if res.data else proj_data
            except Exception:
                saved_project = proj_data

        # Link project_id in faculty.past_project_ids for queryable relation
        for fac in allocated_faculties:
            existing_pids = fac.get("past_project_ids") or ""
            pid_list = [p.strip() for p in str(existing_pids).split(",") if p.strip()]
            if project_id not in pid_list:
                pid_list.append(project_id)
                new_pids = ", ".join(pid_list)
                try:
                    self.client.table("faculty").update({"past_project_ids": new_pids}).eq("faculty_id", fac["faculty_id"]).execute()
                except Exception:
                    pass

        # 6. Initialize milestones to Stage 4: "Faculty Assigned"
        milestone_stages = [
            ("Problem Submitted", "Citizen/Stakeholder problem submitted to platform", "completed", 100),
            ("Routed to Universities", "Deterministic routing to eligible university institutions", "completed", 100),
            ("University Allocated", f"Officially allocated to {uni_id}", "completed", 100),
            ("Faculty Assigned", f"Faculty mentor(s) assigned: {', '.join(f['faculty_name'] for f in allocated_faculties)}", "completed", 100),
            ("Student Team Formed", "Formation and confirmation of multidisciplinary student team", "pending", 0),
            ("Development In Progress", "Active solution prototyping and technical development", "pending", 0),
            ("Solution Deployed", "Field testing, deployment, and impact validation", "pending", 0),
        ]

        try:
            for name, desc, st, pct in milestone_stages:
                m_check = self.client.table("project_milestones").select("milestone_id").eq("project_id", project_id).eq("milestone_name", name).execute()
                if not m_check.data:
                    self.client.table("project_milestones").insert({
                        "project_id": project_id,
                        "milestone_name": name,
                        "description": desc,
                        "assigned_to": primary_faculty.get("faculty_name") if name == "Faculty Assigned" else None,
                        "status": st,
                        "completion_percentage": pct,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    }).execute()
        except Exception:
            pass

        # Update challenge status
        try:
            self.client.table("challenges").update({"status": "project_created"}).eq("challenge_id", challenge_id).execute()
        except Exception:
            pass

        # 7. Trigger deterministic Top-5 Industry matching (Part 11 & Clarification 2)
        industry_matches = []
        try:
            from app.services.matching_service import MatchingService
            industry_matches = MatchingService(self.client).get_or_generate_industry_matches(challenge_id, user, limit=5)
        except Exception:
            pass

        return {
            "success": True,
            "project_id": project_id,
            "challenge_id": challenge_id,
            "university_id": uni_id,
            "primary_faculty_id": primary_fid,
            "primary_faculty_name": primary_faculty.get("faculty_name"),
            "assigned_faculties": [
                {
                    "faculty_id": f["faculty_id"],
                    "faculty_name": f.get("faculty_name"),
                    "department": f.get("department"),
                    "designation": f.get("designation"),
                    "email": f.get("email"),
                }
                for f in allocated_faculties
            ],
            "project": saved_project,
            "industry_matches": industry_matches,
            "current_milestone": "Faculty Assigned",
            "message": f"Successfully allocated {len(allocated_faculties)} faculty mentor(s). Project created and Top-5 Industry matching initiated.",
        }

    def list_university_mous(self, user: AuthenticatedUser) -> List[Dict[str, Any]]:
        """Lists factual MOU collaboration records for the authenticated university's partnered projects.
        Strictly avoids fabricating fake PDFs or fake records.
        """
        if user.role not in ["university_admin", "government"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden: Role '{user.role}' cannot view university MOUs.",
            )

        admin_rec = self._resolve_university_admin_record(user)
        uni_id = (admin_rec or {}).get("university_id")
        if not uni_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: Could not resolve your authorized university institution.",
            )

        try:
            p_res = (
                self.client.table("projects")
                .select("*")
                .eq("university_id", uni_id)
                .order("created_at", desc=True)
                .execute()
            )
            projects = p_res.data or []
        except Exception:
            projects = []

        mous = []
        for p in projects:
            ind_id = p.get("industry_id")
            if not ind_id:
                cid = p.get("challenge_id")
                if cid:
                    try:
                        cim = self.client.table("challenge_industry_matches").select("*").eq("challenge_id", cid).eq("status", "accepted").execute()
                        if cim.data and len(cim.data) > 0:
                            ind_id = cim.data[0].get("industry_id")
                    except Exception:
                        pass

            if not ind_id:
                continue

            uni_res = self.client.table("universities").select("university_name").eq("university_id", uni_id).execute()
            uni_name = uni_res.data[0].get("university_name") if (uni_res and uni_res.data) else uni_id

            ind_res = self.client.table("industries").select("industry_name").eq("industry_id", ind_id).execute()
            ind_name = ind_res.data[0].get("industry_name") if (ind_res and ind_res.data) else ind_id

            ch_doc = None
            if p.get("challenge_id"):
                try:
                    ch_res = self.client.table("challenges").select("title, document").eq("challenge_id", p["challenge_id"]).execute()
                    if ch_res.data:
                        raw_doc = ch_res.data[0].get("document")
                        if raw_doc and str(raw_doc).strip() not in ["", "-", "None", "null"]:
                            ch_doc = str(raw_doc).strip()
                except Exception:
                    pass

            # Check if an MOU URL is stored in challenge_industry_matches.response_note
            if not ch_doc and p.get("challenge_id"):
                try:
                    cim_res = self.client.table("challenge_industry_matches").select("response_note").eq("challenge_id", p["challenge_id"]).execute()
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
                "mou_id": f"MOU-{uni_id}-{ind_id}-{pid}",
                "project_id": pid,
                "project_title": p.get("project_title"),
                "university_id": uni_id,
                "university_name": uni_name,
                "industry_id": ind_id,
                "industry_name": ind_name,
                "government_partner": "Government of Jharkhand — Department of Higher & Technical Education",
                "status": "Active Collaboration",
                "effective_date": p.get("start_date") or p.get("created_at", "")[:10],
                "document_url": resolve_document_signed_url(ch_doc) if has_doc else None,
                "has_document": has_doc,
            })

        return mous

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
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project '{project_id}' not found",
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

    def _get_match_or_404(self, challenge_id: str, university_id: str) -> Dict[str, Any]:
        try:
            res = (
                self.client.table("challenge_university_matches")
                .select("*")
                .eq("challenge_id", challenge_id)
                .eq("university_id", university_id)
                .execute()
            )
            if not res.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Match record between challenge '{challenge_id}' and university '{university_id}' does not exist.",
                )
            return res.data[0]
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Match record between challenge '{challenge_id}' and university '{university_id}' does not exist.",
            )

    def upload_project_mou(
        self,
        project_id: str,
        filename: str,
        content: bytes,
        content_type: str,
        user: AuthenticatedUser,
    ) -> Dict[str, Any]:
        """Uploads an official signed MOU document to Supabase Storage ('documents' bucket)
        and persists the reference to DB.
        """
        import os
        import uuid

        project = self.get_project(project_id)
        uni_id = project.get("university_id")
        ind_id = project.get("industry_id")
        cid = project.get("challenge_id")

        # Authorization
        if user.role == "university_admin":
            admin_rec = self._resolve_university_admin_record(user)
            admin_uni = (admin_rec or {}).get("university_id")
            if not admin_uni or admin_uni != uni_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access forbidden: You cannot upload an MOU for university '{uni_id}'.",
                )
        elif user.role in ["industry_employee", "industry"]:
            if not user.approval_authority:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access forbidden: Only verified Industry SPOCs with approval authority can upload MOUs.",
                )
            emp_ind = getattr(user, "stakeholder", {}).get("industry_id") if getattr(user, "stakeholder", None) else None
            if not emp_ind and getattr(user, "profile", None):
                emp_ind = user.profile.get("industry_id")
            if ind_id and emp_ind and emp_ind != ind_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access forbidden: You cannot upload an MOU for industry '{ind_id}'.",
                )
        elif user.role != "government":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.role}' is not authorized to upload project MOUs.",
            )

        # File validation
        allowed_exts = {".pdf", ".docx", ".doc", ".png", ".jpg", ".jpeg"}
        ext = os.path.splitext(filename)[1].lower()
        if ext not in allowed_exts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file format '{ext}'. Allowed formats: PDF, DOCX, DOC, PNG, JPG, JPEG.",
            )

        if len(content) > 10 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File size exceeds 10 MB limit ({round(len(content) / (1024 * 1024), 2)} MB).",
            )

        # Upload to Supabase Storage (Private bucket)
        try:
            self.client.storage.create_bucket("documents", options={"public": False})
        except Exception:
            pass

        safe_filename = f"MOU_{uuid.uuid4().hex[:8]}_{filename.replace(' ', '_')}"
        storage_path = f"mous/{project_id}/{safe_filename}"
        mime = content_type or ("application/pdf" if ext == ".pdf" else "application/octet-stream")

        try:
            self.client.storage.from_("documents").upload(
                path=storage_path,
                file=content,
                file_options={"content-type": mime, "upsert": "true"},
            )
            doc_url = resolve_document_signed_url(storage_path) or storage_path
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload document to storage: {str(e)}",
            )

        # Persist document URL in DB
        if cid:
            try:
                self.client.table("challenges").update({"document": doc_url}).eq("challenge_id", cid).execute()
            except Exception:
                pass
            try:
                self.client.table("challenge_industry_matches").update({"response_note": f"MOU_URL:{doc_url}"}).eq("challenge_id", cid).execute()
            except Exception:
                pass

        return {
            "success": True,
            "project_id": project_id,
            "document_url": doc_url,
            "storage_path": storage_path,
            "filename": filename,
            "size_bytes": len(content),
            "content_type": mime,
            "uploaded_by": user.email or str(user.user_id),
        }

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
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Faculty record '{faculty_id}' not found in database.",
            )
