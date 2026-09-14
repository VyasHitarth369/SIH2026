"""test_phase5_university_project.py

Comprehensive test suite for Phase 5:
1. University Admin Authorization (cross-university access blocked, 403)
2. Provisional University Acceptance (accept recorded with note, awaiting deadline)
3. Selection Rule Enforcement (highest-ranked accepted university selected; others not_selected)
4. Faculty Allocation & Relationship Validation (faculty must belong strictly to selected university)
5. Project Creation & Status Lifecycle (status='proposed', challenge updated, duplicate prevented)
6. Project Queries & Relational Hydration (GET /api/projects and /api/projects/{id})
"""

import copy
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from starlette.testclient import TestClient

from app.main import app
from app.dependencies.auth import get_current_user
from app.routes.challenges import get_workflow_service as get_challenge_workflow_service
from app.routes.projects import get_workflow_service as get_project_workflow_service
from app.services.auth_service import AuthenticatedUser
from app.services.university_workflow_service import UniversityWorkflowService


class MockPhase5WorkflowService(UniversityWorkflowService):
    """In-memory service for hermetic testing of Phase 5 university workflows."""

    def __init__(self):
        super().__init__()
        self.challenges: Dict[str, Dict[str, Any]] = {}
        self.universities: Dict[str, Dict[str, Any]] = {}
        self.faculty: Dict[str, Dict[str, Any]] = {}
        self.matches: Dict[str, Dict[str, Any]] = {}  # key: f"{cid}:{uid}"
        self.projects: Dict[str, Dict[str, Any]] = {}

    def _get_challenge_or_404(self, challenge_id: str):
        from fastapi import HTTPException
        if challenge_id not in self.challenges:
            raise HTTPException(status_code=404, detail=f"Challenge '{challenge_id}' not found")
        return dict(self.challenges[challenge_id])

    def _get_match_or_404(self, challenge_id: str, university_id: str):
        from fastapi import HTTPException
        key = f"{challenge_id}:{university_id}"
        if key not in self.matches:
            raise HTTPException(
                status_code=404,
                detail=f"Match record between challenge '{challenge_id}' and university '{university_id}' does not exist.",
            )
        return dict(self.matches[key])

    def _get_faculty_or_404(self, faculty_id: str):
        from fastapi import HTTPException
        if faculty_id not in self.faculty:
            raise HTTPException(status_code=404, detail=f"Faculty record '{faculty_id}' not found")
        return dict(self.faculty[faculty_id])

    def respond_to_university_match(
        self,
        challenge_id: str,
        university_id: str,
        action: str,
        user: AuthenticatedUser,
        response_note: Optional[str] = None,
    ):
        from fastapi import HTTPException
        self._verify_admin_for_university(user, university_id)
        self._get_challenge_or_404(challenge_id)
        match_record = self._get_match_or_404(challenge_id, university_id)

        current_status = match_record.get("status")
        if current_status not in ["recommended", "invited"]:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot respond to match in status '{current_status}'. Must be 'recommended' or 'invited'.",
            )

        new_status = "accepted" if action == "accept" else "rejected"
        key = f"{challenge_id}:{university_id}"
        self.matches[key]["status"] = new_status
        self.matches[key]["responded_by"] = str(user.user_id)
        self.matches[key]["responded_at"] = datetime.now(timezone.utc).isoformat()
        self.matches[key]["response_note"] = response_note

        return {
            "challenge_id": challenge_id,
            "university_id": university_id,
            "status": new_status,
            "action_taken": f"university_{action}ed",
            "message": "University response recorded successfully.",
            "match": dict(self.matches[key]),
        }

    def finalize_university_selection(
        self,
        challenge_id: str,
        user: AuthenticatedUser,
        force_deadline: bool = False,
    ):
        from fastapi import HTTPException
        self._get_challenge_or_404(challenge_id)

        matches_for_ch = [m for m in self.matches.values() if m["challenge_id"] == challenge_id]
        if not matches_for_ch:
            raise HTTPException(status_code=404, detail="No matches found")

        accepted = [m for m in matches_for_ch if m["status"] == "accepted"]
        if not accepted:
            raise HTTPException(status_code=400, detail="No universities have accepted challenge yet")

        # Highest-ranked accepted university selected (lowest rank number)
        accepted.sort(key=lambda m: m.get("rank", 999))
        winner = accepted[0]
        winner_id = winner["university_id"]

        self.matches[f"{challenge_id}:{winner_id}"]["status"] = "selected"
        not_selected_count = 0

        for m in matches_for_ch:
            uid = m["university_id"]
            if uid != winner_id and m["status"] in ["accepted", "invited", "recommended"]:
                self.matches[f"{challenge_id}:{uid}"]["status"] = "not_selected"
                not_selected_count += 1

        self.challenges[challenge_id]["status"] = "university_selected"

        return {
            "challenge_id": challenge_id,
            "selected_university_id": winner_id,
            "selected_university_rank": winner.get("rank"),
            "status": "selected",
            "not_selected_count": not_selected_count,
            "message": f"University '{winner_id}' (Rank {winner.get('rank')}) selected.",
            "match": dict(self.matches[f"{challenge_id}:{winner_id}"]),
        }

    def create_project(self, payload: Dict[str, Any], user: AuthenticatedUser):
        import uuid
        from fastapi import HTTPException
        cid = payload["challenge_id"]
        uid = payload["university_id"]
        fid = payload["faculty_id"]
        title = payload.get("project_title", "").strip()

        self._verify_admin_for_university(user, uid)

        # Verify university is 'selected'
        match = self._get_match_or_404(cid, uid)
        if match.get("status") != "selected":
            raise HTTPException(
                status_code=400,
                detail=f"University '{uid}' is in status '{match.get('status')}'. Must be 'selected'.",
            )

        # Verify faculty belongs to university
        faculty_rec = self._get_faculty_or_404(fid)
        if faculty_rec.get("university_id") != uid:
            raise HTTPException(
                status_code=400,
                detail=f"Faculty '{fid}' belongs to '{faculty_rec.get('university_id')}', not '{uid}'.",
            )

        # Check duplicate project
        existing = [p for p in self.projects.values() if p["challenge_id"] == cid]
        if existing:
            raise HTTPException(status_code=400, detail=f"A project for challenge '{cid}' already exists.")

        pid = f"PRJ-{uid}-{uuid.uuid4().hex[:6].upper()}"
        record = {
            "project_id": pid,
            "challenge_id": cid,
            "university_id": uid,
            "faculty_id": fid,
            "industry_id": payload.get("industry_id"),
            "project_title": title,
            "description": payload.get("description"),
            "status": payload.get("status", "proposed"),
            "start_date": payload.get("start_date"),
            "expected_end_date": payload.get("expected_end_date"),
            "actual_end_date": payload.get("actual_end_date"),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.projects[pid] = record
        self.challenges[cid]["status"] = "project_created"
        return dict(record)

    def list_projects(self, university_id=None, faculty_id=None, challenge_id=None, status_filter=None, limit=100):
        res = list(self.projects.values())
        if university_id:
            res = [p for p in res if p["university_id"] == university_id]
        if faculty_id:
            res = [p for p in res if p["faculty_id"] == faculty_id]
        if challenge_id:
            res = [p for p in res if p["challenge_id"] == challenge_id]
        if status_filter:
            res = [p for p in res if p["status"] == status_filter]
        return res[:limit]

    def get_project(self, project_id: str):
        from fastapi import HTTPException
        if project_id not in self.projects:
            raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")
        prj = dict(self.projects[project_id])
        prj["university"] = self.universities.get(prj["university_id"])
        prj["faculty"] = self.faculty.get(prj.get("faculty_id"))
        prj["challenge"] = self.challenges.get(prj["challenge_id"])
        return prj


def run_tests():
    print("=" * 70)
    print("STARTING PHASE 5 UNIVERSITY & PROJECT WORKFLOW TEST SUITE")
    print("=" * 70)

    service = MockPhase5WorkflowService()

    # Seed challenge
    cid = "CHL-2026-RANCHI-WASTE"
    service.challenges[cid] = {
        "challenge_id": cid,
        "title": "Smart Civic Waste Sensor Network",
        "status": "validated",
        "city": "Ranchi",
    }

    # Seed universities
    service.universities["U001"] = {
        "university_id": "U001",
        "university_name": "BIT Mesra, Ranchi",
        "city": "Ranchi",
    }
    service.universities["U003"] = {
        "university_id": "U003",
        "university_name": "NIT Jamshedpur",
        "city": "Jamshedpur",
    }

    # Seed faculty
    service.faculty["FAC001"] = {
        "faculty_id": "FAC001",
        "university_id": "U001",  # Belongs to BIT Mesra
        "faculty_name": "Dr. Abhijit Mustafi",
        "department": "Computer Science & Engg",
    }
    service.faculty["FAC011"] = {
        "faculty_id": "FAC011",
        "university_id": "U003",  # Belongs to NIT Jamshedpur
        "faculty_name": "Prof. Ashok Kumar",
        "department": "Metallurgical & Materials",
    }

    # Seed matches: U001 is Rank 1, U003 is Rank 2
    service.matches[f"{cid}:U001"] = {
        "match_id": 101,
        "challenge_id": cid,
        "university_id": "U001",
        "rank": 1,
        "match_score": 85.50,
        "status": "recommended",
    }
    service.matches[f"{cid}:U003"] = {
        "match_id": 102,
        "challenge_id": cid,
        "university_id": "U003",
        "rank": 2,
        "match_score": 72.00,
        "status": "recommended",
    }

    # User 1: Verified Admin of U001 (BIT Mesra)
    admin_u001 = AuthenticatedUser(
        user_id="user-admin-u001",
        email="admin@bitmesra.ac.in",
        role="university_admin",
        full_name="Registrar BIT Mesra",
        stakeholder={"university_id": "U001", "verification_status": "verified"},
        is_verified=True,
    )

    # User 2: Verified Admin of U003 (NIT Jamshedpur)
    admin_u003 = AuthenticatedUser(
        user_id="user-admin-u003",
        email="admin@nitjsr.ac.in",
        role="university_admin",
        full_name="Dean R&D NIT Jamshedpur",
        stakeholder={"university_id": "U003", "verification_status": "verified"},
        is_verified=True,
    )

    # User 3: Citizen (Unauthorized)
    citizen_user = AuthenticatedUser(
        user_id="user-citizen-999",
        email="citizen@samadhansetu.gov.in",
        role="citizen",
        full_name="Citizen Aarti",
        is_verified=True,
    )

    active_user = admin_u001

    app.dependency_overrides[get_current_user] = lambda: active_user
    app.dependency_overrides[get_challenge_workflow_service] = lambda: service
    app.dependency_overrides[get_project_workflow_service] = lambda: service

    client = TestClient(app)

    # -------------------------------------------------------------
    # TEST 1: University Admin Authorization & Boundary Enforcement
    # -------------------------------------------------------------
    print("\n[TEST 1] University Admin Authorization & Cross-University Security:")
    # Admin of U001 attempts to respond for U003
    r1_cross = client.post(
        f"/api/challenges/{cid}/universities/U003/respond",
        json={"action": "accept", "response_note": "Sneaky cross-university attempt"}
    )
    print("  Cross-university attempt status:", r1_cross.status_code)
    print("  Cross-university response:", r1_cross.json())
    assert r1_cross.status_code == 403
    assert "administrator of 'U001', not 'U003'" in r1_cross.json()["error"]["message"]
    print("  [PASS] Cross-university administrative access blocked with 403.")

    # Citizen attempts to respond
    app.dependency_overrides[get_current_user] = lambda: citizen_user
    r1_citizen = client.post(
        f"/api/challenges/{cid}/universities/U001/respond",
        json={"action": "accept"}
    )
    assert r1_citizen.status_code == 403
    print("  [PASS] Non-admin citizen blocked from university actions with 403.")

    # Restore Admin U001
    app.dependency_overrides[get_current_user] = lambda: admin_u001

    # -------------------------------------------------------------
    # TEST 2: Provisional University Acceptance
    # -------------------------------------------------------------
    print("\n[TEST 2] Provisional University Acceptance Workflow:")
    # First: U003 accepts early
    app.dependency_overrides[get_current_user] = lambda: admin_u003
    r2_u003 = client.post(
        f"/api/challenges/{cid}/universities/U003/respond",
        json={"action": "accept", "response_note": "NIT Jamshedpur R&D accepts. Ready to collaborate."}
    )
    assert r2_u003.status_code == 200
    assert r2_u003.json()["data"]["status"] == "accepted"
    print("  [PASS] Rank 2 (U003) accepted early. Status is provisionally 'accepted'.")

    # Second: U001 accepts within deadline
    app.dependency_overrides[get_current_user] = lambda: admin_u001
    r2_u001 = client.post(
        f"/api/challenges/{cid}/universities/U001/respond",
        json={"action": "accept", "response_note": "BIT Mesra accepts. Advanced IoT lab allocated."}
    )
    assert r2_u001.status_code == 200
    assert r2_u001.json()["data"]["status"] == "accepted"
    print("  [PASS] Rank 1 (U001) accepted. Status is provisionally 'accepted'.")

    # -------------------------------------------------------------
    # TEST 3: Selection Rule (Highest-Ranked Accepted is Selected)
    # -------------------------------------------------------------
    print("\n[TEST 3] Selection Finalization (Highest-Ranked Selected Rule):")
    # Both U001 (Rank 1) and U003 (Rank 2) have accepted. Even though U003 clicked accept first,
    # U001 must win because it has Rank 1.
    r3_sel = client.post(f"/api/challenges/{cid}/universities/finalize-selection")
    print("  Selection Status Code:", r3_sel.status_code)
    sel_data = r3_sel.json()["data"]
    print("  Selected University:", sel_data["selected_university_id"])
    print("  Selected Rank:", sel_data["selected_university_rank"])
    print("  Not Selected Count:", sel_data["not_selected_count"])

    assert r3_sel.status_code == 200
    assert sel_data["selected_university_id"] == "U001"
    assert sel_data["selected_university_rank"] == 1
    assert service.matches[f"{cid}:U001"]["status"] == "selected"
    assert service.matches[f"{cid}:U003"]["status"] == "not_selected"
    assert service.challenges[cid]["status"] == "university_selected"
    print("  [PASS] Rank 1 (U001) officially selected; lower-ranked U003 transitioned to 'not_selected'.")

    # -------------------------------------------------------------
    # TEST 4: Faculty Allocation & University Relationship Validation
    # -------------------------------------------------------------
    print("\n[TEST 4] Faculty Allocation & Relationship Verification:")
    # 4a. Admin of U001 attempts to allocate FAC011 (who belongs to U003!)
    bad_faculty_payload = {
        "challenge_id": cid,
        "university_id": "U001",
        "faculty_id": "FAC011",  # From U003
        "project_title": "Cross-University Faculty Allocation Attempt",
    }
    r4_bad_fac = client.post("/api/projects", json=bad_faculty_payload)
    print("  Mismatched faculty status:", r4_bad_fac.status_code)
    print("  Mismatched faculty response:", r4_bad_fac.json())
    assert r4_bad_fac.status_code == 400
    assert "belongs to 'U003', not 'U001'" in r4_bad_fac.json()["error"]["message"]
    print("  [PASS] Allocation of faculty from different university strictly blocked with 400.")

    # 4b. Non-selected university (U003) attempts to create project
    app.dependency_overrides[get_current_user] = lambda: admin_u003
    r4_unselected = client.post("/api/projects", json={
        "challenge_id": cid,
        "university_id": "U003",
        "faculty_id": "FAC011",
        "project_title": "Unselected University Project Attempt",
    })
    print("  Unselected university project status:", r4_unselected.status_code)
    assert r4_unselected.status_code == 400
    assert "Must be 'selected'" in r4_unselected.json()["error"]["message"]
    print("  [PASS] Unselected university blocked from creating project.")

    # Restore Admin U001
    app.dependency_overrides[get_current_user] = lambda: admin_u001

    # -------------------------------------------------------------
    # TEST 5: Project Creation & Status Lifecycle
    # -------------------------------------------------------------
    print("\n[TEST 5] Legitimate Project Creation & Status Verification:")
    valid_project_payload = {
        "challenge_id": cid,
        "university_id": "U001",
        "faculty_id": "FAC001",  # Belongs to U001!
        "project_title": "Automated Civic Solid Waste Route Optimization Prototype",
        "description": "Collaborative project to deploy smart sensors on municipal garbage trucks and bins in Ranchi.",
        "start_date": "2026-10-01",
        "expected_end_date": "2027-04-01",
        "status": "proposed",
    }
    r5_proj = client.post("/api/projects", json=valid_project_payload)
    print("  Project Creation Status Code:", r5_proj.status_code)
    proj_data = r5_proj.json()["data"]
    print("  Created Project ID:", proj_data["project_id"])
    print("  Project Status:", proj_data["status"])
    print("  Faculty ID:", proj_data["faculty_id"])

    assert r5_proj.status_code == 201
    assert proj_data["project_id"].startswith("PRJ-U001-")
    assert proj_data["status"] == "proposed"
    assert proj_data["faculty_id"] == "FAC001"
    assert service.challenges[cid]["status"] == "project_created"
    created_pid = proj_data["project_id"]
    print("  [PASS] Project created successfully. Initial status='proposed', challenge updated.")

    # 5b. Duplicate project creation blocked
    r5_dup = client.post("/api/projects", json=valid_project_payload)
    assert r5_dup.status_code == 400
    print("  [PASS] Duplicate project for same challenge blocked with 400.")

    # -------------------------------------------------------------
    # TEST 6: Project Queries & Relational Hydration
    # -------------------------------------------------------------
    print("\n[TEST 6] Project Queries & Relational Hydration:")
    # List projects
    r6_list = client.get("/api/projects?university_id=U001")
    assert r6_list.status_code == 200
    assert len(r6_list.json()["data"]) == 1
    print("  [PASS] GET /api/projects retrieved 1 project.")

    # Get single project with relations
    r6_single = client.get(f"/api/projects/{created_pid}")
    assert r6_single.status_code == 200
    single_data = r6_single.json()["data"]
    print("  Hydrated University Name:", single_data["university"]["university_name"])
    print("  Hydrated Faculty Name:", single_data["faculty"]["faculty_name"])
    print("  Hydrated Challenge Title:", single_data["challenge"]["title"])
    assert single_data["university"]["university_id"] == "U001"
    assert single_data["faculty"]["faculty_name"] == "Dr. Abhijit Mustafi"
    assert single_data["challenge"]["title"] == "Smart Civic Waste Sensor Network"
    print("  [PASS] GET /api/projects/{id} hydrated university, faculty, and challenge relations.")

    # Clean overrides
    app.dependency_overrides.clear()
    print("\n" + "=" * 70)
    print("ALL PHASE 5 UNIVERSITY & PROJECT WORKFLOW TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    run_tests()
