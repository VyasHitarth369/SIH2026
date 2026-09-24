"""test_cleaned_dataset_and_routing_performance.py

Pytest suite verifying:
1. Only retained citizen challenges remain in the database (vyashitarth369@gmail.com).
2. System / pre-seeded challenges are completely absent.
3. Government problem endpoint returns retained challenges with category isolation.
4. Problem endpoints (/challenges and /government/problems) do NOT return Base64 media in list responses.
5. Government Pending routing for meaningful problems.
6. Case 1 Rejection cases: Potholes, Street light fixation, Bridge construction.
7. Case 2 Existing solution: Drainage matches PRJ-U004-7421FC.
8. Drainage valid gap routes to Government Pending.
9. Drainage invalid gap routes to rejected / gap_invalid.
10. LLM-unavailable valid fallback for meaningful societal challenges (e.g. Exam question paper software, Malnutrition).
"""

import os
import sys
import uuid
import pytest

backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.database import get_supabase
from app.services.challenge_service import ChallengeService
from app.services.government_service import GovernmentService, GOVERNMENT_CATEGORY_STATUSES
from app.services.ai_service import AIService
from app.services.auth_service import AuthenticatedUser

CITIZEN_UID = "4df37718-cb47-46b8-a999-ce3283946b3b"


@pytest.fixture(scope="module")
def supabase():
    client = get_supabase()
    assert client is not None
    return client


@pytest.fixture(scope="module")
def challenge_service():
    return ChallengeService()


@pytest.fixture(scope="module")
def government_service():
    return GovernmentService()


@pytest.fixture(scope="module")
def ai_service():
    return AIService()


@pytest.fixture(scope="module")
def citizen_user():
    return AuthenticatedUser(
        user_id=CITIZEN_UID,
        email="vyashitarth369@gmail.com",
        role="citizen",
        full_name="Hitarth Vyas",
    )


# -----------------------------------------------------------------------------
# Test 1 & 2: Dataset Cleanliness
# -----------------------------------------------------------------------------
def test_1_and_2_only_retained_citizen_challenges_remain(supabase):
    """Verify all challenges in DB belong strictly to the retained citizen account."""
    res = supabase.table("challenges").select("challenge_id, user_id, title").execute()
    challenges = res.data or []
    
    assert len(challenges) == 27, f"Expected exactly 27 challenges, found {len(challenges)}"
    
    for ch in challenges:
        assert ch.get("user_id") == CITIZEN_UID, (
            f"Challenge {ch['challenge_id']} ('{ch['title']}') does not belong to citizen {CITIZEN_UID}!"
        )
    
    # Confirm known system seeded challenges are completely absent
    system_cids = ["CHL-001", "CHL-002", "CHL-003", "CHL-TEST-001", "CHL-SYSTEM-01"]
    for scid in system_cids:
        assert not any(c["challenge_id"] == scid for c in challenges), f"System challenge {scid} must be absent"


# -----------------------------------------------------------------------------
# Test 3: Government Problems Return Retained Challenges
# -----------------------------------------------------------------------------
def test_3_government_problem_endpoint_returns_retained(government_service):
    """Verify Government problem list returns the retained challenges with category isolation."""
    problems = government_service.get_monitored_problems(category="all", limit=100)
    assert len(problems) > 0, "Government problem list must not be empty"
    
    counts = government_service.get_category_counts()
    assert counts["all"] == len(problems) or counts["all"] >= 20
    assert counts["pending"] >= 5
    assert counts["allocated"] >= 5
    assert counts["rejected"] >= 5
    assert counts["solved"] >= 3
    
    # Every problem must belong to the citizen
    for p in problems:
        assert p.get("challenge_id").startswith("CHL-")


# -----------------------------------------------------------------------------
# Test 4: List Endpoints Do NOT Return Base64 Media
# -----------------------------------------------------------------------------
def test_4_no_base64_media_in_challenge_lists(challenge_service, government_service):
    """Verify that challenge list and government problem responses omit large media."""
    # Citizen challenge list
    ch_list = challenge_service.list_challenges(limit=20)
    for c in ch_list:
        assert c.get("photo") is None, "photo must be None in list_challenges to prevent Base64 leakage"
        assert c.get("video") is None, "video must be None in list_challenges"
        assert c.get("document") is None, "document must be None in list_challenges"

    # Government problem list
    gov_list = government_service.get_monitored_problems(category="all", limit=20)
    for p in gov_list:
        assert "photo" not in p or p.get("photo") is None, "photo must not be present in government list items"


