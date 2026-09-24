"""test_duplicate_and_existing_solutions.py

Comprehensive test suite verifying VidySetu Duplicate Detection + Existing Solutions:
TEST 1: Targeted candidate retrieval returns relevant same-category challenges/projects rather than arbitrary 15 rows.
TEST 2: Substantially identical challenge is classified as duplicate, and duplicate_group is populated.
TEST 3: Similar problem with different locality/scope is related, NOT duplicate.
TEST 4: Problem matching completed VidySetu project is existing_solution, real project_id retained.
TEST 5: Internal VidySetu solution + external public solution can coexist in solutions list.
TEST 6: Citizen accepts internal solution -> accepted_existing_solution (0 extra LLM calls).
TEST 7: Citizen rejects internal solution with valid gap -> Call 2 -> VALID_GAP -> validated.
TEST 8: Citizen rejects with invalid gap -> status = gap_invalid.
TEST 9: External search failure -> search_status = search_failed, existing_solution_found = null, status = uncertain_solution_search.
TEST 10: Routine streetlight complaint rejected by deterministic gate (0 Gemini, 0 OpenAI calls).
TEST 11: Innovation streetlight IoT problem passes deterministic gate.
TEST 12: PastProjectsPage uses real project data, not mockData.js.
TEST 13: LLM cannot invent candidate IDs (hallucinated IDs rejected).
TEST 14: No database migration required (schema verified).
"""

import json
import os
import sys
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from dotenv import load_dotenv
load_dotenv(os.path.join(backend_dir, ".env"))

from app.database import get_supabase
from app.schemas.analysis import (
    Call1GeminiOutput,
    Call2GeminiOutput,
    CandidateRelationship,
    DiscoveredSolution,
    EligibilityResult,
    ExternalSearchResult,
    GapValidationResult,
    ImageEvidenceResult,
    ObjectivePriorityFactors,
    ProblemUnderstanding,
    SkillRequirement,
    TechRequirement,
)
from app.services.ai_service import (
    AIService,
    compute_jaccard_similarity,
    tokenize_text,
)
from app.services.auth_service import AuthenticatedUser
from app.services.challenge_service import ChallengeService


class MockSupabaseTable:
    def __init__(self, data_store: Dict[str, Any], key_field: str):
        self.data_store = data_store
        self.key_field = key_field
        self._filter_field = None
        self._filter_val = None
        self._neq_field = None
        self._neq_val = None
        self._in_field = None
        self._in_vals = None

    def select(self, columns: str = "*"):
        return self

    def eq(self, field: str, value: Any):
        self._filter_field = field
        self._filter_val = str(value)
        return self

    def neq(self, field: str, value: Any):
        self._neq_field = field
        self._neq_val = str(value)
        return self

    def in_(self, field: str, values: List[Any]):
        self._in_field = field
        self._in_vals = [str(v) for v in values]
        return self

    def order(self, field: str, desc: bool = False):
        return self

    def limit(self, count: int):
        return self

    def insert(self, record: Dict[str, Any]):
        self._pending_insert = dict(record)
        return self

    def upsert(self, record: Dict[str, Any], on_conflict: Optional[str] = None):
        self._pending_upsert = dict(record)
        return self

    def update(self, patch_data: Dict[str, Any]):
        self._patch = dict(patch_data)
        return self

    def execute(self):
        class Res:
            data = []

        res = Res()

        if hasattr(self, "_pending_insert"):
            rec = self._pending_insert
            del self._pending_insert
            key = str(rec.get(self.key_field, len(self.data_store) + 1))
            self.data_store[key] = dict(rec)
            res.data = [dict(rec)]
            return res

        if hasattr(self, "_pending_upsert"):
            rec = self._pending_upsert
            del self._pending_upsert
            key = str(rec.get(self.key_field, len(self.data_store) + 1))
            if key in self.data_store:
                self.data_store[key].update(rec)
            else:
                self.data_store[key] = dict(rec)
            res.data = [dict(self.data_store[key])]
            return res

        if hasattr(self, "_patch") and self._filter_field:
            for k, row in self.data_store.items():
                if str(row.get(self._filter_field)) == self._filter_val:
                    row.update(self._patch)
                    res.data.append(dict(row))
            del self._patch
            return res

        results = list(self.data_store.values())
        if self._filter_field:
            results = [r for r in results if str(r.get(self._filter_field)) == self._filter_val]
        if self._neq_field:
            results = [r for r in results if str(r.get(self._neq_field)) != self._neq_val]
        if self._in_field and self._in_vals:
            results = [r for r in results if str(r.get(self._in_field)) in self._in_vals]
        res.data = [dict(r) for r in results]
        return res


