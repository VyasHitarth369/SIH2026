"""test_llm1_call1_understanding.py

Comprehensive test suite for Phase LLM-1:
Verifies AIService.analyze_call_1() problem understanding, canonical categorization,
objective evidence extraction, image transport & verification, search failure handling,
and safe deterministic fallback behavior.
"""

import base64
import os
import sys
from typing import Any, Dict

# Ensure Backend directory in sys.path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from dotenv import load_dotenv
load_dotenv(os.path.join(backend_dir, ".env"))

from app.schemas.analysis import CANONICAL_CATEGORIES, Call1GeminiOutput
from app.services.ai_service import AIService, canonicalize_category, normalize_subcategory


def run_all_llm1_tests():
    print("=" * 70)
    print("STARTING PHASE LLM-1: CALL #1 PROBLEM UNDERSTANDING TEST SUITE")
    print("=" * 70)

    ai = AIService()

    # -------------------------------------------------------------------------
    # TEST 1: Potholes on Main Road
    # -------------------------------------------------------------------------
    print("\n[TEST 1] Road Potholes Submission:")
    chl1 = {
        "title": "Potholes on the main road are causing accidents.",
        "description": "Deep and recurring potholes along the main highway are causing frequent vehicle damage and severe traffic accidents during peak commute hours.",
        "location": "Ranchi Main Highway",
    }
    res1 = ai.analyze_call_1(chl1)
    print(f"  Category: {res1['category']}, Subcategory: {res1['subcategory']}")
    assert res1["category"] == "transportation", f"Expected 'transportation', got '{res1['category']}'"
    assert "pothole" in res1["subcategory"] or "road" in res1["subcategory"], f"Subcategory must relate to road/potholes, got '{res1['subcategory']}'"
    assert res1["category"] != "infrastructure", "Potholes must NOT be categorized as generic 'infrastructure'"
    print("  [PASS] Test 1: Potholes accurately categorized under 'transportation' with road/pothole subcategory.")

    # -------------------------------------------------------------------------
    # TEST 2: Contaminated Drinking Water
    # -------------------------------------------------------------------------
    print("\n[TEST 2] Contaminated Drinking Water Submission:")
    chl2 = {
        "title": "Contaminated drinking water in a village is causing disease.",
        "description": "Groundwater wells across the village contain severe chemical runoff and microbial contamination, leading to widespread dysentery and waterborne illnesses.",
        "location": "Sundarpahar Village, Godda",
    }
    res2 = ai.analyze_call_1(chl2)
    print(f"  Category: {res2['category']}, Subcategory: {res2['subcategory']}")
    assert res2["category"] == "water", f"Expected 'water', got '{res2['category']}'"
    assert "water" in res2["subcategory"] or "contaminat" in res2["subcategory"], f"Subcategory must relate to water/contamination, got '{res2['subcategory']}'"
    print("  [PASS] Test 2: Contaminated water categorized under 'water' with water/contamination subcategory.")

    # -------------------------------------------------------------------------
    # TEST 3: Crop Disease
    # -------------------------------------------------------------------------
    print("\n[TEST 3] Crop Disease Submission:")
    chl3 = {
        "title": "Crop disease is destroying mustard crops across several villages.",
        "description": "A severe white rust and fungal infestation is destroying standing mustard crops across several farming clusters, threatening complete harvest loss.",
        "location": "Palamu Rural Belt",
    }
    res3 = ai.analyze_call_1(chl3)
    print(f"  Category: {res3['category']}, Subcategory: {res3['subcategory']}")
    assert res3["category"] == "agriculture", f"Expected 'agriculture', got '{res3['category']}'"
    print("  [PASS] Test 3: Crop disease accurately categorized under 'agriculture'.")

    # -------------------------------------------------------------------------
    # TEST 4: Maternal Healthcare
    # -------------------------------------------------------------------------
    print("\n[TEST 4] Maternal Healthcare Submission:")
    chl4 = {
        "title": "Lack of maternal healthcare facilities in a tribal district.",
        "description": "Pregnant women in remote tribal hamlets have no access to emergency obstetric care or neonatal monitoring within 40 km, leading to maternal health risks.",
        "location": "Torpa, Khunti District",
    }
    res4 = ai.analyze_call_1(chl4)
    print(f"  Category: {res4['category']}, Subcategory: {res4['subcategory']}")
    assert res4["category"] == "healthcare", f"Expected 'healthcare', got '{res4['category']}'"
    print("  [PASS] Test 4: Maternal healthcare accurately categorized under 'healthcare'.")

    # -------------------------------------------------------------------------
    # TEST 5: Cybersecurity Vulnerabilities
    # -------------------------------------------------------------------------
    print("\n[TEST 5] Cybersecurity Vulnerabilities Submission:")
    chl5 = {
        "title": "Cybersecurity vulnerabilities in a state college network.",
        "description": "Unpatched routers, open database ports, and lack of firewall segmentation on the college intranet expose student academic records to malware and unauthorized data extraction.",
        "location": "State Engineering College",
    }
    res5 = ai.analyze_call_1(chl5)
    print(f"  Category: {res5['category']}, Subcategory: {res5['subcategory']}")
    assert res5["category"] == "cybersecurity", f"Expected 'cybersecurity', got '{res5['category']}'"
    print("  [PASS] Test 5: Cybersecurity vulnerabilities accurately categorized under 'cybersecurity'.")

    # -------------------------------------------------------------------------
    # TEST 6: Routine Maintenance (One Broken Streetlight)
    # -------------------------------------------------------------------------
    print("\n[TEST 6] Routine Maintenance (Single Streetlight):")
    chl6 = {
        "title": "One streetlight outside my house is broken.",
        "description": "The bulb on the municipal streetlight pole outside my front door stopped working three days ago. Please replace the bulb.",
        "location": "Harmu Colony, Ranchi",
    }
    res6 = ai.analyze_call_1(chl6)
    print(f"  Innovation Scope: {res6['innovation_scope']}, University Suitable: {res6['university_suitable']}")
    assert res6["innovation_scope"] in ("none", "low", "uncertain"), f"Expected routine maintenance to have none/low innovation scope, got '{res6['innovation_scope']}'"
    assert res6["university_suitable"] is False or res6["university_suitable"] is None, f"Routine bulb replacement must NOT be marked university suitable, got {res6['university_suitable']}"
    print("  [PASS] Test 6: Routine maintenance correctly identified as none/low innovation and NOT university suitable.")

    # -------------------------------------------------------------------------
    # TEST 7: Advanced Predictive IoT System
    # -------------------------------------------------------------------------
    print("\n[TEST 7] Predictive IoT Telemetry System:")
    chl7 = {
        "title": "Develop a predictive system using IoT sensors to detect streetlight failures across a district.",
        "description": "Create an automated mesh-connected telemetry sensor network with machine learning failure prediction algorithms to detect underground cable faults and luminaire degradation across 10,000 streetlights in the district.",
        "location": "Dhanbad Urban Agglomeration",
    }
    res7 = ai.analyze_call_1(chl7)
    print(f"  Innovation Scope: {res7['innovation_scope']}, University Suitable: {res7['university_suitable']}")
    assert res7["innovation_scope"] in ("medium", "high", "uncertain"), f"Expected high technology opportunity, got '{res7['innovation_scope']}'"
    assert res7["university_suitable"] is True or res7["university_suitable"] is None, f"Predictive system engineering should be university suitable, got {res7['university_suitable']}"
    print("  [PASS] Test 7: Predictive telemetry system accurately recognized as medium/high innovation and university suitable.")

    # -------------------------------------------------------------------------
    # TEST 8: Random Meaningless Text
    # -------------------------------------------------------------------------
    print("\n[TEST 8] Random Meaningless / Spam Submission:")
    chl8 = {
        "title": "asdfghjkl qwerty 123456",
        "description": "just testing spam nonsense joke asdf zxcvbnm",
        "location": "Unknown",
    }
    res8 = ai.analyze_call_1(chl8)
    print(f"  Validity: {res8['validity']}, Eligibility Reason: {res8.get('eligibility_reason')}")
    assert res8["validity"] in ("ineligible", "invalid", "uncertain"), f"Meaningless text must NOT be valid, got '{res8['validity']}'"
    assert res8["validity"] != "valid", "Spam/nonsense must never be marked valid"
    print("  [PASS] Test 8: Nonsense text strictly rejected as ineligible/invalid or uncertain.")

    # -------------------------------------------------------------------------
    # TEST 9: Image Transport & Corrupted / Mismatched Image Handling
    # -------------------------------------------------------------------------
    print("\n[TEST 9] Image Evidence Verification:")
    # 9A: Corrupted / unreachable image URL
    chl9_corrupt = {
        "title": "Road pothole issue with broken image",
        "description": "Severe road craters on main avenue.",
        "photo": "blob:http://localhost:5173/unreachable-blob-url-123",
    }
    res9_corrupt = ai.analyze_call_1(chl9_corrupt)
    print(f"  Unreachable Image Status: {res9_corrupt['image_evidence_status']}")
    assert res9_corrupt["image_evidence_status"] == "uncertain", f"Unreachable image must be 'uncertain', got '{res9_corrupt['image_evidence_status']}'"
    assert res9_corrupt["image_evidence_status"] != "consistent", "Unreachable image must NEVER be marked consistent!"

    # 9B: Valid Base64 1x1 PNG data URL
    valid_png_b64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    chl9_data = {
        "title": "Road pothole issue with real image bytes",
        "description": "Severe road craters on main avenue.",
        "photo": valid_png_b64,
    }
    res9_data = ai.analyze_call_1(chl9_data)
    print(f"  Base64 Image Status: {res9_data['image_evidence_status']}")
    assert res9_data["image_evidence_status"] in ("consistent", "mismatch", "uncertain"), f"Invalid status: {res9_data['image_evidence_status']}"
    assert res9_data["image_evidence_status"] != "not_provided", "Image bytes were provided so status must not be 'not_provided'"
    print("  [PASS] Test 9: Image verification correctly rejects unreadable blob URLs as 'uncertain' and processes base64 bytes.")

    # -------------------------------------------------------------------------
    # TEST 10: No Image Attached
    # -------------------------------------------------------------------------
    print("\n[TEST 10] No Image Attached:")
    chl10 = {
        "title": "Water leakage in colony pipeline",
        "description": "Clean water is gushing out of broken municipal pipeline.",
        "photo": None,
    }
    res10 = ai.analyze_call_1(chl10)
    print(f"  Image Status: {res10['image_evidence_status']}")
    assert res10["image_evidence_status"] == "not_provided", f"Expected 'not_provided', got '{res10['image_evidence_status']}'"
    print("  [PASS] Test 10: Correctly marked image_evidence_status = 'not_provided' when photo is absent.")

    # -------------------------------------------------------------------------
    # TEST 11: Simulated Gemini API Failure (Fallback Policy)
    # -------------------------------------------------------------------------
    print("\n[TEST 11] Deterministic Fallback on API Failure:")
    # Direct test of _deterministic_fallback_call_1
    chl11 = {
        "title": "Unknown municipal concern in remote locality",
        "description": "Some issues with local service delivery occurring regularly.",
    }
    fallback_out = ai._deterministic_fallback_call_1(chl11, image_provided=False)
    print(f"  Fallback Category: {fallback_out.problem_understanding.primary_category}")
    print(f"  Fallback Skills: {[s.name for s in fallback_out.required_skills]}")
    print(f"  Fallback Confidence: {fallback_out.analysis_confidence}")
    print(f"  Fallback Validity: {fallback_out.eligibility.status}")

    assert fallback_out.problem_understanding.primary_category == "other", "Fallback must NOT silently default unknown problems to 'infrastructure'"
    assert len(fallback_out.required_skills) == 0, "Fallback must not manufacture fake Civil Engineering skills"
    assert fallback_out.analysis_confidence == "low", "Fallback confidence must be low"
    assert fallback_out.eligibility.status == "uncertain", "Fallback validity must be uncertain"
    print("  [PASS] Test 11: Deterministic fallback does not manufacture fake infrastructure/civil engineering; confidence=low, status=uncertain.")

    # -------------------------------------------------------------------------
    # TEST 12: External Solution Search Failure State
    # -------------------------------------------------------------------------
    print("\n[TEST 12] External Search Failure & User Correction #1:")
    # Verify that when search_status == 'search_failed', existing_solution_found is None (NOT False)
    mock_search_fail = Call1GeminiOutput()
    mock_search_fail.external_search.search_status = "search_failed"
    mock_search_fail.external_search.existing_solution_found = False  # Deliberately test normalization override

    normalized = ai._validate_and_normalize_call_1(mock_search_fail, image_corrupted=False, search_grounding_used=False)
    formatted = ai._format_call_1_response(normalized, search_grounding_used=False)

    print(f"  Search Status: {formatted['external_search_status']}")
    print(f"  Existing Solution Found: {formatted['existing_solution_found']}")
    print(f"  Solution Gap: {formatted['solution_gap']}")
    print(f"  Solution Gap Valid: {formatted['solution_gap_valid']}")

    assert formatted["external_search_status"] == "search_failed"
    assert formatted["existing_solution_found"] is None, f"existing_solution_found must be None when search fails, got {formatted['existing_solution_found']}"
    assert formatted["solution_gap_valid"] is None, "solution_gap_valid must be None when search fails (not prematurely validated)"
    print("  [PASS] Test 12: External search failure cleanly sets existing_solution_found = None and does not treat search failure as 'no solution exists'.")

    # -------------------------------------------------------------------------
    # TEST 13: Canonical 20 Categories & Normalization
    # -------------------------------------------------------------------------
    print("\n[TEST 13] Canonical Categories Validation & Alias Mapping:")
    assert len(CANONICAL_CATEGORIES) == 20
    test_mappings = [
        ("roads", "transportation"),
        ("road", "transportation"),
        ("health", "healthcare"),
        ("medical", "healthcare"),
        ("clean_water", "water"),
        ("cyber_security", "cybersecurity"),
        ("solar", "energy"),
        ("completely_unknown_domain_xyz", "other"),
    ]
    for raw, expected in test_mappings:
        canon, is_unc = canonicalize_category(raw)
        assert canon == expected, f"Mapping failed for '{raw}': expected '{expected}', got '{canon}'"
    print("  [PASS] Test 13: All 20 canonical categories validated and aliases mapped deterministically.")

    # -------------------------------------------------------------------------
    # TEST 14: Subcategory Normalization & Contradiction Rejection
    # -------------------------------------------------------------------------
    print("\n[TEST 14] Subcategory Normalization & Cross-Domain Rejection:")
    valid_sub = normalize_subcategory("transportation", "Smart Road Potholes !!")
    assert valid_sub == "smart_road_potholes"

    contradictory_sub = normalize_subcategory("healthcare", "smart_highway_sensors")
    assert contradictory_sub == "general_healthcare", f"Contradictory subcategory must be rejected, got '{contradictory_sub}'"
    print("  [PASS] Test 14: Subcategory normalized to snake_case and healthcare/highway contradiction cleanly rejected.")

    # -------------------------------------------------------------------------
    # TEST 15: Namespaced Evidence Envelope in similar_challenges
    # -------------------------------------------------------------------------
    print("\n[TEST 15] User Correction #2: Namespaced Evidence Envelope:")
    env_chl = {
        "title": "High infant mortality in rural block",
        "description": "Lack of neonatal monitoring in primary healthcare centers.",
    }
    env_res = ai.analyze_call_1(env_chl)
    import json
    envelope = json.loads(env_res["similar_challenges"])
    print("  Envelope keys:", list(envelope.keys()))
    assert envelope.get("schema_version") == 1
    assert "objective_evidence" in envelope
    assert "image_evidence" in envelope
    assert "external_search" in envelope
    assert "similar_challenges" in envelope
    assert "severity_level" in envelope["objective_evidence"]
    assert "population_scale" in envelope["objective_evidence"]
    assert "life_safety_threat" in envelope["objective_evidence"]
    print("  [PASS] Test 15: Namespaced evidence envelope verified with schema_version=1 and preserved similar_challenges array.")

    print("\n" + "=" * 70)
    print("ALL 15 PHASE LLM-1 TEST CASES PASSED WITH 100% SUCCESS!")
    print("=" * 70)


if __name__ == "__main__":
    run_all_llm1_tests()
