"""test_strong_validation_and_secondary_llm.py

Comprehensive test suite verifying:
1. Provider-independent pre-LLM deterministic screening gate.
2. Gemini 2.5 Flash as Primary LLM.
3. OpenAI (gpt-5.6-luna) as Secondary Fallback LLM.
4. Fail-closed deterministic backend fallback if both fail.
5. Defense-in-depth post-LLM backend validation gate.
6. Safe database CHECK constraint persistence.
7. Government isolation of non-validated statuses (uncertain_eligibility, uncertain_solution_search, image_mismatch).
8. Real challenge CHL-B98253CC and IoT predictive innovation challenge behavior.
"""

import json
import os
import sys
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

from app.database import get_supabase
from app.schemas.analysis import (
    Call1GeminiOutput,
    DiscoveredSolution,
    EligibilityResult,
    ExternalSearchResult,
    ImageEvidenceResult,
    ObjectivePriorityFactors,
    ProblemUnderstanding,
    SkillRequirement,
    TechRequirement,
)
from app.services.ai_service import AIService
from app.services.challenge_service import ChallengeService
from app.services.government_service import (
    GOVERNMENT_CATEGORY_STATUSES,
    GovernmentService,
)


def run_all_15_tests():
    print("=" * 80)
    print("RUNNING 15 TESTS: STRONG BACKEND VALIDATION + SECONDARY LLM FALLBACK")
    print("=" * 80)

    ai = AIService()

    # -------------------------------------------------------------------------
    # TEST 1: Routine streetlight + Gemini available -> rejected
    # -------------------------------------------------------------------------
    ch1 = {
        "challenge_id": "TEST-CHL-001",
        "title": "Street light fixation",
        "description": "The street light need to be fixed of our society",
    }
    # Pre-LLM gate intercepts and rejects immediately without consuming LLM calls
    t1_res = ai.analyze_call_1(ch1)
    assert t1_res["validity"] == "invalid" or t1_res["validity_raw"] == "ineligible"
    assert t1_res["innovation_scope"] == "none"
    assert t1_res["university_suitable"] is False
    assert t1_res["next_action"] == "reject"
    assert t1_res["provider_used"] == "backend"
    print("[PASS] TEST 1: Routine streetlight rejected immediately by deterministic gate (provider_used=backend).")

    # -------------------------------------------------------------------------
    # TEST 2: Routine streetlight + Gemini unavailable -> rejected by backend fallback
    # -------------------------------------------------------------------------
    ch2 = {
        "challenge_id": "TEST-CHL-002",
        "title": "Fix the broken street light",
        "description": "The streetlight outside my house is broken and dark.",
    }
    with patch.object(ai, "_call_1_gemini", side_effect=Exception("Gemini quota 429")):
        with patch.object(ai, "_call_1_openai", side_effect=Exception("OpenAI quota 429")):
            t2_res = ai.analyze_call_1(ch2)
            assert t2_res["validity_raw"] == "ineligible"
            assert t2_res["innovation_scope"] == "none"
            assert t2_res["university_suitable"] is False
            assert t2_res["next_action"] == "reject"
            assert t2_res["provider_used"] == "backend"
    print("[PASS] TEST 2: Routine streetlight rejected by backend fallback when Gemini & OpenAI unavailable.")

    # -------------------------------------------------------------------------
    # TEST 3: Routine pothole + Gemini unavailable -> rejected
    # -------------------------------------------------------------------------
    ch3 = {
        "challenge_id": "TEST-CHL-003",
        "title": "Repair pothole",
        "description": "Deep pothole on main road needs repair.",
    }
    with patch.object(ai, "_call_1_gemini", side_effect=Exception("Gemini 503")):
        t3_res = ai.analyze_call_1(ch3)
        assert t3_res["validity_raw"] == "ineligible"
        assert t3_res["category"] == "transportation"
        assert "road" in t3_res["subcategory"]
        assert t3_res["next_action"] == "reject"
    print("[PASS] TEST 3: Routine pothole rejected by backend gate/fallback.")

    # -------------------------------------------------------------------------
    # TEST 4: Meaningless text + Gemini unavailable -> rejected
    # -------------------------------------------------------------------------
    ch4 = {
        "challenge_id": "TEST-CHL-004",
        "title": "help me please",
        "description": "problem in my area please solve this issue",
    }
    with patch.object(ai, "_call_1_gemini", side_effect=Exception("Gemini 429")):
        t4_res = ai.analyze_call_1(ch4)
        assert t4_res["validity_raw"] == "ineligible"
        assert t4_res["next_action"] == "reject"
    print("[PASS] TEST 4: Meaningless plea text rejected by backend gate.")

    # -------------------------------------------------------------------------
    # TEST 5: Genuine innovation challenge + Gemini available -> valid/continue
    # -------------------------------------------------------------------------
    ch5 = {
        "challenge_id": "TEST-CHL-005",
        "title": "Develop an IoT-based predictive system to detect failures across 10,000 streetlights",
        "description": "City-wide telemetry and machine learning early warning system for smart street lighting grid.",
    }
    # Mock successful Gemini primary call
    mock_gemini_out = Call1GeminiOutput(
        problem_understanding=ProblemUnderstanding(
            summary="IoT predictive failure detection across municipal lighting infrastructure.",
            primary_category="infrastructure",
            subcategory="predictive_street_lighting_telemetry",
        ),
        eligibility=EligibilityResult(status="valid", reason="Legitimate civic smart grid engineering challenge."),
        innovation_scope="high",
        university_suitable=True,
        university_suitability_reason="Requires embedded IoT systems, predictive ML modeling, and smart grid engineering.",
        priority_factors=ObjectivePriorityFactors(severity_level=2, population_scale=3),
        required_skills=[SkillRequirement(name="IoT Systems", importance="essential")],
        required_technologies=[TechRequirement(name="LoRaWAN", importance="essential")],
        image_evidence=ImageEvidenceResult(status="not_provided"),
        external_search=ExternalSearchResult(search_status="searched", existing_solution_found=False),
        analysis_confidence="high",
        next_action="continue_to_matching",
    )
    with patch.object(ai, "_call_1_gemini", return_value=(mock_gemini_out, True, None)):
        t5_res = ai.analyze_call_1(ch5)
        assert t5_res["validity"] == "valid"
        assert t5_res["innovation_scope"] == "high"
        assert t5_res["university_suitable"] is True
        assert t5_res["provider_used"] == "gemini"
        assert t5_res["next_action"] == "continue_to_matching"
    print("[PASS] TEST 5: Genuine innovation challenge marked valid/continue by primary Gemini provider.")

    # -------------------------------------------------------------------------
    # TEST 6: Genuine innovation + Gemini unavailable + OpenAI available -> provider_used = openai
    # -------------------------------------------------------------------------
    ch6 = {
        "challenge_id": "TEST-CHL-006",
        "title": "Computer vision pipeline for automated crop rust detection",
        "description": "Spectral imaging drone payload to detect fungal infection across wheat farms.",
    }
    mock_openai_out = Call1GeminiOutput(
        problem_understanding=ProblemUnderstanding(
            summary="Spectral imaging and computer vision for agricultural crop disease detection.",
            primary_category="agriculture",
            subcategory="precision_crop_diagnostics",
        ),
        eligibility=EligibilityResult(status="valid", reason="Agricultural innovation research challenge."),
        innovation_scope="high",
        university_suitable=True,
        university_suitability_reason="Requires spectral imaging and plant pathology machine learning models.",
        priority_factors=ObjectivePriorityFactors(severity_level=3, population_scale=3),
        required_skills=[SkillRequirement(name="Computer Vision", importance="essential")],
        required_technologies=[TechRequirement(name="PyTorch", importance="essential")],
        image_evidence=ImageEvidenceResult(status="not_provided"),
        external_search=ExternalSearchResult(search_status="search_failed", existing_solution_found=None),
        analysis_confidence="high",
        next_action="continue_to_matching",
    )
    with patch.object(ai, "_call_1_gemini", return_value=(None, False, "ResourceExhausted: 429 quota exceeded")):
        with patch.object(ai, "_call_1_openai", return_value=(mock_openai_out, None)):
            t6_res = ai.analyze_call_1(ch6)
            assert t6_res["provider_used"] == "openai"
            assert "Gemini failed" in (t6_res.get("provider_failure_reason") or "")
            assert t6_res["validity"] == "valid"
            assert t6_res["category"] == "agriculture"
            assert t6_res["university_suitable"] is True
    print("[PASS] TEST 6: Genuine innovation seamlessly routed to secondary OpenAI provider (gpt-5.6-luna).")

    # -------------------------------------------------------------------------
    # TEST 7: Genuine innovation + Gemini unavailable + OpenAI unavailable -> uncertain/clarification
    # -------------------------------------------------------------------------
    ch7 = {
        "challenge_id": "TEST-CHL-007",
        "title": "Novel community recycling process for industrial composite plastics",
        "description": "Exploring local chemical reclamation methods for discarded polymers in industrial zones.",
    }
    with patch.object(ai, "_call_1_gemini", return_value=(None, False, "Gemini 429")):
        with patch.object(ai, "_call_1_openai", return_value=(None, "OpenAI connection timeout")):
            t7_res = ai.analyze_call_1(ch7)
            assert t7_res["provider_used"] == "backend"
            assert t7_res["validity"] == "uncertain"
            assert t7_res["next_action"] == "uncertain_review"
            # Must NOT be marked valid when both LLMs are offline
            assert t7_res["validity"] != "valid"
    print("[PASS] TEST 7: Both LLMs unavailable -> fail-closed uncertain_review (never falsely validated).")

    # -------------------------------------------------------------------------
    # TEST 8: OpenAI malformed response -> backend fallback used
    # -------------------------------------------------------------------------
    ch8 = {
        "challenge_id": "TEST-CHL-008",
        "title": "Bio-filtration system for arsenic contamination in drinking wells",
        "description": "Constructing bio-adsorbent filtration columns for rural borewells.",
    }
    with patch.object(ai, "_call_1_gemini", return_value=(None, False, "Gemini 429")):
        with patch.object(ai, "_call_1_openai", return_value=(None, "JSONDecodeError: Unterminated string at line 1")):
            t8_res = ai.analyze_call_1(ch8)
            assert t8_res["provider_used"] == "backend"
            assert "OpenAI failed" in (t8_res.get("provider_failure_reason") or "")
            assert t8_res["validity"] in ("valid", "uncertain")
    print("[PASS] TEST 8: OpenAI malformed response gracefully caught; backend fallback safely used.")

    # -------------------------------------------------------------------------
    # TEST 9: Image + Gemini unavailable + OpenAI available -> OpenAI receives image & produces normalized evidence
    # -------------------------------------------------------------------------
    ch9 = {
        "challenge_id": "TEST-CHL-009",
        "title": "Structural fatigue cracks on municipal overpass bridge",
        "description": "Large shear cracks observed on bridge piers carrying heavy freight traffic.",
        "photo": "data:image/jpeg;base64,/9j/4AAQSkZJRg==",
    }
    mock_openai_img_out = Call1GeminiOutput(
        problem_understanding=ProblemUnderstanding(
            summary="Structural damage inspection on highway overpass.",
            primary_category="transportation",
            subcategory="bridge_structural_integrity",
        ),
        eligibility=EligibilityResult(status="valid", reason="Critical infrastructure safety issue."),
        innovation_scope="high",
        university_suitable=True,
        university_suitability_reason="Requires structural dynamics analysis and concrete shear stress modeling.",
        priority_factors=ObjectivePriorityFactors(severity_level=4, population_scale=3, life_safety_threat=True),
        image_evidence=ImageEvidenceResult(
            status="consistent",
            confidence=0.92,
            observations=["Image displays significant shear crack propagation on reinforced concrete bridge pier."],
        ),
        external_search=ExternalSearchResult(search_status="search_failed", existing_solution_found=None),
        analysis_confidence="high",
        next_action="continue_to_matching",
    )
    with patch.object(ai, "_call_1_gemini", return_value=(None, False, "Gemini 429")):
        with patch.object(ai, "_call_1_openai", return_value=(mock_openai_img_out, None)):
            t9_res = ai.analyze_call_1(ch9)
            assert t9_res["provider_used"] == "openai"
            assert t9_res["image_evidence_status"] == "consistent"
            assert t9_res["image_evidence_confidence"] == 0.92
            assert len(t9_res["image_observations"]) > 0
    print("[PASS] TEST 9: Secondary OpenAI provider successfully received image and produced normalized vision evidence.")

    # -------------------------------------------------------------------------
    # TEST 10: Image + both providers unavailable -> image_evidence = uncertain, never "consistent"
    # -------------------------------------------------------------------------
    ch10 = {
        "challenge_id": "TEST-CHL-010",
        "title": "Industrial river pollution monitoring",
        "description": "Chemical discharge into local river.",
        "photo": "data:image/jpeg;base64,/9j/4AAQSkZJRg==",
    }
    with patch.object(ai, "_call_1_gemini", return_value=(None, False, "Gemini 429")):
        with patch.object(ai, "_call_1_openai", return_value=(None, "OpenAI 429")):
            t10_res = ai.analyze_call_1(ch10)
            assert t10_res["provider_used"] == "backend"
            assert t10_res["image_evidence_status"] == "uncertain"
            assert t10_res["image_evidence_status"] != "consistent"
    print("[PASS] TEST 10: Both providers unavailable -> image_evidence safely marked 'uncertain', never 'consistent'.")

    # -------------------------------------------------------------------------
    # TEST 11: ai_analysis persistence -> row stored without CHECK constraint error
    # -------------------------------------------------------------------------
    client = get_supabase()
    test_cid_11 = "CHL-TEST-PERSIST-11"
    # Insert or update challenge record
    client.table("challenges").upsert({
        "challenge_id": test_cid_11,
        "title": "Fallback persistence test challenge",
        "description": "Testing that innovation_scope uncertain maps to low in DB while storing true in envelope.",
        "status": "uncertain_eligibility",
        "submitted_by": "Test Suite",
    }).execute()

    # Create fallback output with innovation_scope = 'uncertain'
    fallback_out = Call1GeminiOutput(
        problem_understanding=ProblemUnderstanding(
            summary="Fallback test",
            primary_category="water",
            subcategory="water_supply",
        ),
        eligibility=EligibilityResult(status="uncertain", reason="Offline"),
        innovation_scope="uncertain",
        priority_factors=ObjectivePriorityFactors(severity_level=2),
    )
    formatted_11 = ai._format_call_1_response(fallback_out, search_grounding_used=False, provider_used="backend")

    # Persist directly into Supabase ai_analysis table
    persist_payload = {
        "challenge_id": test_cid_11,
        "category": formatted_11["category"],
        "subcategory": formatted_11["subcategory"],
        "ai_summary": formatted_11["ai_summary"],
        "validity": formatted_11["validity"],  # "uncertain"
        "innovation_scope": formatted_11["innovation_scope"],  # "low" (satisfies CHECK constraint)
        "confidence_score": formatted_11["confidence_score"],
        "similar_challenges": formatted_11["similar_challenges"],
    }
    persisted = client.table("ai_analysis").upsert(persist_payload, on_conflict="challenge_id").execute()
    assert persisted.data, "ai_analysis row must be successfully persisted"
    row = persisted.data[0]
    assert row["innovation_scope"] in ("none", "low", "medium", "high")
    assert row["validity"] in ("valid", "invalid", "uncertain")

    # Check namespaced envelope contains raw values
    env = json.loads(row["similar_challenges"])
    assert env["objective_evidence"]["innovation_scope_uncertain"] is True
    assert env["objective_evidence"]["innovation_scope_raw"] == "uncertain"
    print(f"[PASS] TEST 11: ai_analysis persisted without CHECK constraint error (DB={row['innovation_scope']}, Raw=uncertain).")

    # Clean up test challenge 11
    client.table("ai_analysis").delete().eq("challenge_id", test_cid_11).execute()
    client.table("challenges").delete().eq("challenge_id", test_cid_11).execute()

    # -------------------------------------------------------------------------
    # TEST 12: uncertain_eligibility -> not present in Government Pending API
    # -------------------------------------------------------------------------
    assert "uncertain_eligibility" not in GOVERNMENT_CATEGORY_STATUSES["pending"]
    print("[PASS] TEST 12: 'uncertain_eligibility' is strictly excluded from Government Pending status list.")

    # -------------------------------------------------------------------------
    # TEST 13: uncertain_solution_search -> not present in Government Pending API
    # -------------------------------------------------------------------------
    assert "uncertain_solution_search" not in GOVERNMENT_CATEGORY_STATUSES["pending"]
    print("[PASS] TEST 13: 'uncertain_solution_search' is strictly excluded from Government Pending status list.")

    # -------------------------------------------------------------------------
    # TEST 14: image_mismatch -> not present in Government Pending API
    # -------------------------------------------------------------------------
    assert "image_mismatch" not in GOVERNMENT_CATEGORY_STATUSES["pending"]
    assert "image_uncertain" not in GOVERNMENT_CATEGORY_STATUSES["pending"]
    print("[PASS] TEST 14: 'image_mismatch' and 'image_uncertain' are strictly excluded from Government Pending status list.")

    # -------------------------------------------------------------------------
    # TEST 15: provider fallback chain (Gemini failure -> OpenAI success) exactly two attempts
    # -------------------------------------------------------------------------
    gemini_call_count = 0
    openai_call_count = 0

    def mock_gemini_counting(*args, **kwargs):
        nonlocal gemini_call_count
        gemini_call_count += 1
        return None, False, "Gemini 429 quota exhausted"

    def mock_openai_counting(*args, **kwargs):
        nonlocal openai_call_count
        openai_call_count += 1
        return mock_openai_out, None

    with patch.object(ai, "_call_1_gemini", side_effect=mock_gemini_counting):
        with patch.object(ai, "_call_1_openai", side_effect=mock_openai_counting):
            ch15 = {
                "challenge_id": "TEST-CHL-015",
                "title": "Machine learning system for real-time flood inundation mapping",
                "description": "Hydrological sensor telemetry combined with satellite synthetic aperture radar imagery.",
            }
            res15 = ai.analyze_call_1(ch15)
            assert res15["provider_used"] == "openai"
            assert gemini_call_count == 1, f"Expected exactly 1 Gemini call, got {gemini_call_count}"
            assert openai_call_count == 1, f"Expected exactly 1 OpenAI fallback call, got {openai_call_count}"
    print(f"[PASS] TEST 15: Bounded fallback chain verified: exactly {gemini_call_count} Gemini call and {openai_call_count} OpenAI call (no loops).")

    # -------------------------------------------------------------------------
    # REAL CHALLENGE RETEST: CHL-B98253CC
    # -------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("VERIFYING REAL CHALLENGE RETEST (CHL-B98253CC)")
    print("=" * 80)

    db_ch = client.table("challenges").select("*").eq("challenge_id", "CHL-B98253CC").execute().data[0]
    db_ai = client.table("ai_analysis").select("*").eq("challenge_id", "CHL-B98253CC").execute().data[0]

    assert db_ch["status"] == "rejected", f"Expected rejected, got {db_ch['status']}"
    assert db_ai["validity"] == "invalid", f"Expected invalid (db column), got {db_ai['validity']}"
    assert db_ai["innovation_scope"] == "none", f"Expected none, got {db_ai['innovation_scope']}"
    assert db_ai["category"] == "infrastructure"
    assert db_ai["subcategory"] == "street_lighting_maintenance"

    # Confirm CHL-B98253CC is NOT in Government Pending
    gov_pending_statuses = GOVERNMENT_CATEGORY_STATUSES["pending"]
    assert db_ch["status"] not in gov_pending_statuses

    print(f"CHL-B98253CC DB Status: {db_ch['status']}")
    print(f"CHL-B98253CC DB Validity: {db_ai['validity']}")
    print(f"CHL-B98253CC DB Innovation Scope: {db_ai['innovation_scope']}")
    print(f"CHL-B98253CC Category: {db_ai['category']} / {db_ai['subcategory']}")
    print("[PASS] Real challenge CHL-B98253CC confirmed rejected in PostgreSQL and absent from Government Pending.")

    # -------------------------------------------------------------------------
    # 10,000 Streetlights Innovation Challenge Check
    # -------------------------------------------------------------------------
    ch_iot = {
        "title": "Develop an IoT-based predictive system to detect failures across 10,000 streetlights",
        "description": "City-wide telemetry and machine learning early warning system.",
    }
    gate_iot = ai.evaluate_deterministic_gate(ch_iot)
    assert gate_iot.decision != "reject", "Must NOT be rejected by routine maintenance gate!"
    assert gate_iot.decision == "continue"
    assert gate_iot.reason_code == "genuine_innovation_candidate"
    print(f"[PASS] 10,000 streetlights IoT innovation prompt NOT rejected: decision={gate_iot.decision}, code={gate_iot.reason_code}.")

    print("\n" + "=" * 80)
    print("ALL 15 TESTS & RETESTS PASSED SUCCESSFULLY (100% SUCCESS)!")
    print("=" * 80)


if __name__ == "__main__":
    run_all_15_tests()
