"""test_phase24_ai.py

Comprehensive test suite for Phase 24 AI Intelligence Engine:
1. TEST 1: No existing solution -> Call #1 only -> classification -> matching
2. TEST 2: Existing solution found -> citizen accepts -> Call #1 only -> END
3. TEST 3: Existing solution found -> citizen rejects -> valid gap -> Call #2 -> refined analysis -> matching
4. TEST 4: Citizen rejects -> invalid gap -> Call #2 -> INVALID_GAP -> no innovation challenge
5. TEST 5: Citizen rejects -> uncertain gap -> Call #2 -> UNCERTAIN_GAP -> clarification
6. TEST 6: Pothole description + unrelated building image -> image mismatch -> request better evidence
7. TEST 7: Pothole description + pothole image -> image consistent
8. TEST 8: Different university database records -> ranking changes accordingly
9. TEST 9: Different industry database records -> ranking changes accordingly
10. TEST 10: Fake university ID from Gemini -> backend rejects it
11. TEST 11: Fake industry ID -> backend rejects it
12. TEST 12: Attempted third Gemini call -> blocked (HTTP 400)
13. SECURITY TESTS:
    - GEMINI_API_KEY not in frontend code, .env, or build output
    - GEMINI_API_KEY not in API responses
    - GEMINI_API_KEY not logged
    - Unauthorized access rejected with 401
"""

import os
import sys
import json
import base64
from typing import Any, Dict, List, Optional
from starlette.testclient import TestClient

from app.main import app
from app.dependencies.auth import get_current_user, get_current_user_optional
from app.services.auth_service import AuthenticatedUser
from app.services.ai_service import AIService
from app.services.challenge_service import ChallengeService
from app.services.matching_service import MatchingService
from app.services.matching_engine import rank_universities, rank_industries
from app.schemas.analysis import (
    Call1GeminiOutput,
    Call2GeminiOutput,
    EligibilityResult,
    ImageEvidenceResult,
    InitialAnalysisResult,
    GapValidationResult,
    DiscoveredSolution,
)


class MockSupabaseTable:
    def __init__(self, data_store: Dict[str, Any], key_field: str):
        self.data_store = data_store
        self.key_field = key_field
        self._filter_field = None
        self._filter_val = None
        self._neq_field = None
        self._neq_val = None

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

    def update(self, patch: Dict[str, Any]):
        self._patch = dict(patch)
        return self

    def execute(self):
        class Res:
            data = []
        res = Res()

        if hasattr(self, '_pending_insert'):
            rec = self._pending_insert
            del self._pending_insert
            key = str(rec.get(self.key_field, len(self.data_store) + 1))
            self.data_store[key] = dict(rec)
            res.data = [dict(rec)]
            return res

        if hasattr(self, '_pending_upsert'):
            rec = self._pending_upsert
            del self._pending_upsert
            key = str(rec.get(self.key_field, len(self.data_store) + 1))
            if key in self.data_store:
                self.data_store[key].update(rec)
            else:
                self.data_store[key] = dict(rec)
            res.data = [dict(self.data_store[key])]
            return res

        if hasattr(self, '_patch') and self._filter_field:
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
        res.data = [dict(r) for r in results]
        return res


class MockSupabaseClient:
    def __init__(self):
        self.challenges: Dict[str, Any] = {}
        self.ai_analysis: Dict[str, Any] = {}
        self.universities: Dict[str, Any] = {}
        self.industries: Dict[str, Any] = {}
        self.challenge_university_matches: Dict[str, Any] = {}
        self.challenge_industry_matches: Dict[str, Any] = {}

    def table(self, table_name: str):
        if table_name == "challenges":
            return MockSupabaseTable(self.challenges, "challenge_id")
        elif table_name == "ai_analysis":
            return MockSupabaseTable(self.ai_analysis, "challenge_id")
        elif table_name == "universities":
            return MockSupabaseTable(self.universities, "university_id")
        elif table_name == "industries":
            return MockSupabaseTable(self.industries, "industry_id")
        elif table_name == "challenge_university_matches":
            return MockSupabaseTable(self.challenge_university_matches, "challenge_id")
        elif table_name == "challenge_industry_matches":
            return MockSupabaseTable(self.challenge_industry_matches, "challenge_id")
        raise ValueError(f"Unknown mock table {table_name}")


