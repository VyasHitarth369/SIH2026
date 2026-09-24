"""test_drainage_existing_solution_workflow.py

Live end-to-end verification of the VidySetu Existing Solution Decision Workflow
for the "Drainage Issue" demo scenario:
1. Deterministic offline candidate discovery for "Drainage Issue" in Sector 4.
2. Verification that PRJ-U004-7421FC is discovered with milestones and project details.
3. Verification that existing_solution_found takes precedence over duplicate_detected.
4. Option A (Accept): transitions status to 'accepted_existing_solution'.
5. Option B (Reject / Different):
   - Invalid gap -> transitions status to 'gap_invalid'.
   - Valid gap -> transitions status to 'validated' and appears in Government Pending list.
6. Cleans up all test challenges from live Supabase DB upon completion.
"""

import os
import sys
import uuid
import pytest

backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from dotenv import load_dotenv
load_dotenv(os.path.join(backend_dir, ".env"))

from app.database import get_supabase
from app.services.challenge_service import ChallengeService
from app.services.government_service import GovernmentService
from app.services.auth_service import AuthenticatedUser


@pytest.fixture(scope="module")
def supabase():
    client = get_supabase()
    assert client is not None, "Supabase client must be available"
    return client


@pytest.fixture(scope="module")
def challenge_service():
    return ChallengeService()


@pytest.fixture(scope="module")
def government_service():
    return GovernmentService()


@pytest.fixture(scope="module")
def test_user(supabase):
    p_data = supabase.table("profiles").select("user_id, role").limit(1).execute().data
    uid = p_data[0]["user_id"] if p_data else "7b3bb465-fc4f-4633-a97f-9762174ce15f"
    return AuthenticatedUser(
        user_id=uid,
        email="citizen@test.com",
        role="citizen",
    )


@pytest.fixture
def clean_challenge(supabase, test_user):
    created_ids = []

    def _create(title: str, description: str, district: str = "Bokaro", city: str = "Bokaro Steel City"):
        cid = f"TEST-CHL-{uuid.uuid4().hex[:8].upper()}"
        res = supabase.table("challenges").insert({
            "challenge_id": cid,
            "title": title,
            "description": description,
            "district": district,
            "city": city,
            "status": "pending_ai_review",
            "user_id": test_user.user_id,
        }).execute()
        assert res.data, f"Failed to insert test challenge {cid}"
        created_ids.append(cid)
        return cid

    yield _create

    # Teardown
    for cid in created_ids:
        try:
            supabase.table("challenges").delete().eq("challenge_id", cid).execute()
        except Exception as e:
            print(f"Error cleaning up challenge {cid}: {e}")


def test_offline_drainage_candidate_retrieval(challenge_service):
    """Test targeted candidate retrieval finds PRJ-U004-7421FC with milestones."""
    cands = challenge_service.retrieve_targeted_candidates(
        challenge={
            "challenge_id": "TEST-CAND",
            "title": "Drainage Issue",
            "description": "We have issue in the drainage in the sector 4 as it overflows or look after it",
            "district": "Bokaro",
            "city": "Bokaro Steel City",
        },
        limit=10,
    )
    assert len(cands) > 0, "Should retrieve at least one candidate for drainage"
    
    prj_cand = next((c for c in cands if c.get("project_id") == "PRJ-U004-7421FC"), None)
    assert prj_cand is not None, "PRJ-U004-7421FC must be in retrieved candidates"
    assert prj_cand.get("source") == "vidysetu_project"
    assert prj_cand.get("status") in ["deployed", "completed"]
    assert prj_cand.get("university_name") is not None
    assert isinstance(prj_cand.get("milestones"), list)
    assert len(prj_cand.get("milestones")) > 0, "PRJ-U004-7421FC milestones must be hydrated"


