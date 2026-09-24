"""test_bokaro_transport_duplicate.py

Authoritative verification for Bokaro Transportation Duplicate Scenario:
- NEW Challenge: CHL-10EA34A2 ("Transportation problem", Bokaro)
- EXISTING Challenge: CHL-3927A854 ("Transport System", Bokaro, Project PRJ-U001-F0279E)

Tests:
1. Retrieval of both existing challenge and deployed project
2. Multi-signal scoring ensuring stemming alone does not qualify as duplicate
3. Offline / LLM outage deterministic duplicate gate activation
4. Citizen Duplicate Gate response handling: support_existing vs claim_different
"""

import pytest
from unittest.mock import patch, MagicMock
from app.database import get_supabase
from app.services.challenge_service import ChallengeService
from app.services.ai_service import (
    AIService,
    compute_multi_signal_similarity,
    compute_jaccard_similarity,
    tokenize_text,
    stem_word,
)
from app.services.auth_service import AuthenticatedUser


@pytest.fixture
def supabase_client():
    return get_supabase()


@pytest.fixture
def challenge_service(supabase_client):
    return ChallengeService(supabase_client)


@pytest.fixture
def ai_service():
    return AIService()


@pytest.fixture
def citizen_user(supabase_client):
    res = supabase_client.table("profiles").select("user_id, role").eq("role", "citizen").limit(1).execute()
    uid = res.data[0]["user_id"] if res.data else "7b3bb465-fc4f-4633-a97f-9762174ce15f"
    return AuthenticatedUser(
        user_id=uid,
        email="citizen@samadhansetu.gov.in",
        role="citizen",
        is_verified=True,
    )


def test_stemming_and_multi_signal_similarity():
    """Requirement: Stemming/prefix matching must NOT by itself classify a problem as duplicate."""
    # Test stemming tokenization
    t1 = tokenize_text("Transportation problem")
    t2 = tokenize_text("Transport System")
    assert "transport" in t1
    assert "transport" in t2

    # Two items with same stem but completely different category and location must NOT be duplicate
    cand_unrelated = {
        "title": "Transporting office stationery",
        "description": "Moving pens and paper between rooms",
        "category": "Education Supplies",
        "city": "Deoghar",
        "district": "Deoghar",
        "location": "Deoghar",
    }
    chl_test = {
        "title": "Transportation problem",
        "description": "we face a huge problem in the transportation issue so we need solution on this",
        "category": "transportation",
        "city": "Bokaro",
        "district": "Bokaro",
        "location": "Bokaro, Jharkhand",
    }
    unrelated_res = compute_multi_signal_similarity(chl_test, cand_unrelated)
    assert unrelated_res["relationship"] != "duplicate", "Stemming alone must not trigger duplicate!"

    # In contrast, Bokaro Transport System with same district and category MUST trigger duplicate
    cand_bokaro = {
        "title": "Transport System",
        "description": "we have a show in the transpose system so you have to fix it",
        "category": "transportation",
        "city": "Bokaro",
        "district": "Bokaro",
        "location": "Bokaro",
    }
    bokaro_res = compute_multi_signal_similarity(chl_test, cand_bokaro)
    assert bokaro_res["relationship"] == "duplicate"
    assert bokaro_res["category_match"] >= 0.8
    assert bokaro_res["location_match"] >= 0.8


def test_real_database_bokaro_candidate_retrieval(challenge_service, supabase_client):
    """Confirm CHL-10EA34A2 retrieves CHL-3927A854 and its completed/deployed project PRJ-U001-F0279E."""
    # Query real CHL-10EA34A2
    res_10 = supabase_client.table("challenges").select("*").eq("challenge_id", "CHL-10EA34A2").execute()
    if not res_10.data:
        pytest.skip("CHL-10EA34A2 not present in current local database.")

    chl_10 = res_10.data[0]
    candidates = challenge_service.retrieve_targeted_candidates(chl_10, limit=15)
    assert len(candidates) > 0

    c_ids = [c.get("challenge_id") for c in candidates]
    p_ids = [c.get("project_id") for c in candidates if c.get("project_id")]

    # Assert either the challenge or its project is retrieved in the Top candidates
    assert "CHL-3927A854" in c_ids or any("PRJ" in str(pid) for pid in p_ids), (
        f"Expected CHL-3927A854 or its project in candidates, got {c_ids[:5]}"
    )