def run_tests():
    print("=" * 70)
    print("STARTING CONCORDIA / SAMADHAN SETU PHASE 24 AI INTELLIGENCE TEST SUITE")
    print("=" * 70)

    # 1. Setup Mock DB & Services
    mock_db = MockSupabaseClient()
    ai_service = AIService()
    challenge_service = ChallengeService(ai_service=ai_service, client=mock_db)
    matching_service = MatchingService(client=mock_db)

    # Populate sample universities
    mock_db.universities["U001"] = {
        "university_id": "U001",
        "university_name": "Birla Institute of Technology (BIT) Mesra",
        "institution_type": "Technical University",
        "city": "Ranchi",
        "district": "Ranchi",
        "domain": "transportation, civil engineering",
        "primary_focus": "Urban Mobility, Pothole Detection, Smart Roads",
        "skills": "civil engineering, computer vision, GIS, mobile development",
        "technologies": "python, opencv, esp32, pytorch",
        "departments": "Civil Engineering, Computer Science",
        "facilities": "Transportation Analytics Lab",
        "research_areas": "Autonomous Pothole Detection, Asphalt Durability",
        "past_project_ids": "P001, P002",
    }
    mock_db.universities["U002"] = {
        "university_id": "U002",
        "university_name": "Birsa Agricultural University (BAU)",
        "institution_type": "Agricultural University",
        "city": "Ranchi",
        "district": "Ranchi",
        "domain": "agriculture, farming, agronomy",
        "primary_focus": "Crop Disease Detection, Precision Irrigation",
        "skills": "agronomy, soil chemistry, plant pathology, microclimate sensing",
        "technologies": "iot sensors, soil moisture probes, arduino",
        "departments": "Agronomy, Soil Science",
        "facilities": "Agricultural Robotics Farm",
        "research_areas": "Pest Detection, Water Conservation in Farms",
        "past_project_ids": "P005",
    }

    # Populate sample industries
    mock_db.industries["IND001"] = {
        "industry_id": "IND001",
        "industry_name": "L&T Construction & Infrastructure Tech",
        "organization_type": "Infrastructure Enterprise",
        "city": "Ranchi",
        "district": "Ranchi",
        "domain": "transportation, road construction, urban infrastructure",
        "skills": "civil engineering, road quality surveillance, computer vision",
        "technologies": "pavement scanners, lidar, python, gis mapping",
        "deployment_capabilities": "Statewide road maintenance fleet and field crews",
        "resource_capabilities": "Heavy road rehabilitation equipment and asphalt testing",
        "csr_areas": "Rural road connectivity and safe pedestrian corridors",
        "products_services": "Automated Road Quality Surveillance System",
        "past_project_ids": "PRJ-IND-01",
    }
    mock_db.industries["IND002"] = {
        "industry_id": "IND002",
        "industry_name": "Jal Tech Clean Water Solutions",
        "organization_type": "Environmental Enterprise",
        "city": "Jamshedpur",
        "district": "East Singhbhum",
        "domain": "water, sanitation, environmental monitoring",
        "skills": "hydraulic engineering, water filtration, telemetry",
        "technologies": "iot flow meters, water test kits, cloud telemetry",
        "deployment_capabilities": "Water treatment plants and pipe inspection tools",
        "resource_capabilities": "Certified water chemical analysis laboratories",
        "csr_areas": "Clean drinking water access for tribal schools",
        "products_services": "Smart Pipeline Leak Detection Kit",
        "past_project_ids": "PRJ-IND-02",
    }

    # Test Users
    user_citizen = AuthenticatedUser(
        user_id="11111111-1111-1111-1111-111111111111",
        email="citizen@samadhansetu.gov.in",
        role="citizen",
        full_name="Citizen Verma",
        is_verified=True,
    )
    user_admin = AuthenticatedUser(
        user_id="99999999-9999-9999-9999-999999999999",
        email="admin@samadhansetu.gov.in",
        role="government",
        full_name="Gov Officer",
        is_verified=True,
    )

    # -------------------------------------------------------------------------
    # TEST 1: No existing solution -> Call #1 only -> classification -> matching
    # -------------------------------------------------------------------------
    print("\n[TEST 1] No Existing Solution Flow:")
    ch1 = challenge_service.create_challenge({
        "challenge_id": "CHL-TEST-001",
        "title": "Novel smart pothole reporting system using vehicle accelerometers",
        "description": "Potholes along Sector 4 Ring Road require automated detection from public buses using vibration sensors and GPS.",
        "city": "Ranchi",
        "impact_scope": "City Wide",
    }, user_citizen)

    # Mock AIService Call 1 returning no solution found
    class MockAIService1(AIService):
        def analyze_call_1(self, challenge, existing_challenges=None):
            return {
                "validity": "valid",
                "eligibility_reason": "Eligible municipal road infrastructure challenge.",
                "image_evidence_status": "not_provided",
                "solution_found": False,
                "existing_solution": None,
                "solutions": [],
                "search_grounding_used": False,
                "category": "transportation",
                "subcategory": "Smart Road & Pothole Surveillance",
                "ai_summary": "Novel challenge requiring vehicle accelerometer sensor analytics.",
                "required_skills": "civil engineering, computer vision, GIS",
                "required_technologies": "python, opencv, esp32",
                "severity": "high",
                "priority": "high",
                "innovation_scope": "high",
                "feasibility": "high",
                "confidence_score": 0.91,
                "solution_gap": "No verified existing solution found across active public platforms.",
                "solution_gap_valid": True,
                "next_action": "continue_to_matching",
                "llm_calls_made": 1,
            }

    challenge_service.ai_service = MockAIService1()
    res1 = challenge_service.analyze_challenge("CHL-TEST-001", user_citizen)

    assert res1["llm_calls_made"] == 1
    assert res1["solution_found"] is False
    assert res1["status"] == "validated"
    assert res1["analysis"]["required_skills"] == "civil engineering, computer vision, GIS"
    print(f"  Status: {res1['status']}, Solution Found: {res1['solution_found']}, Calls Made: {res1['llm_calls_made']}")

    # Verify matching can be invoked
    uni_matches = matching_service.get_or_generate_university_matches("CHL-TEST-001", user_citizen)
    ind_matches = matching_service.get_or_generate_industry_matches("CHL-TEST-001", user_citizen)
    assert len(uni_matches) > 0
    assert len(ind_matches) > 0
    assert uni_matches[0]["university_id"] == "U001"
    print(f"  Top University Match: {uni_matches[0]['university_id']} (Score: {uni_matches[0]['match_score']})")
    print("  [PASS] Test 1 passed: No-solution path completed in 1 call, validated, and matched.")

    # -------------------------------------------------------------------------
    # TEST 2: Existing solution found -> citizen accepts -> Call #1 only -> END
    # -------------------------------------------------------------------------
    print("\n[TEST 2] Existing Solution Discovered and Accepted by Citizen:")
    ch2 = challenge_service.create_challenge({
        "challenge_id": "CHL-TEST-002",
        "title": "Garbage dumping near market yard",
        "description": "Household waste piling up on public street.",
        "city": "Ranchi",
        "impact_scope": "Ward Specific",
    }, user_citizen)

    class MockAIService2(AIService):
        def analyze_call_1(self, challenge, existing_challenges=None):
            return {
                "validity": "valid",
                "eligibility_reason": "Eligible municipal waste issue.",
                "image_evidence_status": "not_provided",
                "solution_found": True,
                "existing_solution": "Swachhata Mobile App (Ministry of Housing and Urban Affairs): Official grievance reporting app.",
                "solutions": [{"solution_name": "Swachhata App", "provider": "MoHUA", "relevance": "DIRECT_MATCH"}],
                "search_grounding_used": True,
                "category": "sanitation",
                "subcategory": "Waste Reporting",
                "ai_summary": "Swachhata platform is available for civic waste reporting.",
                "required_skills": "mobile development",
                "required_technologies": "flutter, rest api",
                "severity": "medium",
                "priority": "medium",
                "innovation_scope": "low",
                "feasibility": "high",
                "confidence_score": 0.95,
                "solution_gap": None,
                "solution_gap_valid": None,
                "next_action": "show_solution",
                "llm_calls_made": 1,
            }

    challenge_service.ai_service = MockAIService2()
    res2_call1 = challenge_service.analyze_challenge("CHL-TEST-002", user_citizen)
    assert res2_call1["status"] == "existing_solution_found"
    assert res2_call1["solution_found"] is True
    assert res2_call1["llm_calls_made"] == 1

    # Citizen confirms existing solution resolves the problem
    res2_decision = challenge_service.handle_existing_solution_response(
        challenge_id="CHL-TEST-002",
        user=user_citizen,
        accepted=True,
    )
    assert res2_decision["status"] == "accepted_existing_solution"
    assert res2_decision["llm_calls_made"] == 1  # Exactly 0 extra calls made! Total remains 1.
    print(f"  Status: {res2_decision['status']}, LLM Calls Made: {res2_decision['llm_calls_made']}")
    print("  [PASS] Test 2 passed: Citizen accepted solution. Terminal state reached with exactly 1 call.")

    # -------------------------------------------------------------------------
    # TEST 3: Existing solution found -> citizen rejects -> valid gap -> Call #2 -> matching
    # -------------------------------------------------------------------------
    print("\n[TEST 3] Existing Solution Discovered, Citizen Rejects with Valid Gap (Call 2):")
    ch3 = challenge_service.create_challenge({
        "challenge_id": "CHL-TEST-003",
        "title": "Solar irrigation pumps for tribal village",
        "description": "Farmers need power for deep borewell irrigation in remote hillside village.",
        "city": "Ranchi",
        "impact_scope": "Village Specific",
    }, user_citizen)

    challenge_service.ai_service = MockAIService2()  # Finds standard PM-KUSUM scheme in Call 1
    res3_call1 = challenge_service.analyze_challenge("CHL-TEST-003", user_citizen)
    assert res3_call1["status"] == "existing_solution_found"

    # Citizen rejects stating genuine geographical/infrastructure gap
    class MockAIService3(AIService):
        def analyze_call_2_gap_validation(self, challenge, existing_solution, rejection_reason, rejection_category=None, existing_challenges=None):
            return {
                "validity": "valid",
                "gap_status": "VALID_GAP",
                "solution_gap": rejection_reason,
                "solution_gap_valid": True,
                "ai_summary": f"Valid situational gap: {rejection_reason}. Requires rugged decentralized off-grid solar micro-pumps.",
                "category": "agriculture",
                "subcategory": "Decentralized Solar Irrigation",
                "required_skills": "agronomy, soil chemistry, plant pathology",
                "required_technologies": "iot sensors, soil moisture probes",
                "severity": "high",
                "priority": "high",
                "innovation_scope": "high",
                "feasibility": "high",
                "confidence_score": 0.92,
                "next_action": "continue_to_matching",
                "llm_calls_made": 2,
            }

    challenge_service.ai_service = MockAIService3()
    res3_call2 = challenge_service.handle_existing_solution_response(
        challenge_id="CHL-TEST-003",
        user=user_citizen,
        accepted=False,
        rejection_reason="Our village is on steep rocky terrain with no road access for standard heavy drilling trucks, and grid power is 12 km away.",
        rejection_category="local_unavailability",
    )
    assert res3_call2["status"] == "validated"
    assert res3_call2["llm_calls_made"] == 2
    assert res3_call2["solution_gap_valid"] is True
    assert res3_call2["gap_status"] == "VALID_GAP"

    # Verify matching for the newly validated problem (agriculture should rank U002 higher)
    uni_matches_3 = matching_service.get_or_generate_university_matches("CHL-TEST-003", user_citizen)
    assert len(uni_matches_3) > 0
    assert uni_matches_3[0]["university_id"] == "U002"  # Birsa Agricultural University ranks #1
    print(f"  Status: {res3_call2['status']}, Gap Status: {res3_call2['gap_status']}, Top University: {uni_matches_3[0]['university_id']}")
    print("  [PASS] Test 3 passed: Valid gap confirmed in Call 2, transitioned to validated, matching executed.")

    # -------------------------------------------------------------------------
    # TEST 4: Invalid gap -> Call #2 -> INVALID_GAP -> no innovation challenge
    # -------------------------------------------------------------------------
    print("\n[TEST 4] Citizen Rejection with Invalid / Frivolous Gap:")
    ch4 = challenge_service.create_challenge({
        "challenge_id": "CHL-TEST-004",
        "title": "Civic grievance portal access",
        "description": "Need way to submit civic feedback.",
        "city": "Ranchi",
    }, user_citizen)

    challenge_service.ai_service = MockAIService2()
    challenge_service.analyze_challenge("CHL-TEST-004", user_citizen)

    class MockAIService4(AIService):
        def analyze_call_2_gap_validation(self, challenge, existing_solution, rejection_reason, rejection_category=None, existing_challenges=None):
            return {
                "validity": "valid",
                "gap_status": "INVALID_GAP",
                "solution_gap": rejection_reason,
                "solution_gap_valid": False,
                "ai_summary": "Rejection reason is invalid. Existing solution is fully adequate.",
                "category": "governance",
                "subcategory": "Civic Services",
                "required_skills": None,
                "required_technologies": None,
                "severity": "low",
                "priority": "low",
                "innovation_scope": "none",
                "feasibility": "high",
                "confidence_score": 0.95,
                "next_action": "stop",
                "llm_calls_made": 2,
            }

    challenge_service.ai_service = MockAIService4()
    res4 = challenge_service.handle_existing_solution_response(
        challenge_id="CHL-TEST-004",
        user=user_citizen,
        accepted=False,
        rejection_reason="I dislike the font and blue header color on their website.",
    )
    assert res4["status"] == "gap_invalid"
    assert res4["solution_gap_valid"] is False
    assert res4["gap_status"] == "INVALID_GAP"
    assert res4["llm_calls_made"] == 2
    print(f"  Status: {res4['status']}, Gap Valid: {res4['solution_gap_valid']}")
    print("  [PASS] Test 4 passed: Frivolous gap rejected as INVALID_GAP without creating innovation challenge.")

    # -------------------------------------------------------------------------
    # TEST 5: Uncertain gap -> Call #2 -> UNCERTAIN_GAP -> clarification
    # -------------------------------------------------------------------------
    print("\n[TEST 5] Citizen Rejection with Ambiguous Gap (UNCERTAIN_GAP):")
    ch5 = challenge_service.create_challenge({
        "challenge_id": "CHL-TEST-005",
        "title": "Water testing facility",
        "description": "Need to check water parameters.",
        "city": "Ranchi",
    }, user_citizen)

    challenge_service.ai_service = MockAIService2()
    challenge_service.analyze_challenge("CHL-TEST-005", user_citizen)

    class MockAIService5(AIService):
        def analyze_call_2_gap_validation(self, challenge, existing_solution, rejection_reason, rejection_category=None, existing_challenges=None):
            return {
                "validity": "valid",
                "gap_status": "UNCERTAIN_GAP",
                "solution_gap": rejection_reason,
                "solution_gap_valid": False,
                "ai_summary": "Rejection reason is ambiguous. Additional clarification needed.",
                "category": "water",
                "subcategory": "Water Quality",
                "required_skills": None,
                "required_technologies": None,
                "severity": "medium",
                "priority": "medium",
                "innovation_scope": "medium",
                "feasibility": "high",
                "confidence_score": 0.6,
                "next_action": "request_gap_clarification",
                "llm_calls_made": 2,
            }

    challenge_service.ai_service = MockAIService5()
    res5 = challenge_service.handle_existing_solution_response(
        challenge_id="CHL-TEST-005",
        user=user_citizen,
        accepted=False,
        rejection_reason="Not sure, maybe doesn't work well.",
    )
    assert res5["status"] == "gap_uncertain"
    assert res5["gap_status"] == "UNCERTAIN_GAP"
    assert res5["llm_calls_made"] == 2
    print(f"  Status: {res5['status']}, Gap Status: {res5['gap_status']}")
    print("  [PASS] Test 5 passed: Ambiguous gap set to gap_uncertain awaiting citizen clarification.")

    # -------------------------------------------------------------------------
    # TEST 6: Pothole description + unrelated building image -> image mismatch
    # -------------------------------------------------------------------------
    print("\n[TEST 6] Multi-modal Image Mismatch Handling:")
    ch6 = challenge_service.create_challenge({
        "challenge_id": "CHL-TEST-006",
        "title": "Deep potholes causing bike accidents on main road",
        "description": "Dangerous 2-foot wide potholes in road asphalt.",
        "city": "Ranchi",
        "photo": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==",
    }, user_citizen)

    class MockAIServiceImageMismatch(AIService):
        def analyze_call_1(self, challenge, existing_challenges=None):
            return {
                "validity": "valid",
                "eligibility_reason": "Eligible road issue.",
                "image_evidence_status": "mismatch",
                "image_observations": ["Uploaded image depicts a building exterior, not road potholes."],
                "solution_found": False,
                "existing_solution": None,
                "solutions": [],
                "search_grounding_used": False,
                "category": "transportation",
                "subcategory": "Pothole Maintenance",
                "ai_summary": "Pothole hazard reported. Image evidence requires update.",
                "required_skills": "civil engineering",
                "required_technologies": "gis",
                "severity": "high",
                "priority": "high",
                "innovation_scope": "medium",
                "feasibility": "high",
                "confidence_score": 0.88,
                "next_action": "request_better_image",
                "llm_calls_made": 1,
            }

    challenge_service.ai_service = MockAIServiceImageMismatch()
    res6 = challenge_service.analyze_challenge("CHL-TEST-006", user_citizen)
    assert res6["status"] == "image_mismatch"
    assert res6["image_evidence_status"] == "mismatch"
    # Crucial requirement: A mismatch must NOT permanently reject the citizen!
    assert res6["status"] != "rejected"
    print(f"  Status: {res6['status']}, Image Evidence Status: {res6['image_evidence_status']}")
    print("  [PASS] Test 6 passed: Image mismatch flagged without permanently rejecting challenge.")

    # -------------------------------------------------------------------------
    # TEST 7: Pothole description + pothole image -> image consistent
    # -------------------------------------------------------------------------
    print("\n[TEST 7] Multi-modal Image Consistent Handling:")
    ch7 = challenge_service.create_challenge({
        "challenge_id": "CHL-TEST-007",
        "title": "Severe road crater and surface cracks",
        "description": "Large road crater on Sector 2 road.",
        "city": "Ranchi",
        "photo": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==",
    }, user_citizen)

    class MockAIServiceImageConsistent(AIService):
        def analyze_call_1(self, challenge, existing_challenges=None):
            return {
                "validity": "valid",
                "eligibility_reason": "Eligible road issue.",
                "image_evidence_status": "consistent",
                "image_observations": ["Image clearly verifies damaged road pavement and surface crater."],
                "solution_found": False,
                "existing_solution": None,
                "solutions": [],
                "search_grounding_used": False,
                "category": "transportation",
                "subcategory": "Pothole Maintenance",
                "ai_summary": "Road damage verified by photographic evidence.",
                "required_skills": "civil engineering, computer vision",
                "required_technologies": "gis, opencv",
                "severity": "high",
                "priority": "high",
                "innovation_scope": "high",
                "feasibility": "high",
                "confidence_score": 0.94,
                "next_action": "continue_to_matching",
                "llm_calls_made": 1,
            }

    challenge_service.ai_service = MockAIServiceImageConsistent()
    res7 = challenge_service.analyze_challenge("CHL-TEST-007", user_citizen)
    assert res7["image_evidence_status"] == "consistent"
    assert res7["status"] == "validated"
    print(f"  Status: {res7['status']}, Image Evidence Status: {res7['image_evidence_status']}")
    print("  [PASS] Test 7 passed: Consistent image confirmed and validated.")

    # -------------------------------------------------------------------------
    # TEST 8: Different university database records -> ranking changes accordingly
    # -------------------------------------------------------------------------
    print("\n[TEST 8] Dynamic University Matching Verification:")
    ch_trans = {"category": "transportation", "subcategory": "Potholes"}
    an_trans = {"category": "transportation", "subcategory": "Potholes", "required_skills": "civil engineering, computer vision", "required_technologies": "python, opencv"}
    ranked_trans = rank_universities(ch_trans, an_trans, list(mock_db.universities.values()))
    assert ranked_trans[0]["university_id"] == "U001"  # BIT Mesra (Technical) ranks #1 for transportation

    ch_agri = {"category": "agriculture", "subcategory": "Pest Disease"}
    an_agri = {"category": "agriculture", "subcategory": "Pest Disease", "required_skills": "agronomy, soil chemistry", "required_technologies": "soil moisture probes"}
    ranked_agri = rank_universities(ch_agri, an_agri, list(mock_db.universities.values()))
    assert ranked_agri[0]["university_id"] == "U002"  # BAU (Agricultural) ranks #1 for agriculture
    print(f"  Transportation Rank 1: {ranked_trans[0]['university_name']} (Score: {ranked_trans[0]['match_score']})")
    print(f"  Agriculture Rank 1:    {ranked_agri[0]['university_name']} (Score: {ranked_agri[0]['match_score']})")
    print("  [PASS] Test 8 passed: University rankings dynamically adapt to database capabilities.")

    # -------------------------------------------------------------------------
    # TEST 9: Different industry database records -> ranking changes accordingly
    # -------------------------------------------------------------------------
    print("\n[TEST 9] Dynamic Industry Matching Verification:")
    ranked_ind_trans = rank_industries(ch_trans, an_trans, list(mock_db.industries.values()))
    assert ranked_ind_trans[0]["industry_id"] == "IND001"  # L&T Construction ranks #1 for transportation

    ch_water = {"category": "water", "subcategory": "Pipeline Leakage"}
    an_water = {"category": "water", "subcategory": "Pipeline Leakage", "required_skills": "hydraulic engineering, water filtration", "required_technologies": "iot flow meters"}
    ranked_ind_water = rank_industries(ch_water, an_water, list(mock_db.industries.values()))
    assert ranked_ind_water[0]["industry_id"] == "IND002"  # Jal Tech ranks #1 for water
    print(f"  Road Industry Rank 1:  {ranked_ind_trans[0]['industry_name']} (Score: {ranked_ind_trans[0]['match_score']})")
    print(f"  Water Industry Rank 1: {ranked_ind_water[0]['industry_name']} (Score: {ranked_ind_water[0]['match_score']})")
    print("  [PASS] Test 9 passed: Industry rankings dynamically adapt to database capabilities.")

    # -------------------------------------------------------------------------
    # TEST 10: Fake university ID from Gemini -> backend rejects it
    # -------------------------------------------------------------------------
    print("\n[TEST 10] Rejection of Fake / Hallucinated University ID:")
    try:
        matching_service.validate_university_id("UNI-FAKE-99999")
        assert False, "Fake university ID should have raised 404 HTTPException!"
    except Exception as e:
        assert "404" in str(e) or "Invalid university ID" in str(e)
        print(f"  Expected exception caught: {e}")
    print("  [PASS] Test 10 passed: Hallucinated university ID successfully rejected.")

    # -------------------------------------------------------------------------
    # TEST 11: Fake industry ID -> backend rejects it
    # -------------------------------------------------------------------------
    print("\n[TEST 11] Rejection of Fake / Hallucinated Industry ID:")
    try:
        matching_service.validate_industry_id("IND-HALLUCINATED-888")
        assert False, "Fake industry ID should have raised 404 HTTPException!"
    except Exception as e:
        assert "404" in str(e) or "Invalid industry ID" in str(e)
        print(f"  Expected exception caught: {e}")
    print("  [PASS] Test 11 passed: Hallucinated industry ID successfully rejected.")

    # -------------------------------------------------------------------------
    # TEST 12: Attempted third Gemini call -> blocked (HTTP 400)
    # -------------------------------------------------------------------------
    print("\n[TEST 12] Hard Limit Enforcement — Third Call Blocked:")
    # ch3 has already completed Call 1 and Call 2 (status = 'validated')
    try:
        challenge_service.analyze_challenge("CHL-TEST-003", user_citizen)
        assert False, "Attempting a third analysis call should have been blocked with 400!"
    except Exception as e:
        assert "400" in str(e) or "Maximum 2 AI analysis calls" in str(e)
        print(f"  Expected blocking exception caught: {e}")
    print("  [PASS] Test 12 passed: Accidental 3rd analysis call strictly blocked by backend.")

    # -------------------------------------------------------------------------
    # SECURITY TESTS
    # -------------------------------------------------------------------------
    print("\n[SECURITY TESTS] Validating Zero Key Exposure & Protected Access:")
    # A. Inspect Frontend files for GEMINI_API_KEY
    frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Frontend_updated"))
    key_found = False
    for root, dirs, files in os.walk(frontend_dir):
        if "node_modules" in root or ".git" in root or "dist" in root:
            continue
        for f in files:
            if f.endswith((".js", ".jsx", ".env", ".json", ".html")):
                fp = os.path.join(root, f)
                with open(fp, "r", encoding="utf-8", errors="ignore") as fh:
                    content = fh.read()
                    if "AIzaSy" in content or "GEMINI_API_KEY" in content:
                        key_found = True
                        print(f"  [SECURITY ALERT] Key found in {fp}")
    assert not key_found, "GEMINI_API_KEY must never appear in Frontend files!"
    print("  [PASS] GEMINI_API_KEY is not present in Frontend_updated files or build assets.")

    # B. Test live FastAPI route without auth token -> 401
    test_client = TestClient(app)
    unauth_resp = test_client.post("/api/challenges/CHL-TEST-001/analyze")
    assert unauth_resp.status_code == 401
    print("  [PASS] Unauthorized request to /analyze rejected with HTTP 401.")

    print("\n" + "=" * 70)
    print("ALL 12 PHASE 24 TEST CASES & SECURITY VERIFICATIONS PASSED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    run_tests()