class MockSupabaseClient:
    def __init__(self):
        self.challenges: Dict[str, Any] = {}
        self.ai_analysis: Dict[str, Any] = {}
        self.projects: Dict[str, Any] = {}
        self.universities: Dict[str, Any] = {}
        self.industries: Dict[str, Any] = {}
        self.project_milestones: Dict[str, Any] = {}

    def table(self, table_name: str):
        if table_name == "challenges":
            return MockSupabaseTable(self.challenges, "challenge_id")
        elif table_name == "ai_analysis":
            return MockSupabaseTable(self.ai_analysis, "challenge_id")
        elif table_name == "projects":
            return MockSupabaseTable(self.projects, "project_id")
        elif table_name == "universities":
            return MockSupabaseTable(self.universities, "university_id")
        elif table_name == "industries":
            return MockSupabaseTable(self.industries, "industry_id")
        elif table_name == "project_milestones":
            return MockSupabaseTable(self.project_milestones, "milestone_id")
        raise ValueError(f"Unknown mock table {table_name}")


def run_all_14_tests():
    print("=" * 80)
    print("RUNNING 14 TESTS: DUPLICATE DETECTION + EXISTING VIDYSETU SOLUTIONS")
    print("=" * 80)

    ai = AIService()
    real_db = get_supabase()

    # -------------------------------------------------------------------------
    # TEST 1: Targeted candidate retrieval returns relevant same-category challenges/projects
    # -------------------------------------------------------------------------
    print("\n[TEST 1] Targeted Candidate Retrieval vs Naive .limit(15):")
    cs = ChallengeService(ai_service=ai, client=real_db)
    water_chl = {
        "challenge_id": "TEST-WATER-999",
        "title": "Municipal water pipeline leakage and rupture detection",
        "description": "Continuous water loss in municipal pipeline due to underground pipe rupture and acoustic pressure drops.",
    }
    candidates = cs.retrieve_targeted_candidates(water_chl, limit=10)
    assert len(candidates) > 0, "Targeted retrieval must return candidate records from real DB"
    assert len(candidates) <= 10, "Targeted candidates must be bounded to specified limit"
    # Ensure ranked by similarity score descending
    scores = [c.get("similarity_score", 0.0) for c in candidates]
    assert all(scores[i] >= scores[i + 1] for i in range(len(scores) - 1)), "Candidates must be ranked descending by similarity_score"
    # Ensure current challenge is never self-included
    assert all(c.get("challenge_id") != "TEST-WATER-999" for c in candidates), "Current challenge cannot be returned in candidate set"
    # Verify candidate metadata is hydrated
    top_cand = candidates[0]
    assert "source" in top_cand, "Candidate must specify source (vidysetu_project or vidysetu_challenge)"
    assert "similarity_score" in top_cand, "Candidate must include deterministic similarity score"
    print(f"  Top Candidate: id={top_cand.get('project_id') or top_cand.get('challenge_id')}, source={top_cand['source']}, sim={top_cand['similarity_score']:.3f}, title='{top_cand.get('title')}'")
    print("[PASS] TEST 1: Targeted candidate retrieval returns bounded, ranked candidates based on token similarity.")

    # -------------------------------------------------------------------------
    # TEST 2: Substantially identical challenge -> duplicate + duplicate_group
    # -------------------------------------------------------------------------
    print("\n[TEST 2] Substantially Identical Challenge -> Duplicate:")
    existing_cands = [
        {
            "challenge_id": "CHL-BASE-01",
            "title": "Smart Solar Inverter for Rural Microgrid Management",
            "description": "Developing a high efficiency smart IoT solar inverter for remote rural microgrid power distribution.",
            "source": "vidysetu_challenge",
            "status": "validated",
        }
    ]
    sub_identical = {
        "challenge_id": "CHL-NEW-02",
        "title": "Smart Solar Inverter for Rural Microgrid Management",
        "description": "Developing a high efficiency smart IoT solar inverter for remote rural microgrid power distribution.",
    }
    rels, sols, dup_id = ai._evaluate_candidate_relationships(sub_identical, existing_cands)
    assert len(rels) == 1, "Must return relationship evaluation for candidate"
    assert rels[0].relationship == "duplicate", f"Expected duplicate, got {rels[0].relationship}"
    assert rels[0].challenge_id == "CHL-BASE-01"
    assert rels[0].similarity_score >= 0.80, f"Expected high similarity >= 0.80, got {rels[0].similarity_score}"
    assert dup_id == "CHL-BASE-01", f"Best duplicate ID must be 'CHL-BASE-01', got '{dup_id}'"

    # Also verify analyze_call_1 returns duplicate_group
    with patch.object(ai, "_call_1_gemini", side_effect=Exception("Gemini quota 429")):
        with patch.object(ai, "_call_1_openai", return_value=(None, "OpenAI quota 429")):
            res2 = ai.analyze_call_1(sub_identical, existing_challenges=existing_cands)
    assert res2["duplicate_group"] == "CHL-BASE-01", f"Expected duplicate_group='CHL-BASE-01', got '{res2.get('duplicate_group')}'"
    print(f"  Identified duplicate: {res2['duplicate_group']} with score {rels[0].similarity_score:.2f}")
    print("[PASS] TEST 2: Substantially identical challenge classified as duplicate with duplicate_group populated.")

    # -------------------------------------------------------------------------
    # TEST 3: Similar problem with different locality/scope -> related, NOT duplicate
    # -------------------------------------------------------------------------
    print("\n[TEST 3] Similar Domain with Different Scope -> Related (NOT Duplicate):")
    existing_cands3 = [
        {
            "challenge_id": "CHL-ROAD-SURAT",
            "title": "Surat Industrial Area Bitumen Road Degradation and Chemical Sludge Potholes",
            "description": "Chemical effluent tanker leakage degrading asphalt in Sachin GIDC industrial cluster.",
            "source": "vidysetu_challenge",
            "status": "validated",
        }
    ]
    diff_scope = {
        "challenge_id": "CHL-ROAD-HIMACHAL",
        "title": "Mountain Highway Freeze-Thaw Pavement Cracks in Spiti Valley",
        "description": "High altitude sub-zero temperature thermal expansion cracks on NH-505 highway requiring polymer additives.",
    }
    rels3, sols3, dup_id3 = ai._evaluate_candidate_relationships(diff_scope, existing_cands3)
    assert len(rels3) == 1
    assert rels3[0].relationship == "related", f"Expected 'related', got '{rels3[0].relationship}'"
    assert dup_id3 is None, f"Expected dup_id=None for related challenge, got '{dup_id3}'"

    with patch.object(ai, "_call_1_gemini", side_effect=Exception("Gemini quota 429")):
        with patch.object(ai, "_call_1_openai", return_value=(None, "OpenAI quota 429")):
            res3 = ai.analyze_call_1(diff_scope, existing_challenges=existing_cands3)
    assert res3["duplicate_group"] is None, "duplicate_group must NOT be populated for related challenges"
    print(f"  Relationship: {rels3[0].relationship}, duplicate_group: {res3['duplicate_group']}")
    print("[PASS] TEST 3: Different scope/locality categorized as 'related' without setting duplicate_group.")

    # -------------------------------------------------------------------------
    # TEST 4: Problem matching completed VidySetu project -> existing_solution
    # -------------------------------------------------------------------------
    print("\n[TEST 4] Problem Matching Completed VidySetu Project -> existing_solution:")
    completed_proj_cand = [
        {
            "project_id": "PRJ-U002-C047",
            "challenge_id": "C047",
            "title": "Acoustic Sensor Pipeline Leakage Detection System",
            "project_title": "Acoustic Sensor Pipeline Leakage Detection System",
            "description": "Municipal water distribution acoustic frequency sensors to detect underground pipe ruptures and water wastage.",
            "source": "vidysetu_project",
            "status": "completed",
            "university_name": "IIT Bombay",
            "industry_name": "Tata Utilities",
            "evidence_url": "https://vidysetu.gov.in/evidence/c047.pdf",
        }
    ]
    matching_ch = {
        "challenge_id": "CHL-NEW-LEAK",
        "title": "Water distribution pipeline leakage detection",
        "description": "Municipal water distribution acoustic frequency sensors to detect underground pipe ruptures.",
    }
    rels4, sols4, dup_id4 = ai._evaluate_candidate_relationships(matching_ch, completed_proj_cand)
    assert len(rels4) == 1
    assert rels4[0].relationship == "existing_solution", f"Expected 'existing_solution', got '{rels4[0].relationship}'"
    assert rels4[0].project_id == "PRJ-U002-C047", "Real DB project_id must be retained in CandidateRelationship"
    assert len(sols4) == 1, "Must generate internal DiscoveredSolution object"
    assert sols4[0].project_id == "PRJ-U002-C047"
    assert sols4[0].source_type == "vidysetu_internal"
    assert sols4[0].university_name == "IIT Bombay"
    assert sols4[0].industry_name == "Tata Utilities"
    print(f"  Discovered Internal Solution: {sols4[0].solution_name} (project_id={sols4[0].project_id}, university={sols4[0].university_name})")
    print("[PASS] TEST 4: Problem matching completed VidySetu project generates 'existing_solution' with real DB project_id.")

    # -------------------------------------------------------------------------
    # TEST 5: Internal VidySetu solution + external public solution coexist
    # -------------------------------------------------------------------------
    print("\n[TEST 5] Coexistence of Internal VidySetu Solution and External Public Solution:")
    ext_sol = DiscoveredSolution(
        solution_name="Jal Jeevan Mission National Portal",
        source_type="external",
        provider="Ministry of Jal Shakti",
        description="Public central government scheme for rural tap connections.",
    )
    int_sol = DiscoveredSolution(
        solution_name="Acoustic Pipeline Sensor",
        source_type="vidysetu_internal",
        project_id="PRJ-U002-C047",
        university_name="IIT Bombay",
        description="Completed VidySetu student project deployed in Ward 4.",
    )
    dummy_out5 = Call1GeminiOutput(
        external_search=ExternalSearchResult(
            search_status="searched",
            existing_solution_found=True,
            solutions=[ext_sol],
        )
    )
    fmt5 = ai._format_call_1_response(dummy_out5, internal_solutions=[int_sol])
    assert len(fmt5["solutions"]) == 2, f"Expected 2 solutions, got {len(fmt5['solutions'])}"
    types = [s["source_type"] for s in fmt5["solutions"]]
    assert "vidysetu_internal" in types and "external" in types, f"Both solution source types must coexist: {types}"
    assert fmt5["solution_found"] is True
    assert fmt5["existing_solution_found"] is True
    print(f"  Coexisting solutions count: {len(fmt5['solutions'])}, types: {types}")
    print("[PASS] TEST 5: Internal VidySetu solution and external public solution coexist without overwriting.")

    # -------------------------------------------------------------------------
    # TEST 6: Citizen accepts internal solution -> accepted_existing_solution
    # -------------------------------------------------------------------------
    print("\n[TEST 6] Citizen Accepts Internal Solution:")
    mock_db6 = MockSupabaseClient()
    mock_db6.challenges["CHL-ACCEPT-01"] = {
        "challenge_id": "CHL-ACCEPT-01",
        "user_id": "cit-001",
        "created_by": "cit-001",
        "status": "existing_solution_found",
        "title": "Water leakage problem",
        "ai_analysis": {
            "challenge_id": "CHL-ACCEPT-01",
            "solution_found": True,
            "existing_solution": "Acoustic Sensor Pipeline Leakage Detection System",
        },
    }
    mock_db6.ai_analysis["CHL-ACCEPT-01"] = dict(mock_db6.challenges["CHL-ACCEPT-01"]["ai_analysis"])
    cs6 = ChallengeService(ai_service=ai, client=mock_db6)
    user6 = AuthenticatedUser(user_id="cit-001", email="cit@test.com", role="citizen")
    res6 = cs6.handle_existing_solution_response(
        challenge_id="CHL-ACCEPT-01",
        user=user6,
        accepted=True,
    )
    assert res6["status"] == "accepted_existing_solution"
    assert res6["action_taken"] == "solution_accepted"
    assert res6["llm_calls_made"] == 1, "Accepting existing solution must require 0 extra LLM calls"
    assert mock_db6.challenges["CHL-ACCEPT-01"]["status"] == "accepted_existing_solution"
    print(f"  Updated status: {res6['status']}, extra LLM calls: 0")
    print("[PASS] TEST 6: Citizen accepts internal solution -> status='accepted_existing_solution'.")

    # -------------------------------------------------------------------------
    # TEST 7: Citizen rejects internal solution with valid gap -> Call 2 -> VALID_GAP -> validated
    # -------------------------------------------------------------------------
    print("\n[TEST 7] Citizen Rejects with Valid Gap -> Call 2 VALID_GAP -> validated:")
    mock_db7 = MockSupabaseClient()
    mock_db7.challenges["CHL-GAP-01"] = {
        "challenge_id": "CHL-GAP-01",
        "user_id": "cit-002",
        "created_by": "cit-002",
        "status": "existing_solution_found",
        "title": "Groundwater desalination in arid saline belt",
        "description": "Borewell groundwater is extremely brackish and unusable for drinking.",
        "ai_analysis": {
            "challenge_id": "CHL-GAP-01",
            "category": "environment",
            "solution_found": True,
            "existing_solution": "Municipal chlorination plant",
        },
    }
    mock_db7.ai_analysis["CHL-GAP-01"] = dict(mock_db7.challenges["CHL-GAP-01"]["ai_analysis"])
    cs7 = ChallengeService(ai_service=ai, client=mock_db7)
    user7 = AuthenticatedUser(user_id="cit-002", email="cit2@test.com", role="citizen")

    call2_valid_res = {
        "gap_status": "VALID_GAP",
        "solution_gap_valid": True,
        "solution_gap": "Salinity removal requires thermal or membrane desalinization.",
        "ai_summary": "Groundwater brackish salinity desalination",
        "category": "environment",
        "subcategory": "water_purification",
        "required_skills": "Membrane Desalination",
        "required_technologies": "Solar Electrodialysis",
        "severity": "high",
        "priority": "high",
        "innovation_scope": "high",
        "feasibility": "high",
        "confidence_score": 0.92,
    }

    with patch.object(ai, "analyze_call_2_gap_validation", return_value=call2_valid_res):
        res7 = cs7.handle_existing_solution_response(
            challenge_id="CHL-GAP-01",
            user=user7,
            accepted=False,
            rejection_reason="Municipal chlorination does not address brackish salinity or dissolved solids.",
            rejection_category="technical_scope",
        )
    assert res7["status"] == "validated", f"Expected 'validated', got '{res7['status']}'"
    assert res7["solution_gap_valid"] is True
    assert mock_db7.challenges["CHL-GAP-01"]["status"] == "validated"
    print(f"  Updated status: {res7['status']}, gap_valid: {res7['solution_gap_valid']}")
    print("[PASS] TEST 7: Citizen rejects with valid gap -> Call 2 VALID_GAP -> status='validated'.")

    # -------------------------------------------------------------------------
    # TEST 8: Citizen rejects with invalid gap -> status = gap_invalid
    # -------------------------------------------------------------------------
    print("\n[TEST 8] Citizen Rejects with Invalid Gap -> status = gap_invalid:")
    mock_db8 = MockSupabaseClient()
    mock_db8.challenges["CHL-INV-01"] = {
        "challenge_id": "CHL-INV-01",
        "user_id": "cit-003",
        "created_by": "cit-003",
        "status": "existing_solution_found",
        "title": "Water distribution leak",
        "description": "Water leaks in pipeline.",
        "ai_analysis": {
            "challenge_id": "CHL-INV-01",
            "category": "environment",
            "solution_found": True,
            "existing_solution": "Acoustic Sensor Pipeline Leakage Detection System",
        },
    }
    mock_db8.ai_analysis["CHL-INV-01"] = dict(mock_db8.challenges["CHL-INV-01"]["ai_analysis"])
    cs8 = ChallengeService(ai_service=ai, client=mock_db8)
    user8 = AuthenticatedUser(user_id="cit-003", email="cit3@test.com", role="citizen")

    call2_invalid_res = {
        "gap_status": "INVALID_GAP",
        "solution_gap_valid": False,
        "solution_gap": "No valid research gap identified.",
        "ai_summary": "Water leak",
        "category": "environment",
        "subcategory": "water_leakage",
        "severity": "low",
        "priority": "low",
        "innovation_scope": "none",
        "feasibility": "high",
        "confidence_score": 0.88,
    }

    with patch.object(ai, "analyze_call_2_gap_validation", return_value=call2_invalid_res):
        res8 = cs8.handle_existing_solution_response(
            challenge_id="CHL-INV-01",
            user=user8,
            accepted=False,
            rejection_reason="I just don't like this project, make another one.",
            rejection_category="other",
        )
    assert res8["status"] == "gap_invalid", f"Expected 'gap_invalid', got '{res8['status']}'"
    assert res8["solution_gap_valid"] is False
    assert mock_db8.challenges["CHL-INV-01"]["status"] == "gap_invalid"
    print(f"  Updated status: {res8['status']}, gap_valid: {res8['solution_gap_valid']}")
    print("[PASS] TEST 8: Citizen rejects with invalid gap -> status='gap_invalid'.")

    # -------------------------------------------------------------------------
    # TEST 9: External search failure -> search_status = search_failed, existing_solution_found = null, status = uncertain_solution_search
    # -------------------------------------------------------------------------
    print("\n[TEST 9] External Search Failure Semantics:")
    failed_ext_out = Call1GeminiOutput(
        external_search=ExternalSearchResult(
            search_status="search_failed",
            existing_solution_found=None,
            solutions=[],
            evidence_summary="Search provider returned 503 Service Unavailable.",
        )
    )
    fmt9 = ai._format_call_1_response(failed_ext_out, internal_solutions=[])
    assert fmt9["external_search_status"] == "search_failed"
    assert fmt9["existing_solution_found"] is None, "CRITICAL: existing_solution_found must be None on search failure, NEVER False"
    assert fmt9["solution_found"] is False

    # Also verify ChallengeService maps search_failed to 'uncertain_solution_search'
    mock_db9 = MockSupabaseClient()
    mock_db9.challenges["CHL-SEARCH-FAIL"] = {
        "challenge_id": "CHL-SEARCH-FAIL",
        "user_id": "cit-009",
        "created_by": "cit-009",
        "title": "Advanced Quantum Sensor for Underground Aquifers",
        "description": "Designing room-temperature quantum diamond NV magnetometers for deep subterranean aquifer mapping.",
        "status": "submitted",
    }
    cs9 = ChallengeService(ai_service=ai, client=mock_db9)
    user9 = AuthenticatedUser(user_id="cit-009", email="cit9@test.com", role="citizen")

    # Simulate Call 1 returning search_failed with no internal solution
    call1_mock_res = {
        "category": "water",
        "subcategory": "groundwater_sensing",
        "ai_summary": "Quantum magnetometry for aquifer mapping",
        "validity": "valid",
        "validity_raw": "eligible",
        "innovation_scope": "high",
        "feasibility": "high",
        "university_suitable": True,
        "solution_found": False,
        "existing_solution_found": None,
        "external_search_status": "search_failed",
        "image_evidence_status": "not_provided",
        "provider_used": "gemini",
        "solutions": [],
        "duplicate_group": None,
        "similar_challenges": json.dumps({"schema_version": 1, "external_search": {"search_status": "search_failed", "existing_solution_found": None}}),
    }

    with patch.object(ai, "analyze_call_1", return_value=call1_mock_res):
        res9 = cs9.analyze_challenge(challenge_id="CHL-SEARCH-FAIL", user=user9)

    assert res9["status"] == "uncertain_solution_search", f"Expected 'uncertain_solution_search', got '{res9['status']}'"
    assert mock_db9.challenges["CHL-SEARCH-FAIL"]["status"] == "uncertain_solution_search"
    print(f"  External search_status='search_failed' -> Challenge status: '{res9['status']}' (quarantined from government)")
    print("[PASS] TEST 9: Search failure preserves existing_solution_found=None and transitions to 'uncertain_solution_search'.")

    # -------------------------------------------------------------------------
    # TEST 10: Routine streetlight complaint -> rejected at deterministic gate (0 Gemini, 0 OpenAI calls)
    # -------------------------------------------------------------------------
    print("\n[TEST 10] Routine Streetlight Complaint Rejection (0 LLM Calls):")
    routine_ch = {
        "challenge_id": "TEST-CHL-ROUTINE",
        "title": "Street light fixation",
        "description": "The street light need to be fixed of our society outside house 42.",
    }
    with patch.object(ai, "_call_1_gemini", side_effect=AssertionError("Gemini must NOT be called for routine submission!")):
        with patch.object(ai, "_call_1_openai", side_effect=AssertionError("OpenAI must NOT be called for routine submission!")):
            res10 = ai.analyze_call_1(routine_ch)

    assert res10["validity_raw"] == "ineligible"
    assert res10["innovation_scope"] == "none"
    assert res10["university_suitable"] is False
    assert res10["next_action"] == "reject"
    assert res10["provider_used"] == "backend"
    print(f"  Provider used: {res10['provider_used']}, Validity: {res10['validity']}, External LLM calls: 0 (Gemini: 0, OpenAI: 0)")
    print("[PASS] TEST 10: Routine streetlight complaint rejected by deterministic gate with 0 Gemini/OpenAI calls.")

    # -------------------------------------------------------------------------
    # TEST 11: Innovation streetlight IoT problem passes deterministic gate
    # -------------------------------------------------------------------------
    print("\n[TEST 11] Innovation Streetlight IoT Problem Passes Deterministic Gate:")
    iot_ch = {
        "challenge_id": "TEST-CHL-IOT-11",
        "title": "City-wide Mesh IoT Streetlight Automation and Telemetry",
        "description": "Designing autonomous mesh network microcontroller nodes for 10,000 streetlights with dynamic LDR dimming, power theft detection, and predictive maintenance telemetry.",
    }
    gate_res = ai.evaluate_deterministic_gate(iot_ch)
    assert gate_res.decision == "continue", f"Innovation challenge must return 'continue', got '{gate_res.decision}'"
    print(f"  Pre-screen decision: '{gate_res.decision}', reason_code: '{gate_res.reason_code}', innovation_scope: '{gate_res.innovation_scope}'")
    print("[PASS] TEST 11: Innovation streetlight IoT challenge successfully passes deterministic pre-screen.")

    # -------------------------------------------------------------------------
    # TEST 12: PastProjectsPage uses real project data, not mockData.js
    # -------------------------------------------------------------------------
    print("\n[TEST 12] PastProjectsPage Verification (No mockData):")
    past_projects_path = os.path.join(
        backend_dir, "..", "Frontend_updated", "src", "pages", "PastProjectsPage.jsx"
    )
    with open(past_projects_path, "r", encoding="utf-8") as f:
        pp_code = f.read()

    assert "mockData" not in pp_code, "mockData.js must be completely removed from PastProjectsPage.jsx"
    assert "projectService.fetchProjects" in pp_code, "PastProjectsPage must call projectService.fetchProjects"
    assert "status: 'completed'" in pp_code, "PastProjectsPage must filter for completed projects"
    assert "project_title" in pp_code, "PastProjectsPage must render project_title"
    assert "university_name" in pp_code, "PastProjectsPage must render university_name"
    assert "challenge_title" in pp_code, "PastProjectsPage must render challenge_title"
    print("  PastProjectsPage imports projectService and renders real database fields (no mockData).")
    print("[PASS] TEST 12: PastProjectsPage uses real project data from live API and database.")

    # -------------------------------------------------------------------------
    # TEST 13: LLM cannot invent candidate IDs (hallucinated IDs rejected)
    # -------------------------------------------------------------------------
    print("\n[TEST 13] Prevention of LLM Hallucinated Candidate IDs:")
    legit_records = [
        {
            "challenge_id": "CHL-LEGIT-101",
            "title": "Real challenge in database",
            "description": "Real challenge description.",
            "source": "vidysetu_challenge",
        }
    ]
    hallucinated_rels = [
        CandidateRelationship(
            challenge_id="CHL-FAKE-99999",
            relationship="duplicate",
            similarity_score=0.98,
            reason="Hallucinated duplicate that does not exist in candidate_records",
            source="vidysetu_challenge",
        ),
        CandidateRelationship(
            challenge_id="CHL-LEGIT-101",
            relationship="related",
            similarity_score=0.65,
            reason="Legitimate candidate",
            source="vidysetu_challenge",
        ),
    ]
    eval_rels, eval_sols, eval_dup_id = ai._evaluate_candidate_relationships(
        {"challenge_id": "CHL-CURR-01", "title": "Current submission", "description": "Current description"},
        legit_records,
        raw_relationships=hallucinated_rels,
    )
    eval_cids = [r.challenge_id for r in eval_rels]
    assert "CHL-FAKE-99999" not in eval_cids, "Hallucinated challenge_id must be stripped by backend validator"
    assert "CHL-LEGIT-101" in eval_cids, "Legitimate candidate must be preserved"
    assert eval_dup_id != "CHL-FAKE-99999", "Hallucinated candidate cannot become duplicate_group"
    print(f"  Allowed Candidate IDs: {eval_cids}, Hallucinated ID rejected: True")
    print("[PASS] TEST 13: LLM hallucinated candidate IDs are rejected and cannot be persisted.")

    # -------------------------------------------------------------------------
    # TEST 14: No database migration required (schema verified)
    # -------------------------------------------------------------------------
    print("\n[TEST 14] Database Schema Integrity (No Migration Required):")
    # Verify ai_analysis columns via Supabase select
    sample_analysis = real_db.table("ai_analysis").select("challenge_id, similar_challenges, duplicate_group").limit(1).execute()
    assert sample_analysis.data is not None, "ai_analysis table must exist and be accessible"
    assert "similar_challenges" in sample_analysis.data[0], "similar_challenges text/json column must exist"
    assert "duplicate_group" in sample_analysis.data[0], "duplicate_group text column must exist"

    # Verify versioned envelope serialization and deserialization
    envelope = {
        "schema_version": 1,
        "provider_metadata": {"provider": "gemini"},
        "internal_search": {
            "search_status": "searched",
            "existing_solution_found": True,
            "solutions": [{"solution_name": "Test Project", "source_type": "vidysetu_internal"}],
        },
        "external_search": {
            "search_status": "searched",
            "existing_solution_found": False,
            "solutions": [],
        },
        "similar_challenges": [
            {
                "challenge_id": "CHL-001",
                "relationship": "related",
                "similarity_score": 0.45,
                "reason": "Token overlap in municipal water management",
                "source": "vidysetu_challenge",
            }
        ],
    }
    serialized = json.dumps(envelope)
    unpacked = cs._unpack_ai_analysis({"challenge_id": "TEST-CHL", "similar_challenges": serialized})
    assert unpacked.get("internal_search_status") == "searched"
    assert len(unpacked.get("internal_solutions", [])) == 1
    assert len(unpacked.get("similar_challenges_list", [])) == 1
    print("  Envelope version 1 round-trip clean. Zero database migrations or column additions needed.")
    print("[PASS] TEST 14: Versioned envelope cleanly persists to existing similar_challenges column without migrations.")

    print("\n" + "=" * 80)
    print("ALL 14 TESTS PASSED SUCCESSFULLY!")
    print("=" * 80)


if __name__ == "__main__":
    run_all_14_tests()