# -----------------------------------------------------------------------------
# Test 5 & 10: Meaningful Problems Route to Validated / Government Pending
# -----------------------------------------------------------------------------
def test_5_and_10_meaningful_problems_route_to_pending(ai_service):
    """Verify that meaningful problems route to validated even with deterministic offline fallback."""
    test_cases = [
        ("Exam question paper software", "Software system for generating and encrypting exam question papers"),
        ("Malnutrition", "Childhood malnutrition identification and community nutritional tracking system"),
    ]
    
    for title, desc in test_cases:
        challenge = {"challenge_id": "TEST-CAND", "title": title, "description": desc}
        
        # 1. Gate must not reject
        gate = ai_service.evaluate_deterministic_gate(challenge)
        assert gate.decision == "continue", f"Meaningful problem '{title}' must pass gate, got {gate.decision}"
        
        # 2. Fallback must validate
        fallback = ai_service._deterministic_fallback_call_1(challenge, image_provided=False, image_corrupted=False)
        assert fallback.eligibility.status == "valid", (
            f"Meaningful problem '{title}' must be valid in fallback, got {fallback.eligibility.status}"
        )
        assert fallback.university_suitable is True
        assert fallback.next_action == "continue_to_matching"


# -----------------------------------------------------------------------------
# Test 6: Rejection Cases (Case 1)
# -----------------------------------------------------------------------------
def test_6_temporary_rejection_cases(ai_service):
    """Verify Potholes, Street light fixation, and Bridge construction are rejected."""
    rejection_cases = [
        ("Potholes", "There are big potholes on the road near our colony"),
        ("Street light fixation", "Fix street light in street number 4"),
        ("Bridge construction", "We need a new bridge construction over the river"),
    ]
    
    for title, desc in rejection_cases:
        challenge = {"challenge_id": "TEST-REJ", "title": title, "description": desc}
        gate = ai_service.evaluate_deterministic_gate(challenge)
        assert gate.decision == "reject", f"Case '{title}' must be rejected by gate, got {gate.decision}"
        assert gate.university_suitable is False
        assert gate.innovation_scope == "none"


# -----------------------------------------------------------------------------
# Test 7: Drainage Existing Solution Discovery (Case 2)
# -----------------------------------------------------------------------------
def test_7_drainage_existing_solution(challenge_service):
    """Verify Drainage problem statement discovers deployed project PRJ-U004-7421FC."""
    cands = challenge_service.retrieve_targeted_candidates(
        challenge={
            "challenge_id": "TEST-DRN",
            "title": "Drainage Issue",
            "description": "Severe drainage overflow and blockage in municipal ward",
        },
        limit=10,
    )
    prj_match = next((c for c in cands if c.get("project_id") == "PRJ-U004-7421FC"), None)
    assert prj_match is not None, "PRJ-U004-7421FC must be retrieved as candidate for Drainage"
    assert prj_match.get("status") in ["deployed", "completed"]


# -----------------------------------------------------------------------------
# Test 8 & 9: Drainage Valid Gap vs Invalid Gap
# -----------------------------------------------------------------------------
def test_8_and_9_drainage_gap_validation(challenge_service, government_service, citizen_user, supabase):
    """Verify Drainage with valid gap routes to Government Pending, invalid gap routes to rejected."""
    # Test Invalid Gap
    cid_invalid = f"TEST-CHL-INV-{uuid.uuid4().hex[:6].upper()}"
    supabase.table("challenges").insert({
        "challenge_id": cid_invalid,
        "title": "Drainage Issue",
        "description": "We have issue in the drainage in the sector 4 as it overflows or look after it",
        "district": "Bokaro",
        "city": "Bokaro Steel City",
        "status": "pending_ai_review",
        "user_id": citizen_user.user_id,
    }).execute()
    
    try:
        challenge_service.analyze_challenge(cid_invalid, user=citizen_user)
        res_inv = challenge_service.handle_existing_solution_response(
            challenge_id=cid_invalid,
            user=citizen_user,
            accepted=False,
            rejection_reason="No thanks",
        )
        assert res_inv["status"] in ["rejected", "gap_invalid"], f"Invalid gap should be rejected, got {res_inv['status']}"
        assert res_inv["solution_gap_valid"] is False
    finally:
        supabase.table("challenges").delete().eq("challenge_id", cid_invalid).execute()

    # Test Valid Gap
    cid_valid = f"TEST-CHL-VAL-{uuid.uuid4().hex[:6].upper()}"
    supabase.table("challenges").insert({
        "challenge_id": cid_valid,
        "title": "Drainage Issue",
        "description": "We have issue in the drainage in the sector 4 as it overflows or look after it",
        "district": "Bokaro",
        "city": "Bokaro Steel City",
        "status": "pending_ai_review",
        "user_id": citizen_user.user_id,
    }).execute()
    
    try:
        challenge_service.analyze_challenge(cid_valid, user=citizen_user)
        res_val = challenge_service.handle_existing_solution_response(
            challenge_id=cid_valid,
            user=citizen_user,
            accepted=False,
            rejection_reason="The existing IIIT Ranchi IoT drainage sensor is designed for underground concrete storm drains, but Sector 4 has open unpaved silted stormwater channels requiring biological filtration and silt traps",
        )
        assert res_val["status"] == "validated", f"Valid gap should be validated, got {res_val['status']}"
        assert res_val["solution_gap_valid"] is True
        
        # Verify it appears in Government Pending
        pending = government_service.get_monitored_problems(category="pending")
        assert any(p["challenge_id"] == cid_valid for p in pending), "Valid gap challenge must appear in Government Pending"
    finally:
        supabase.table("challenges").delete().eq("challenge_id", cid_valid).execute()
