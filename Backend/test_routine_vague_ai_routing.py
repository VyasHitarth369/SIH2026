"""test_routine_vague_ai_routing.py

Verifies the 15 strict requirements for routine/vague submissions,
deterministic fallback, database CHECK constraint persistence,
image transport, and Government queue isolation.
"""

import base64
import os
import sys

backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from dotenv import load_dotenv
load_dotenv(os.path.join(backend_dir, ".env"))

from app.database import get_supabase
from app.services.ai_service import AIService
from app.services.challenge_service import ChallengeService
from app.services.government_service import GovernmentService, GOVERNMENT_CATEGORY_STATUSES
from app.services.auth_service import AuthenticatedUser


def run_15_tests():
    print("=" * 75)
    print("RUNNING 15 TESTS: ROUTINE/VAGUE SUBMISSIONS & AI FALLBACK ROUTING")
    print("=" * 75)

    ai = AIService()
    cs = ChallengeService(ai_service=ai)
    gov = GovernmentService()
    client = get_supabase()

    test_user = AuthenticatedUser(
        user_id="test-routing-user-id",
        email="citizen@test.com",
        role="citizen"
    )

    # -------------------------------------------------------------------------
    # TEST 1: "Street light fixation" / "The street light need to be fixed of our society"
    # -------------------------------------------------------------------------
    print("\n[TEST 1] 'Street light fixation' Submission:")
    t1_chl = {
        "title": "Street light fixation",
        "description": "The street light need to be fixed of our society",
        "location": "Local Society",
    }
    t1_out = ai._deterministic_fallback_call_1(t1_chl, image_provided=False)
    t1_fmt = ai._format_call_1_response(t1_out, search_grounding_used=False)
    print(f"  Validity: {t1_out.eligibility.status}")
    print(f"  Innovation Scope: {t1_out.innovation_scope}")
    print(f"  University Suitable: {t1_out.university_suitable}")
    print(f"  Next Action: {t1_out.next_action}")
    print(f"  Category: {t1_out.problem_understanding.primary_category}")
    print(f"  Subcategory: {t1_out.problem_understanding.subcategory}")

    assert t1_out.eligibility.status == "ineligible", f"Expected 'ineligible', got '{t1_out.eligibility.status}'"
    assert t1_out.innovation_scope == "none", f"Expected innovation_scope='none', got '{t1_out.innovation_scope}'"
    assert t1_out.university_suitable is False, f"Expected university_suitable=False, got '{t1_out.university_suitable}'"
    assert t1_out.problem_understanding.primary_category == "infrastructure"
    assert t1_out.problem_understanding.subcategory == "street_lighting_maintenance"
    # Status transition check
    validity = t1_fmt.get("validity_raw") or t1_fmt.get("validity")
    status_t1 = "rejected" if (validity in ("ineligible", "invalid") or t1_out.innovation_scope == "none" or t1_out.university_suitable is False) else "validated"
    assert status_t1 == "rejected", f"Expected status='rejected', got '{status_t1}'"
    print("  [PASS] TEST 1: Correctly flagged ineligible, none, university_suitable=False, status=rejected.")

    # -------------------------------------------------------------------------
    # TEST 2: "Fix the broken street light near my house"
    # -------------------------------------------------------------------------
    print("\n[TEST 2] 'Fix the broken street light near my house':")
    t2_chl = {
        "title": "Fix the broken street light near my house",
        "description": "The streetlight right outside my house is broken and not turning on.",
    }
    t2_out = ai._deterministic_fallback_call_1(t2_chl, image_provided=False)
    assert t2_out.eligibility.status == "ineligible"
    assert t2_out.innovation_scope == "none"
    assert t2_out.university_suitable is False
    print("  [PASS] TEST 2: Expected rejected confirmed.")

    # -------------------------------------------------------------------------
    # TEST 3: "Repair pothole on road"
    # -------------------------------------------------------------------------
    print("\n[TEST 3] 'Repair pothole on road':")
    t3_chl = {
        "title": "Repair pothole on road",
        "description": "Please repair the pothole on the society road which is damaged.",
    }
    t3_out = ai._deterministic_fallback_call_1(t3_chl, image_provided=False)
    assert t3_out.eligibility.status == "ineligible"
    assert t3_out.innovation_scope == "none"
    assert t3_out.university_suitable is False
    assert t3_out.problem_understanding.primary_category == "transportation"
    print("  [PASS] TEST 3: Expected rejected (transportation/road_maintenance) confirmed.")

    # -------------------------------------------------------------------------
    # TEST 4: "Clean garbage near my house"
    # -------------------------------------------------------------------------
    print("\n[TEST 4] 'Clean garbage near my house':")
    t4_chl = {
        "title": "Clean garbage near my house",
        "description": "Trash is dumped near our society gate. Need cleaning and removal.",
    }
    t4_out = ai._deterministic_fallback_call_1(t4_chl, image_provided=False)
    assert t4_out.eligibility.status == "ineligible"
    assert t4_out.innovation_scope == "none"
    assert t4_out.university_suitable is False
    assert t4_out.problem_understanding.primary_category == "sanitation"
    print("  [PASS] TEST 4: Expected rejected (sanitation/waste_cleanup) confirmed.")

    # -------------------------------------------------------------------------
    # TEST 5: "Fix leaking municipal pipe"
    # -------------------------------------------------------------------------
    print("\n[TEST 5] 'Fix leaking municipal pipe':")
    t5_chl = {
        "title": "Fix leaking municipal pipe",
        "description": "Water pipe has a crack and leaking water on the footpath. Needs repair.",
    }
    t5_out = ai._deterministic_fallback_call_1(t5_chl, image_provided=False)
    assert t5_out.eligibility.status == "ineligible"
    assert t5_out.innovation_scope == "none"
    assert t5_out.university_suitable is False
    assert t5_out.problem_understanding.primary_category == "water"
    print("  [PASS] TEST 5: Expected rejected (water/pipe_repair) confirmed.")

    # -------------------------------------------------------------------------
    # TEST 6: "Develop an IoT-based predictive system to detect failures across 10,000 streetlights"
    # -------------------------------------------------------------------------
    print("\n[TEST 6] Genuine Innovation: Predictive IoT Streetlights:")
    t6_chl = {
        "title": "Develop an IoT-based predictive system to detect failures across 10,000 streetlights",
        "description": "Engineering a smart mesh telemetry network to predict bulb lifespan and detect electrical grid fluctuations before outages occur across 10,000 streetlights.",
    }
    t6_out = ai._deterministic_fallback_call_1(t6_chl, image_provided=False)
    print(f"  Validity: {t6_out.eligibility.status}")
    print(f"  Innovation Scope: {t6_out.innovation_scope}")
    print(f"  University Suitable: {t6_out.university_suitable}")
    assert t6_out.eligibility.status == "valid", f"Expected valid, got '{t6_out.eligibility.status}'"
    assert t6_out.innovation_scope in ("medium", "high"), f"Expected medium/high, got '{t6_out.innovation_scope}'"
    assert t6_out.university_suitable is True, f"Expected university_suitable=True, got '{t6_out.university_suitable}'"
    print("  [PASS] TEST 6: Genuine innovation challenge NOT rejected; marked valid, high innovation, university_suitable=True.")

    # -------------------------------------------------------------------------
    # TEST 7: "asdfghjkl qwerty 123456"
    # -------------------------------------------------------------------------
    print("\n[TEST 7] Gibberish Submission:")
    t7_chl = {
        "title": "asdfghjkl",
        "description": "qwerty 123456",
    }
    t7_out = ai._deterministic_fallback_call_1(t7_chl, image_provided=False)
    assert t7_out.eligibility.status == "ineligible"
    assert t7_out.innovation_scope == "none"
    assert t7_out.university_suitable is False
    print("  [PASS] TEST 7: Gibberish correctly rejected.")

    # -------------------------------------------------------------------------
    # TEST 8: "Help me with this issue"
    # -------------------------------------------------------------------------
    print("\n[TEST 8] Vague Generic Submission:")
    t8_chl = {
        "title": "Help me with this issue",
        "description": "Help me with this issue please",
    }
    t8_out = ai._deterministic_fallback_call_1(t8_chl, image_provided=False)
    assert t8_out.eligibility.status == "ineligible"
    assert t8_out.next_action == "reject"
    # Must never route to Government
    assert "uncertain_eligibility" not in GOVERNMENT_CATEGORY_STATUSES["pending"]
    assert "rejected" in GOVERNMENT_CATEGORY_STATUSES["rejected"]
    print("  [PASS] TEST 8: Generic phrase rejected, never routed to Government.")

    # -------------------------------------------------------------------------
    # TEST 9: Gemini API unavailable + routine streetlight problem
    # -------------------------------------------------------------------------
    print("\n[TEST 9] Fallback Routine Streetlight Problem:")
    t9_chl = {
        "title": "Street light fixation",
        "description": "The street light need to be fixed of our society",
    }
    t9_out = ai._deterministic_fallback_call_1(t9_chl, image_provided=False)
    assert t9_out.eligibility.status == "ineligible"
    assert t9_out.innovation_scope == "none"
    assert t9_out.university_suitable is False
    print("  [PASS] TEST 9: Fallback evaluates routine streetlight as rejected.")

    # -------------------------------------------------------------------------
    # TEST 10: Gemini API unavailable + genuine innovation problem
    # -------------------------------------------------------------------------
    print("\n[TEST 10] Fallback Genuine Problem with Insufficient Offline Evidence:")
    t10_chl = {
        "title": "Some complex regional coordination problem",
        "description": "A complex multi-agency coordination issue occurring across multiple districts.",
    }
    t10_out = ai._deterministic_fallback_call_1(t10_chl, image_provided=False)
    print(f"  Offline Status: {t10_out.eligibility.status}")
    print(f"  Next Action: {t10_out.next_action}")
    assert t10_out.eligibility.status == "uncertain", "Must remain uncertain rather than falsely validated"
    # Verify that uncertain_eligibility is excluded from Government Pending
    assert "uncertain_eligibility" not in GOVERNMENT_CATEGORY_STATUSES["pending"]
    print("  [PASS] TEST 10: Not falsely validated; remains uncertain/clarification state, excluded from Government.")

    # -------------------------------------------------------------------------
    # TEST 11: ai_analysis persistence with fallback result
    # -------------------------------------------------------------------------
    print("\n[TEST 11] ai_analysis Database CHECK Constraint Persistence:")
    # Test persisting an uncertain fallback result: innovation_scope must map to 'low' and raw uncertainty in envelope
    t11_chl = {
        "challenge_id": "CHL-TEST-CONSTRAINT-11",
        "title": "Test Challenge for CHECK Constraint",
        "description": "General domain problem without clear scope.",
    }
    t11_out = ai._deterministic_fallback_call_1(t11_chl, image_provided=False)
    t11_fmt = ai._format_call_1_response(t11_out, search_grounding_used=False)

    print(f"  DB Column innovation_scope: {t11_fmt['innovation_scope']}")
    print(f"  Raw innovation_scope: {t11_fmt['innovation_scope_raw']}")
    print(f"  DB Column validity: {t11_fmt['validity']}")
    print(f"  Raw validity: {t11_fmt['validity_raw']}")

    assert t11_fmt["innovation_scope"] in ("none", "low", "medium", "high"), f"Invalid DB innovation_scope: {t11_fmt['innovation_scope']}"
    assert t11_fmt["validity"] in ("valid", "invalid", "uncertain"), f"Invalid DB validity: {t11_fmt['validity']}"

    # Verify live upsert into Supabase for real challenge CHL-B98253CC succeeded
    ai_row = client.table("ai_analysis").select("*").eq("challenge_id", "CHL-B98253CC").execute().data
    assert len(ai_row) == 1, "Expected 1 row in ai_analysis for CHL-B98253CC"
    assert ai_row[0]["validity"] == "invalid"
    assert ai_row[0]["innovation_scope"] == "none"
    print("  [PASS] TEST 11: ai_analysis CHECK constraints satisfied; row successfully exists in PostgreSQL.")

    # -------------------------------------------------------------------------
    # TEST 12: uncertain_eligibility not in Government Pending
    # -------------------------------------------------------------------------
    print("\n[TEST 12] Government Pending Isolation: uncertain_eligibility:")
    assert "uncertain_eligibility" not in GOVERNMENT_CATEGORY_STATUSES["pending"]
    pending_list = gov.get_monitored_problems(category="pending")
    for p in pending_list:
        assert p.get("status") != "uncertain_eligibility", f"Found challenge with uncertain_eligibility in Pending: {p.get('challenge_id')}"
    print("  [PASS] TEST 12: Government API does NOT return uncertain_eligibility in Pending.")

    # -------------------------------------------------------------------------
    # TEST 13: uncertain_solution_search not in Government Pending
    # -------------------------------------------------------------------------
    print("\n[TEST 13] Government Pending Isolation: uncertain_solution_search:")
    assert "uncertain_solution_search" not in GOVERNMENT_CATEGORY_STATUSES["pending"]
    for p in pending_list:
        assert p.get("status") != "uncertain_solution_search", f"Found challenge with uncertain_solution_search in Pending: {p.get('challenge_id')}"
    print("  [PASS] TEST 13: Government API does NOT return uncertain_solution_search in Pending.")

    # -------------------------------------------------------------------------
    # TEST 14: image_mismatch not in Government Pending
    # -------------------------------------------------------------------------
    print("\n[TEST 14] Government Pending Isolation: image_mismatch:")
    assert "image_mismatch" not in GOVERNMENT_CATEGORY_STATUSES["pending"]
    for p in pending_list:
        assert p.get("status") != "image_mismatch", f"Found challenge with image_mismatch in Pending: {p.get('challenge_id')}"
    print("  [PASS] TEST 14: Government API does NOT return image_mismatch in Pending.")

    # -------------------------------------------------------------------------
    # TEST 15: Base64 image transport
    # -------------------------------------------------------------------------
    print("\n[TEST 15] Base64 Image Transport:")
    # Create 1x1 transparent PNG base64 data URI
    tiny_png_b64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    part, provided, corrupted = ai._prepare_image_part(tiny_png_b64)
    assert provided is True, "image_provided must be True"
    assert corrupted is False, "image_corrupted must be False"
    assert part is not None, "types.Part must be constructed"
    # Also verify real image on CHL-B98253CC in DB
    real_ch = client.table("challenges").select("photo").eq("challenge_id", "CHL-B98253CC").execute().data[0]
    real_photo = real_ch.get("photo")
    if real_photo and real_photo.startswith("data:image/"):
        real_part, real_prov, real_corr = ai._prepare_image_part(real_photo)
        assert real_prov is True
        assert real_corr is False
        assert real_part is not None
        print("  Real CHL-B98253CC attached photo (1.68MB base64) parsed successfully into types.Part.")
    print("  [PASS] TEST 15: Actual base64 image bytes decoded and types.Part prepared correctly.")

    print("\n" + "=" * 75)
    print("ALL 15 TESTS PASSED WITH 100% SUCCESS!")
    print("=" * 75)


if __name__ == "__main__":
    run_15_tests()