def test_analyze_drainage_precedence_and_details(challenge_service, clean_challenge, test_user):
    """Test analyze_challenge discovers existing solution and prioritizes over duplicate group."""
    cid = clean_challenge(
        title="Drainage Issue",
        description="We have issue in the drainage in the sector 4 as it overflows or look after it",
    )
    
    result = challenge_service.analyze_challenge(cid, user=test_user)
    assert result is not None
    assert result.get("status") == "existing_solution_found", f"Expected existing_solution_found, got {result.get('status')}"
    assert result.get("existing_solution_found") is True
    
    internal_sols = result.get("internal_solutions", [])
    assert len(internal_sols) >= 1, "Must contain at least 1 internal solution"
    
    primary = internal_sols[0]
    assert primary.get("project_id") == "PRJ-U004-7421FC"
    assert primary.get("university_name") is not None
    assert primary.get("project_status") in ["deployed", "completed"]
    assert len(primary.get("milestones", [])) > 0, "Milestones must be included in internal solution"


def test_option_a_accept_existing_solution(challenge_service, clean_challenge, supabase, test_user):
    """Test Option A: citizen accepts existing solution -> status becomes accepted_existing_solution."""
    cid = clean_challenge(
        title="Drainage Issue",
        description="We have issue in the drainage in the sector 4 as it overflows or look after it",
    )
    challenge_service.analyze_challenge(cid, user=test_user)
    
    res = challenge_service.handle_existing_solution_response(
        challenge_id=cid,
        user=test_user,
        accepted=True,
    )
    assert res.get("status") == "accepted_existing_solution"
    assert res.get("action_taken") == "solution_accepted"
    
    # Verify in DB
    db_row = supabase.table("challenges").select("status").eq("challenge_id", cid).single().execute().data
    assert db_row["status"] == "accepted_existing_solution"
    ai_row = supabase.table("ai_analysis").select("solution_gap").eq("challenge_id", cid).single().execute().data
    assert ai_row is not None


def test_option_b_reject_with_invalid_gap(challenge_service, clean_challenge, supabase, test_user):
    """Test Option B: citizen rejects with invalid/trivial reason -> status becomes gap_invalid or gap_uncertain."""
    cid = clean_challenge(
        title="Drainage Issue",
        description="We have issue in the drainage in the sector 4 as it overflows or look after it",
    )
    challenge_service.analyze_challenge(cid, user=test_user)
    
    res = challenge_service.handle_existing_solution_response(
        challenge_id=cid,
        user=test_user,
        accepted=False,
        rejection_reason="No thanks",
    )
    assert res.get("status") in ["gap_invalid", "gap_uncertain"]
    assert res.get("solution_gap_valid") is False
    
    # Verify in DB
    db_row = supabase.table("challenges").select("status").eq("challenge_id", cid).single().execute().data
    assert db_row["status"] in ["gap_invalid", "gap_uncertain"]


def test_option_b_reject_with_valid_gap_routes_to_government(challenge_service, government_service, clean_challenge, supabase, test_user):
    """Test Option B: citizen rejects with genuine technical/geographic difference -> status becomes validated and is in Government Pending list."""
    cid = clean_challenge(
        title="Drainage Issue",
        description="We have issue in the drainage in the sector 4 as it overflows or look after it",
    )
    challenge_service.analyze_challenge(cid, user=test_user)
    
    res = challenge_service.handle_existing_solution_response(
        challenge_id=cid,
        user=test_user,
        accepted=False,
        rejection_reason="The existing IIIT Ranchi IoT drainage sensor is designed for underground concrete storm drains, but Sector 4 has open unpaved silted stormwater channels requiring biological filtration and silt traps",
    )
    assert res.get("status") == "validated"
    assert res.get("solution_gap_valid") is True
    
    # Verify in DB
    db_row = supabase.table("challenges").select("status").eq("challenge_id", cid).single().execute().data
    assert db_row["status"] == "validated"
    
    # Verify Government Pending list includes this challenge
    pending_challenges = government_service.get_monitored_problems(category="pending")
    found = any(c.get("challenge_id") == cid for c in pending_challenges)
    assert found is True, f"Challenge {cid} with status validated must appear in Government pending list"
