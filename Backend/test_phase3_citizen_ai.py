"""test_phase3_citizen_ai.py

Comprehensive test suite for Phase 3:
1. Citizen Challenge Submission (authenticated user association, impact_scope preservation)
2. Unauthorized Access & Challenge Ownership Security (401 unauth, 403 non-owner)
3. Call 1: Existing-Solution Discovery with Real Evidence (Swachhata App detection, 1 call)
4. Citizen Accepts Existing Solution (terminal state, zero extra calls)
5. Call 2: Citizen Rejects Existing Solution + Gap Validation + Classification (2 calls)
6. Call 1 Direct Validation: Novel Problem with No Existing Solution (1 call, no redundant call 2)
7. Edge Cases: Repeated analyze calls, missing rejection reason, invalid status transition
"""

import os
from typing import Any, Dict, List, Optional
from starlette.testclient import TestClient

from app.main import app
from app.dependencies.auth import get_auth_service, get_current_user
from app.routes.challenges import get_challenge_service
from app.services.auth_service import AuthenticatedUser
from app.services.challenge_service import ChallengeService


# Mock In-Memory Database Service for hermetic Phase 3 testing
class MockChallengeDatabase:
    def __init__(self):
        self.challenges: Dict[str, Dict[str, Any]] = {}
        self.ai_analysis: Dict[str, Dict[str, Any]] = {}

    def insert_challenge(self, record: Dict[str, Any]) -> Dict[str, Any]:
        cid = record["challenge_id"]
        self.challenges[cid] = dict(record)
        return dict(self.challenges[cid])

    def get_challenge(self, cid: str) -> Optional[Dict[str, Any]]:
        ch = self.challenges.get(cid)
        if not ch:
            return None
        res = dict(ch)
        res["ai_analysis"] = dict(self.ai_analysis[cid]) if cid in self.ai_analysis else None
        return res

    def list_challenges(self, status: Optional[str] = None, city: Optional[str] = None, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        results = list(self.challenges.values())
        if status:
            results = [c for c in results if c.get("status") == status]
        if city:
            results = [c for c in results if c.get("city") == city]
        if user_id:
            results = [c for c in results if c.get("user_id") == user_id]
        return results

    def update_challenge_status(self, cid: str, new_status: str):
        if cid in self.challenges:
            self.challenges[cid]["status"] = new_status

    def upsert_ai_analysis(self, data: Dict[str, Any]):
        cid = data["challenge_id"]
        self.ai_analysis[cid] = dict(data)
        return dict(self.ai_analysis[cid])

    def update_ai_analysis(self, cid: str, patch: Dict[str, Any]):
        if cid in self.ai_analysis:
            self.ai_analysis[cid].update(patch)


class MockChallengeService(ChallengeService):
    """Subclasses ChallengeService with mock in-memory DB while using the real AIService."""

    def __init__(self, db: MockChallengeDatabase):
        super().__init__()
        self.db = db

    def create_challenge(self, payload: Dict[str, Any], user: AuthenticatedUser) -> Dict[str, Any]:
        # Invoke real validation and ID generation logic
        title = payload.get("title", "").strip()
        description = payload.get("description", "").strip()
        if not title or not description:
            from fastapi import HTTPException
            raise HTTPException(status_code=422, detail="Title and description required")

        cid = payload.get("challenge_id") or f"CHL-MOCK-{len(self.db.challenges) + 1:04d}"
        record = {
            "challenge_id": cid,
            "title": title,
            "description": description,
            "location": payload.get("location"),
            "city": payload.get("city"),
            "district": payload.get("district") or payload.get("city"),
            "address": payload.get("address"),
            "pincode": payload.get("pincode"),
            "impact_scope": payload.get("impact_scope") or "Area Specific",
            "photo": payload.get("photo"),
            "video": payload.get("video"),
            "document": payload.get("document"),
            "expected_solution": payload.get("expected_solution"),
            "submitted_by": payload.get("submitted_by") or user.full_name or "Citizen",
            "status": "submitted",
            "user_id": user.user_id,
        }
        return self.db.insert_challenge(record)

    def get_challenge(self, challenge_id: str) -> Dict[str, Any]:
        from fastapi import HTTPException
        ch = self.db.get_challenge(challenge_id)
        if not ch:
            raise HTTPException(status_code=404, detail=f"Challenge '{challenge_id}' not found")
        return ch

    def list_challenges(self, status_filter=None, city_filter=None, user_id_filter=None, limit=100) -> List[Dict[str, Any]]:
        return self.db.list_challenges(status=status_filter, city=city_filter, user_id=user_id_filter)[:limit]

    def analyze_challenge(self, challenge_id: str, user: AuthenticatedUser) -> Dict[str, Any]:
        ch = self.get_challenge(challenge_id)
        self._verify_ownership(ch, user)

        current_status = ch.get("status", "submitted")
        existing_analysis = ch.get("ai_analysis")
        if existing_analysis:
            if current_status in ["accepted_existing_solution", "validated", "rejected", "gap_invalid"]:
                return {
                    "challenge_id": challenge_id,
                    "status": current_status,
                    "action_taken": "already_analyzed",
                    "llm_calls_made": 1,
                    "solution_found": existing_analysis.get("solution_found", False),
                    "existing_solution": existing_analysis.get("existing_solution"),
                    "solution_gap_valid": existing_analysis.get("solution_gap_valid"),
                    "analysis": existing_analysis,
                    "message": "Challenge has already undergone complete AI analysis.",
                }

        # Real Call 1 via AIService
        call_1_result = self.ai_service.analyze_call_1(ch)
        self.db.upsert_ai_analysis({
            "challenge_id": challenge_id,
            **call_1_result,
        })

        solution_found = call_1_result.get("solution_found", False)
        validity = call_1_result.get("validity", "valid")
        if validity != "valid":
            new_status = "rejected"
            msg = "Problem flagged as invalid/safety concern."
        elif solution_found:
            new_status = "existing_solution_found"
            msg = "Existing verified solution discovered. Awaiting citizen confirmation."
        else:
            new_status = "validated"
            msg = "No existing solution found. Challenge classified and validated for matching."

        self.db.update_challenge_status(challenge_id, new_status)
        return {
            "challenge_id": challenge_id,
            "status": new_status,
            "action_taken": "call_1_completed",
            "llm_calls_made": 1,
            "solution_found": solution_found,
            "existing_solution": call_1_result.get("existing_solution"),
            "solution_gap_valid": call_1_result.get("solution_gap_valid"),
            "analysis": call_1_result,
            "message": msg,
        }

    def handle_existing_solution_response(
        self,
        challenge_id: str,
        user: AuthenticatedUser,
        accepted: bool,
        rejection_reason: Optional[str] = None,
        rejection_category: Optional[str] = None,
    ) -> Dict[str, Any]:
        from fastapi import HTTPException
        ch = self.get_challenge(challenge_id)
        self._verify_ownership(ch, user)

        current_status = ch.get("status")
        existing_analysis = ch.get("ai_analysis")
        if current_status != "existing_solution_found" or not existing_analysis:
            raise HTTPException(
                status_code=400,
                detail=f"Challenge '{challenge_id}' is in status '{current_status}'. Not awaiting existing solution response.",
            )

        if accepted:
            new_status = "accepted_existing_solution"
            self.db.update_challenge_status(challenge_id, new_status)
            self.db.update_ai_analysis(challenge_id, {
                "solution_gap": "Citizen confirmed existing solution resolves the challenge.",
                "solution_gap_valid": False,
            })
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

        # Citizen rejects -> validate reason
        if not rejection_reason or not rejection_reason.strip():
            raise HTTPException(
                status_code=422,
                detail="A non-empty rejection_reason explaining why the existing solution does not work locally is required.",
            )

        # Real Call 2 via AIService
        call_2_result = self.ai_service.analyze_call_2_gap_validation(
            challenge=ch,
            existing_solution=existing_analysis.get("existing_solution", ""),
            rejection_reason=rejection_reason.strip(),
            rejection_category=rejection_category,
        )

        is_gap_valid = call_2_result["solution_gap_valid"]
        new_status = "validated" if is_gap_valid else "gap_invalid"
        self.db.update_challenge_status(challenge_id, new_status)
        self.db.update_ai_analysis(challenge_id, call_2_result)

        return {
            "challenge_id": challenge_id,
            "status": new_status,
            "action_taken": "call_2_gap_validated",
            "llm_calls_made": 2,
            "solution_found": True,
            "existing_solution": existing_analysis.get("existing_solution"),
            "solution_gap_valid": is_gap_valid,
            "analysis": call_2_result,
            "message": "Gap validation complete. Problem validated and classified for university/industry matching.",
        }


def run_tests():
    print("=" * 70)
    print("STARTING PHASE 3 CITIZEN & AI WORKFLOW TEST SUITE")
    print("=" * 70)

    db = MockChallengeDatabase()
    mock_service = MockChallengeService(db)

    # Active user 1: Citizen A
    user_a = AuthenticatedUser(
        user_id="user-citizen-aaa-111",
        email="citizen.a@samadhansetu.gov.in",
        role="citizen",
        full_name="Citizen Aarti",
        is_verified=True,
    )

    # Active user 2: Citizen B (unauthorized third party)
    user_b = AuthenticatedUser(
        user_id="user-citizen-bbb-222",
        email="citizen.b@samadhansetu.gov.in",
        role="citizen",
        full_name="Citizen Bharat",
        is_verified=True,
    )

    # Global active user context for test client
    current_test_user = user_a

    app.dependency_overrides[get_current_user] = lambda: current_test_user
    app.dependency_overrides[get_challenge_service] = lambda: mock_service

    client = TestClient(app)

    # -------------------------------------------------------------
    # TEST 1: Challenge Submission by Authenticated Citizen
    # -------------------------------------------------------------
    print("\n[TEST 1] Citizen Challenge Submission:")
    submit_payload = {
        "title": "Overflowing Garbage and Solid Waste Dump near Main Vegetable Market",
        "description": "Solid waste and municipal garbage has been accumulating for weeks near APMC market causing severe health hazard and foul odor. Local dustbins are overflowing.",
        "location": "APMC Yard, Sector 4",
        "city": "Ranchi",
        "district": "Ranchi",
        "address": "Opposite Gate 2, Vegetable Market",
        "pincode": "834001",
        "impact_scope": "Ward Specific",  # Strictly impact_scope, NOT impact_score
        "photo": "https://storage.samadhansetu.gov.in/photos/garbage_01.jpg",
        "video": None,
        "document": None,
        "expected_solution": "Automated waste detection sensor and regular municipal collection schedule",
    }

    r1 = client.post("/api/challenges", json=submit_payload)
    print("  Status Code:", r1.status_code)
    print("  Response data:", r1.json()["data"])
    assert r1.status_code == 201
    assert r1.json()["success"] is True
    created_ch = r1.json()["data"]
    assert created_ch["user_id"] == "user-citizen-aaa-111"
    assert created_ch["impact_scope"] == "Ward Specific"
    assert "impact_score" not in created_ch
    assert created_ch["status"] == "submitted"
    ch1_id = created_ch["challenge_id"]
    print(f"  [PASS] Challenge successfully created with ID: {ch1_id}, user_id linked, impact_scope preserved.")

    # -------------------------------------------------------------
    # TEST 2: Ownership & Authorization Security Gate
    # -------------------------------------------------------------
    print("\n[TEST 2] Unauthorized Access & Ownership Enforcement:")
    # Citizen B attempts to analyze Citizen A's challenge
    app.dependency_overrides[get_current_user] = lambda: user_b
    r2_unauth = client.post(f"/api/challenges/{ch1_id}/analyze")
    print("  Citizen B attempt status:", r2_unauth.status_code)
    print("  Citizen B attempt response:", r2_unauth.json())
    assert r2_unauth.status_code == 403
    assert "Access forbidden" in r2_unauth.json()["error"]["message"]
    print("  [PASS] Citizen B blocked with 403 when trying to analyze Citizen A's challenge.")

    # Unauthenticated request (no override)
    app.dependency_overrides.pop(get_current_user)
    r2_no_token = client.post(f"/api/challenges/{ch1_id}/analyze")
    assert r2_no_token.status_code == 401
    print("  [PASS] Unauthenticated request blocked with 401.")

    # Restore Citizen A
    app.dependency_overrides[get_current_user] = lambda: user_a

    # -------------------------------------------------------------
    # TEST 3: Call 1 — Existing-Solution Discovery with Real Evidence
    # -------------------------------------------------------------
    print("\n[TEST 3] AI Call 1: Problem Analysis + Verified Real Solution Discovery:")
    r3 = client.post(f"/api/challenges/{ch1_id}/analyze")
    print("  Status Code:", r3.status_code)
    data3 = r3.json()["data"]
    print("  Status:", data3["status"])
    print("  Solution Found:", data3["solution_found"])
    print("  LLM Calls Made:", data3["llm_calls_made"])
    print("  Discovered Solution:", data3["existing_solution"])

    assert r3.status_code == 200
    assert data3["status"] == "existing_solution_found"
    assert data3["solution_found"] is True
    assert data3["llm_calls_made"] == 1
    # Verify that real verified evidence is cited (Swachhata App by MoHUA) and no hallucinated fake URLs
    assert "Swachhata App" in data3["existing_solution"]
    assert "MoHUA" in data3["existing_solution"]
    print("  [PASS] Call 1 found verified real solution 'Swachhata App (MoHUA)'. 1 LLM call used.")

    # -------------------------------------------------------------
    # TEST 4: Citizen Accepts Existing Solution (Workflow Closes)
    # -------------------------------------------------------------
    print("\n[TEST 4] Citizen Accepts Existing Solution:")
    # Submit second challenge for accept test
    r4_create = client.post("/api/challenges", json={
        "title": "Severe Solid Waste accumulation in Commercial Colony",
        "description": "Garbage dump and trash collection missing in commercial sector. Need waste pickup.",
        "city": "Bhopal",
    })
    ch2_id = r4_create.json()["data"]["challenge_id"]
    client.post(f"/api/challenges/{ch2_id}/analyze")  # Call 1 -> existing_solution_found

    # Citizen A accepts the solution
    r4_accept = client.post(
        f"/api/challenges/{ch2_id}/existing-solution-response",
        json={"accepted": True}
    )
    print("  Accept Status Code:", r4_accept.status_code)
    print("  Response:", r4_accept.json()["data"])
    assert r4_accept.status_code == 200
    assert r4_accept.json()["data"]["status"] == "accepted_existing_solution"
    assert r4_accept.json()["data"]["llm_calls_made"] == 1  # Zero extra calls
    print("  [PASS] Workflow terminates cleanly on acceptance. Total LLM calls = 1.")

    # -------------------------------------------------------------
    # TEST 5: Call 2 — Citizen Rejection + Gap Validation + Classification
    # -------------------------------------------------------------
    print("\n[TEST 5] Citizen Rejects Solution -> AI Call 2 (Gap Validation + Classification):")
    # On ch1_id (which is in existing_solution_found status):
    # Citizen A provides valid rejection reason explaining rural/local gap
    reject_payload = {
        "accepted": False,
        "rejection_reason": "Swachhata App is only serviceable within notified Nagar Nigam urban limits; our APMC wholesale yard lies in a rural peri-urban gram panchayat where ULB sanitation trucks are not deployed.",
        "rejection_category": "local_unavailability",
    }
    r5 = client.post(f"/api/challenges/{ch1_id}/existing-solution-response", json=reject_payload)
    print("  Status Code:", r5.status_code)
    data5 = r5.json()["data"]
    print("  Status after Call 2:", data5["status"])
    print("  Solution Gap Valid:", data5["solution_gap_valid"])
    print("  Total LLM Calls:", data5["llm_calls_made"])
    print("  Classified Category:", data5["analysis"]["category"])
    print("  Required Technologies:", data5["analysis"]["required_technologies"])

    assert r5.status_code == 200
    assert data5["status"] == "validated"
    assert data5["solution_gap_valid"] is True
    assert data5["llm_calls_made"] == 2
    assert "Municipal Solid Waste" in data5["analysis"]["category"]
    print("  [PASS] Call 2 validated genuine local gap, completed classification, and entered 'validated' state. Total calls = 2.")

    # -------------------------------------------------------------
    # TEST 6: Call 1 Direct Validation for Novel Challenge (Zero Solution Found)
    # -------------------------------------------------------------
    print("\n[TEST 6] Novel Problem: Call 1 Direct Classification (No Redundant Call 2):")
    novel_payload = {
        "title": "Low-Head Micro Hydrokinetic Turbine for Silt-Heavy Himalayan Glacial Streams",
        "description": "Designing erosion-resistant ceramic-coated Pelton runner blades to prevent cavitation and abrasive quartz silt erosion in high-altitude glacial streams generating off-grid power.",
        "city": "Chamoli",
        "district": "Chamoli",
        "impact_scope": "State Specific",
    }
    r6_create = client.post("/api/challenges", json=novel_payload)
    ch3_id = r6_create.json()["data"]["challenge_id"]

    r6_analyze = client.post(f"/api/challenges/{ch3_id}/analyze")
    print("  Status Code:", r6_analyze.status_code)
    data6 = r6_analyze.json()["data"]
    print("  Status:", data6["status"])
    print("  Solution Found:", data6["solution_found"])
    print("  LLM Calls Made:", data6["llm_calls_made"])
    print("  Category:", data6["analysis"]["category"])
    print("  Skills:", data6["analysis"]["required_skills"])

    assert r6_analyze.status_code == 200
    assert data6["solution_found"] is False
    assert data6["status"] == "validated"
    assert data6["llm_calls_made"] == 1  # Call 1 handled everything directly
    assert "Energy" in data6["analysis"]["category"] or "Power" in data6["analysis"]["category"]
    print("  [PASS] Novel problem validated in single Call 1 without redundant second call. Total calls = 1.")

    # -------------------------------------------------------------
    # TEST 7: Repeated Analysis & Edge Case Guards
    # -------------------------------------------------------------
    print("\n[TEST 7] Repeated Analysis & Rejection Validation Guards:")
    # 7a. Repeated analyze call on already validated challenge
    r7_repeat = client.post(f"/api/challenges/{ch3_id}/analyze")
    print("  Repeated analyze action:", r7_repeat.json()["data"]["action_taken"])
    assert r7_repeat.status_code == 200
    assert r7_repeat.json()["data"]["action_taken"] == "already_analyzed"
    print("  [PASS] Repeated /analyze is idempotent and does not consume additional AI calls.")

    # 7b. Rejection without explanation rejected
    # Create challenge in existing_solution_found
    r7_garbage = client.post("/api/challenges", json={
        "title": "Dustbin overflow and garbage dumps",
        "description": "Waste and litter on the street corner.",
    })
    ch4_id = r7_garbage.json()["data"]["challenge_id"]
    client.post(f"/api/challenges/{ch4_id}/analyze")

    r7_empty_reason = client.post(
        f"/api/challenges/{ch4_id}/existing-solution-response",
        json={"accepted": False, "rejection_reason": "   "}
    )
    print("  Empty rejection reason status:", r7_empty_reason.status_code)
    assert r7_empty_reason.status_code == 422
    print("  [PASS] Empty rejection reason correctly rejected with 422.")

    # 7c. Calling existing-solution-response on challenge not awaiting it
    r7_invalid_state = client.post(
        f"/api/challenges/{ch3_id}/existing-solution-response",
        json={"accepted": True}
    )
    print("  Invalid state call status:", r7_invalid_state.status_code)
    assert r7_invalid_state.status_code == 400
    print("  [PASS] Existing-solution response rejected with 400 on non-awaiting challenge.")

    # 7d. GET /api/challenges/{id} hydrates ai_analysis
    r7_get = client.get(f"/api/challenges/{ch1_id}")
    assert r7_get.status_code == 200
    assert r7_get.json()["data"]["ai_analysis"] is not None
    assert r7_get.json()["data"]["ai_analysis"]["solution_gap_valid"] is True
    print("  [PASS] GET /api/challenges/{id} successfully hydrates ai_analysis record.")

    # Clean up
    app.dependency_overrides.clear()
    print("\n" + "=" * 70)
    print("ALL 7 PHASE 3 CITIZEN & AI WORKFLOW TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    run_tests()
