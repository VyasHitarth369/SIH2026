"""matching_service.py

Coordinates database operations for challenge university and industry matching.
Validates challenge prerequisites, fetches actual database records, executes the
deterministic matching engine, and persists results into challenge_university_matches
and challenge_industry_matches while respecting UNIQUE constraints.
"""

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple
from fastapi import HTTPException, status

from app.database import get_supabase
from app.services.auth_service import AuthenticatedUser
from app.services.matching_engine import (
    rank_universities,
    rank_industries,
    score_university_candidate,
)


class MatchingService:
    """Service handling university and industry match generation and retrieval."""

    def __init__(self, client=None):
        self._client = client

    @property
    def client(self):
        return self._client if self._client is not None else get_supabase()


    # -------------------------------------------------------------------------
    # University Matching
    # -------------------------------------------------------------------------
    def _fetch_university_workloads(self) -> Dict[str, int]:
        """Calculates active project/challenge workloads for all universities from DB tables.

        Statuses counted as active:
        - projects: 'proposed', 'active', 'in_progress', 'prototype', 'pilot'
        - challenge_university_matches: 'accepted', 'selected'
        Prevents double-counting by tracking distinct active challenge_ids per university.
        """
        counts: Dict[str, set] = {}
        try:
            active_proj_statuses = ["proposed", "active", "in_progress", "prototype", "pilot"]
            p_res = (
                self.client.table("projects")
                .select("university_id, challenge_id, status")
                .in_("status", active_proj_statuses)
                .execute()
            )
            for row in (p_res.data or []):
                uid = row.get("university_id")
                cid = row.get("challenge_id")
                if uid and cid:
                    counts.setdefault(uid, set()).add(cid)
        except Exception:
            pass

        try:
            m_res = (
                self.client.table("challenge_university_matches")
                .select("university_id, challenge_id, status")
                .in_("status", ["accepted", "selected"])
                .execute()
            )
            for row in (m_res.data or []):
                uid = row.get("university_id")
                cid = row.get("challenge_id")
                if uid and cid:
                    counts.setdefault(uid, set()).add(cid)
        except Exception:
            pass

        return {uid: len(cids) for uid, cids in counts.items()}

    def _hydrate_university_matches(
        self,
        matches: List[Dict[str, Any]],
        challenge: Dict[str, Any],
        analysis: Dict[str, Any],
        workloads: Dict[str, int],
    ) -> List[Dict[str, Any]]:
        """Hydrates persisted match records with university names, active workloads, and matched capabilities."""
        unis_by_id = {u["university_id"]: u for u in self._fetch_universities()}
        min_workload = min(workloads.values()) if workloads else 0

        hydrated = []
        for m in matches:
            uid = m.get("university_id")
            uni = unis_by_id.get(uid, {})
            active_proj = workloads.get(uid, 0)
            workload_advantage = (active_proj - min_workload == 0) and any(w - active_proj >= 3 for w in workloads.values())

            # Extract capability tokens from university record
            _, breakdown, _ = score_university_candidate(challenge, analysis, uni) if uni else (0, {}, "")

            item = dict(m)
            item.update({
                "university_name": uni.get("university_name") or uni.get("name") or uid,
                "city": uni.get("city"),
                "district": uni.get("district"),
                "institution_type": uni.get("institution_type") or "University",
                "active_projects": active_proj,
                "active_project_count": active_proj,
                "matched_skills": breakdown.get("matched_skills", []),
                "matched_technologies": breakdown.get("matched_technologies", []),
                "matched_domains": breakdown.get("matched_domains", []),
                "workload_advantage_applied": workload_advantage,
            })
            hydrated.append(item)
        return hydrated

    def get_or_generate_university_matches(
        self,
        challenge_id: str,
        user: Optional[AuthenticatedUser] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Retrieves persisted university matches or deterministically generates, ranks,
        and persists them if not already computed.
        """
        challenge, analysis = self._validate_challenge_and_analysis(challenge_id, user)
        workloads = self._fetch_university_workloads()

        # 1. Check if matches already exist in database (prevent duplicates)
        try:
            existing_res = (
                self.client.table("challenge_university_matches")
                .select("*")
                .eq("challenge_id", challenge_id)
                .order("rank", desc=False)
                .execute()
            )
            if existing_res.data and len(existing_res.data) > 0:
                meaningful_existing = [m for m in existing_res.data if m.get("match_score", 0) > 0]
                if meaningful_existing:
                    return self._hydrate_university_matches(meaningful_existing[:limit], challenge, analysis, workloads)
        except Exception:
            pass

        # 2. Fetch real universities from database
        universities = self._fetch_universities()
        if not universities:
            return []

        # 3. Deterministically score and rank candidates with workload balancing
        ranked = rank_universities(challenge, analysis, universities, workloads=workloads)
        meaningful_matches = [m for m in ranked if m.get("match_score", 0) > 0]
        top_matches = meaningful_matches[:limit]

        # 4. Persist to challenge_university_matches respecting UNIQUE(challenge_id, university_id)
        persisted_rows = []
        deadline_iso = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
        for match in top_matches:
            row = {
                "challenge_id": challenge_id,
                "university_id": match["university_id"],
                "rank": match["rank"],
                "match_score": match["match_score"],
                "match_reason": match["match_reason"],
                "status": "recommended",
                "response_deadline": match.get("response_deadline") or deadline_iso,
            }
            try:
                res = (
                    self.client.table("challenge_university_matches")
                    .upsert(row, on_conflict="challenge_id,university_id")
                    .execute()
                )
                db_row = res.data[0] if res.data else row
            except Exception:
                db_row = row

            merged = dict(match)
            merged.update(db_row)
            persisted_rows.append(merged)

        return persisted_rows

    # -------------------------------------------------------------------------
    # Industry Matching
    # -------------------------------------------------------------------------
    def get_or_generate_industry_matches(
        self,
        challenge_id: str,
        user: Optional[AuthenticatedUser] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Retrieves persisted industry matches or deterministically generates, ranks,

        and persists them if not already computed.
        """
        challenge, analysis = self._validate_challenge_and_analysis(challenge_id, user)

        # 1. Check if matches already exist in database (prevent duplicates)
        try:
            existing_res = (
                self.client.table("challenge_industry_matches")
                .select("*")
                .eq("challenge_id", challenge_id)
                .order("rank", desc=False)
                .execute()
            )
            if existing_res.data and len(existing_res.data) > 0:
                meaningful_existing = [m for m in existing_res.data if m.get("match_score", 0) > 0]
                return meaningful_existing[:limit]
        except Exception:
            pass

        # 2. Fetch real industries from database
        industries = self._fetch_industries()
        if not industries:
            return []

        # 3. Deterministically score and rank candidates
        ranked = rank_industries(challenge, analysis, industries)
        meaningful_matches = [m for m in ranked if m.get("match_score", 0) > 0]
        top_matches = meaningful_matches[:limit]

        # 4. Persist to challenge_industry_matches respecting UNIQUE(challenge_id, industry_id)
        persisted_rows = []
        for match in top_matches:
            row = {
                "challenge_id": challenge_id,
                "industry_id": match["industry_id"],
                "rank": match["rank"],
                "match_score": match["match_score"],
                "match_reason": match["match_reason"],
                "status": "recommended",
            }
            try:
                res = (
                    self.client.table("challenge_industry_matches")
                    .upsert(row, on_conflict="challenge_id,industry_id")
                    .execute()
                )
                persisted_rows.append(res.data[0] if res.data else row)
            except Exception:
                persisted_rows.append(row)

        return persisted_rows

    # -------------------------------------------------------------------------
    # Internal Validation & Fetch Helpers
    # -------------------------------------------------------------------------
    def _validate_challenge_and_analysis(
        self, challenge_id: str, user: Optional[AuthenticatedUser] = None
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Ensures challenge exists, user is authorized, and ai_analysis prerequisites are met."""
        # 1. Fetch challenge
        ch_res = (
            self.client.table("challenges")
            .select("*")
            .eq("challenge_id", challenge_id)
            .execute()
        )
        if not ch_res.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Challenge '{challenge_id}' not found",
            )
        challenge = ch_res.data[0]

        # 2. Fetch ai_analysis
        an_res = (
            self.client.table("ai_analysis")
            .select("*")
            .eq("challenge_id", challenge_id)
            .execute()
        )
        if not an_res.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Challenge '{challenge_id}' has not undergone AI review and classification. "
                    f"Run /api/challenges/{challenge_id}/analyze first before matching."
                ),
            )
        analysis = an_res.data[0]

        return challenge, analysis

    def _fetch_universities(self) -> List[Dict[str, Any]]:
        """Queries universities from the database."""
        try:
            res = self.client.table("universities").select("*").execute()
            return res.data or []
        except Exception:
            return []

    def _fetch_industries(self) -> List[Dict[str, Any]]:
        """Queries industries from the database."""
        try:
            res = self.client.table("industries").select("*").execute()
            return res.data or []
        except Exception:
            return []

    def validate_university_id(self, university_id: str) -> Dict[str, Any]:
        """Validates that a university ID exists in public.universities. Rejects fake/hallucinated IDs."""
        res = self.client.table("universities").select("*").eq("university_id", university_id).execute()
        if not res.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Invalid university ID '{university_id}'. University does not exist in database.",
            )
        return res.data[0]

    def validate_industry_id(self, industry_id: str) -> Dict[str, Any]:
        """Validates that an industry ID exists in public.industries. Rejects fake/hallucinated IDs."""
        res = self.client.table("industries").select("*").eq("industry_id", industry_id).execute()
        if not res.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Invalid industry ID '{industry_id}'. Industry does not exist in database.",
            )
        return res.data[0]
