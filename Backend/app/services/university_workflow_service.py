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
            "response_note": response_note,
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
        """Lists projects with optional filtering."""
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
            return res.data or []
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
            admin_uni = (user.stakeholder or {}).get("university_id")
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
        university_id: str,
        user: AuthenticatedUser,
        status_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Lists challenge match invitations for a university with hydrated challenge details."""
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
            hydrated.append(item)

        return hydrated

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