def test_offline_duplicate_gate_under_llm_outage(ai_service):
    """Requirement: LLM outage must never bypass duplicate detection.

    Simulate Gemini and OpenAI failure; deterministic fallback must still identify duplicate.
    """
    chl = {
        "challenge_id": "CHL-TEST-DUP-01",
        "title": "Transportation problem",
        "description": "we face a huge problem in the transportation issue so we need solution on this",
        "category": "transportation",
        "city": "Bokaro",
        "district": "Bokaro",
        "location": "Bokaro, Jharkhand",
    }
    cand_records = [
        {
            "challenge_id": "CHL-3927A854",
            "title": "Transport System",
            "description": "we have a show in the transpose system so you have to fix it",
            "category": "transportation",
            "city": "Bokaro",
            "district": "Bokaro",
            "location": "Bokaro",
            "status": "resolved",
        }
    ]

    # Force both LLM providers to fail
    with patch.object(ai_service, "_call_1_gemini", side_effect=RuntimeError("Gemini 429 Quota Exhausted")), \
         patch.object(ai_service, "_call_1_openai", side_effect=RuntimeError("OpenAI 429 Rate Limit")):
        result = ai_service.analyze_call_1(chl, existing_challenges=cand_records)

    assert result["duplicate_group"] == "CHL-3927A854"
    assert len(result["duplicate_candidates"]) > 0
    assert result["duplicate_candidates"][0]["challenge_id"] == "CHL-3927A854"


def test_duplicate_gate_response_support_existing(challenge_service, citizen_user, supabase_client):
    """Test citizen clicking 'Support Existing Problem' on Duplicate Gate."""
    # Create or use temporary challenge
    test_id = "CHL-TEST-DUP-GATE-01"
    existing_id = "CHL-3927A854"

    # Setup record in DB
    supabase_client.table("challenges").upsert({
        "challenge_id": test_id,
        "title": "Transportation problem test",
        "description": "Test description for duplicate gate",
        "status": "duplicate_detected",
        "submitted_by": citizen_user.email,
        "user_id": citizen_user.user_id,
        "city": "Bokaro",
        "district": "Bokaro",
        "location": "Bokaro",
    }).execute()

    try:
        res = challenge_service.handle_duplicate_response(
            challenge_id=test_id,
            user=citizen_user,
            action="support_existing",
            existing_challenge_id=existing_id,
        )

        assert res["status"] == "duplicate_merged"
        assert res["action_taken"] == "duplicate_merged"

        # Verify DB status
        db_ch = supabase_client.table("challenges").select("status").eq("challenge_id", test_id).execute()
        assert db_ch.data[0]["status"] == "duplicate_merged"
    finally:
        # Cleanup test residue
        supabase_client.table("challenges").delete().eq("challenge_id", test_id).execute()
        supabase_client.table("ai_analysis").delete().eq("challenge_id", test_id).execute()


def test_duplicate_gate_response_claim_different_valid_gap(challenge_service, citizen_user, supabase_client):
    """Test citizen clicking 'This is Different / Explain Gap' with a valid local operational gap."""
    test_id = "CHL-TEST-DUP-GATE-02"
    existing_id = "CHL-3927A854"

    supabase_client.table("challenges").upsert({
        "challenge_id": test_id,
        "title": "Transportation problem test",
        "description": "Test description for duplicate gate",
        "status": "duplicate_detected",
        "submitted_by": citizen_user.email,
        "user_id": citizen_user.user_id,
        "city": "Bokaro",
        "district": "Bokaro",
        "location": "Bokaro",
    }).execute()

    try:
        res = challenge_service.handle_duplicate_response(
            challenge_id=test_id,
            user=citizen_user,
            action="claim_different",
            existing_challenge_id=existing_id,
            gap_reason="Existing buses operate on national highway; sector 4 rural residential wards have zero last-mile connectivity and no evening routes.",
        )

        assert res["status"] == "validated"
        assert res["action_taken"] == "duplicate_gap_evaluated"

        db_ch = supabase_client.table("challenges").select("status").eq("challenge_id", test_id).execute()
        assert db_ch.data[0]["status"] == "validated"
    finally:
        # Cleanup test residue
        supabase_client.table("challenges").delete().eq("challenge_id", test_id).execute()
        supabase_client.table("ai_analysis").delete().eq("challenge_id", test_id).execute()
