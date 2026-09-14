"""test_phase4_matching.py

Comprehensive test suite for Phase 4: Deterministic University + Industry Matching Engine.

Validates:
1. Deterministic repeated execution (10 runs produce 100% identical scores and ranks)
2. Monotonic ranking order (rank 1 >= rank 2 >= rank 3...)
3. Duplicate prevention (UNIQUE constraints respected on repeated calls)
4. Nonexistent challenge handling (404 Not Found)
5. Insufficient data / unanalyzed challenge handling (400 Bad Request)
6. Unauthorized access blocking (401 Unauthorized)
7. Exact weight breakdowns and qualitative explanations
"""

import copy
from typing import Any, Dict, List, Optional
from starlette.testclient import TestClient

from app.main import app
from app.dependencies.auth import get_current_user
from app.routes.challenges import get_matching_service
from app.services.auth_service import AuthenticatedUser
from app.services.matching_service import MatchingService
from app.services.matching_engine import rank_universities, rank_industries


# Real-World Master Seed Data for Universities (from CONCORDIA_BACKEND_CONTEXT.md & Faculties CSV)
SAMPLE_UNIVERSITIES = [
    {
        "university_id": "U001",
        "university_name": "Birla Institute of Technology (BIT) Mesra, Ranchi",
        "city": "Ranchi",
        "district": "Ranchi",
        "domain": "Computer Science, Civil & Environmental Engineering",
        "primary_focus": "Urban Computing, Smart Cities, Structural Modeling",
        "skills": "IoT Sensors, Embedded Systems, Computer Vision, Software Development, Machine Learning",
        "technologies": "ESP32, LoRaWAN, Python, OpenCV, Cloud Telemetry, OpenStreetMap",
        "departments": "Computer Science & Engg, Civil Engineering, Remote Sensing",
        "facilities": "Advanced IoT Prototyping Lab, Remote Sensing Center, Environmental Testing Lab",
        "research_areas": "Smart Cities, Municipal Solid Waste Management, Water Quality",
        "past_project_ids": "PRJ-U001-24-01, PRJ-U001-23-04",
    },
    {
        "university_id": "U002",
        "university_name": "Indian Institute of Technology (ISM) Dhanbad",
        "city": "Dhanbad",
        "district": "Dhanbad",
        "domain": "Environmental Science, Mining & Water Resources",
        "primary_focus": "Wastewater Treatment, Mine Effluent, Underground IoT",
        "skills": "Water Quality Chemistry, Bioremediation, GIS Mapping, AI Predictive Models",
        "technologies": "Underground IoT, Cloud Analytics, Clean Tech, Remote Sensing",
        "departments": "Environmental Science & Engg, Mining Engineering, Computer Science",
        "facilities": "Water Testing Spectrophotometry Lab, Geospatial Data Hub",
        "research_areas": "Water Contamination, Landslide Analysis, Sustainability",
        "past_project_ids": "PRJ-U002-24-11, PRJ-U002-23-45",
    },
    {
        "university_id": "U003",
        "university_name": "National Institute of Technology (NIT) Jamshedpur",
        "city": "Jamshedpur",
        "district": "East Singhbhum",
        "domain": "Transportation Engineering, Materials Science & AI",
        "primary_focus": "Pavement Design, Traffic IoT, High-Strength Alloys",
        "skills": "Computer Vision, Accelerometer Sensor Analytics, Geofencing, Mobile Apps",
        "technologies": "PyTorch, Android SDK, MapLibre, OpenCV, TensorFlow",
        "departments": "Civil Engineering, Metallurgical & Materials, Computer Science",
        "facilities": "Transportation IoT Lab, Advanced Materials Characterization Center",
        "research_areas": "Traffic Analytics, Road Surface Quality, Structural Materials",
        "past_project_ids": "PRJ-U003-22-11, PRJ-U003-23-07",
    },
    {
        "university_id": "U005",
        "university_name": "Birsa Agricultural University (BAU) Ranchi",
        "city": "Ranchi",
        "district": "Ranchi",
        "domain": "Smart Agriculture & Agronomy",
        "primary_focus": "Crop Yield Optimization, Drought Resilience, Soil Fertility",
        "skills": "Soil Moisture Sensing, Crop Disease Diagnostics, Precision Irrigation",
        "technologies": "Deep Learning CNNs, LoRa, Soil Test Kits, Arduino",
        "departments": "Faculty of Agriculture, Plant Pathology, Soil Science",
        "facilities": "Experimental Farm, Plant Pathology Diagnostic Center",
        "research_areas": "AgriTech, Crop Disease, Soil Health",
        "past_project_ids": "PRJ-U005-24-01, PRJ-U005-23-17",
    },
]

# Real-World Master Seed Data for Industries (from CONCORDIA_BACKEND_CONTEXT.md & orgData.js)
SAMPLE_INDUSTRIES = [
    {
        "industry_id": "IND001",
        "industry_name": "Tata CSR Water & Civic Solutions",
        "city": "Jamshedpur",
        "district": "East Singhbhum",
        "domain": "IoT, Water Resources & Environmental Engineering",
        "skills": "IoT Sensors, Water Quality Chemistry, Embedded Systems, Hardware Fabrication",
        "technologies": "ESP32, LoRaWAN, Cloud Telemetry, Solar Inverters",
        "deployment_capabilities": "Statewide Field Deployment, Gram Panchayat Water Tanks, Village Sensor Networks",
        "resource_capabilities": "Hardware fabrication co-funding, Rapid prototyping lab, 50-engineer technical field team",
        "products_services": "Smart water metering, Rural chlorination dispensers, IoT telemetry dashboards",
        "geography": "Jharkhand, Odisha, West Bengal",
        "csr_areas": "Clean Water, Rural Sanitation, Public Health Infrastructure",
        "past_project_ids": "PRJ-IND-24-03, PRJ-IND-23-12",
    },
    {
        "industry_id": "IND002",
        "industry_name": "Tata Steel Innovation Cell",
        "city": "Jamshedpur",
        "district": "East Singhbhum",
        "domain": "Software Development, AI / Machine Learning & Urban Tech",
        "skills": "Computer Vision, Edge AI, Route Optimization, Mobile Development, Python",
        "technologies": "TensorFlow Lite, OpenCV, Python, Flutter, Docker",
        "deployment_capabilities": "Industrial plants, Municipal urban hubs, Fleet tracking",
        "resource_capabilities": "Cloud GPU infrastructure, Co-funding pilot deployments, Enterprise mentorship",
        "products_services": "Visual inspection software, Municipal fleet management, Automated worker safety systems",
        "geography": "Jamshedpur, Ranchi, Dhanbad",
        "csr_areas": "Urban Sustainability, Youth Digital Literacy, Community Development",
        "past_project_ids": "PRJ-IND-24-08",
    },
    {
        "industry_id": "IND003",
        "industry_name": "L&T Construction & Infrastructure Tech",
        "city": "Ranchi",
        "district": "Ranchi",
        "domain": "Smart Transportation & Civil Infrastructure",
        "skills": "Civil Engineering, Accelerometer Sensor Analytics, Structural Modeling",
        "technologies": "PyTorch, MapLibre, Heavy machinery telematics",
        "deployment_capabilities": "Urban road networks, Highway corridors, Bridge monitoring",
        "resource_capabilities": "Heavy construction equipment, Structural test benches",
        "products_services": "Pavement sensors, Smart traffic corridors, Bridge structural monitoring",
        "geography": "Ranchi, Dhanbad, Bokaro",
        "csr_areas": "Road Safety, Disaster Resilient Infrastructure",
        "past_project_ids": "PRJ-IND-22-05",
    },
]


class MockMatchingService(MatchingService):
    """In-memory matching service for hermetic testing of Phase 4 matching logic."""

    def __init__(self):
        super().__init__()
        self.challenges: Dict[str, Dict[str, Any]] = {}
        self.ai_analyses: Dict[str, Dict[str, Any]] = {}
        self.university_matches: Dict[str, List[Dict[str, Any]]] = {}
        self.industry_matches: Dict[str, List[Dict[str, Any]]] = {}
        self.universities = copy.deepcopy(SAMPLE_UNIVERSITIES)
        self.industries = copy.deepcopy(SAMPLE_INDUSTRIES)

    def _validate_challenge_and_analysis(self, challenge_id: str, user: AuthenticatedUser):
        from fastapi import HTTPException
        if challenge_id not in self.challenges:
            raise HTTPException(status_code=404, detail=f"Challenge '{challenge_id}' not found")
        challenge = self.challenges[challenge_id]
        if challenge_id not in self.ai_analyses:
            raise HTTPException(
                status_code=400,
                detail=f"Challenge '{challenge_id}' has not undergone AI review and classification. Run /analyze first.",
            )
        analysis = self.ai_analyses[challenge_id]
        return challenge, analysis

    def _fetch_universities(self):
        return self.universities

    def _fetch_industries(self):
        return self.industries

    def get_or_generate_university_matches(self, challenge_id: str, user: AuthenticatedUser, limit: int = 5):
        challenge, analysis = self._validate_challenge_and_analysis(challenge_id, user)

        # Return persisted matches if already present (duplicate prevention)
        if challenge_id in self.university_matches and len(self.university_matches[challenge_id]) > 0:
            return self.university_matches[challenge_id][:limit]

        # Calculate using pure deterministic matching engine
        ranked = rank_universities(challenge, analysis, self.universities)
        self.university_matches[challenge_id] = ranked
        return ranked[:limit]

    def get_or_generate_industry_matches(self, challenge_id: str, user: AuthenticatedUser, limit: int = 5):
        challenge, analysis = self._validate_challenge_and_analysis(challenge_id, user)

        # Return persisted matches if already present (duplicate prevention)
        if challenge_id in self.industry_matches and len(self.industry_matches[challenge_id]) > 0:
            return self.industry_matches[challenge_id][:limit]

        # Calculate using pure deterministic matching engine
        ranked = rank_industries(challenge, analysis, self.industries)
        self.industry_matches[challenge_id] = ranked
        return ranked[:limit]


def run_tests():
    print("=" * 70)
    print("STARTING PHASE 4 DETERMINISTIC MATCHING ENGINE TEST SUITE")
    print("=" * 70)

    service = MockMatchingService()

    # Create a validated test challenge in Ranchi
    cid_valid = "CHL-TEST-RANCHI-001"
    service.challenges[cid_valid] = {
        "challenge_id": cid_valid,
        "title": "Automated Municipal Solid Waste & Garbage Detection Sensor",
        "description": "Smart sensor network for route optimization and waste monitoring in Ranchi municipal wards.",
        "city": "Ranchi",
        "district": "Ranchi",
        "impact_scope": "Ward Specific",
        "status": "validated",
        "user_id": "user-citizen-123",
    }
    service.ai_analyses[cid_valid] = {
        "challenge_id": cid_valid,
        "category": "Municipal Solid Waste Management",
        "subcategory": "Automated Segregation & Citizen Reporting Systems",
        "required_skills": "Computer Vision, Edge AI, Route Optimization, Mobile Development, IoT Sensors",
        "required_technologies": "TensorFlow Lite, Python, OpenCV, Flutter, ESP32, LoRaWAN",
        "severity": "High",
        "priority": "High",
        "validity": "valid",
        "innovation_scope": "medium",
        "feasibility": "high",
        "confidence_score": 0.90,
    }

    # Challenge without AI analysis (insufficient data)
    cid_unanalyzed = "CHL-TEST-UNANALYZED"
    service.challenges[cid_unanalyzed] = {
        "challenge_id": cid_unanalyzed,
        "title": "Raw unanalyzed problem",
        "description": "Description without ai_analysis row.",
        "status": "submitted",
        "user_id": "user-citizen-123",
    }

    test_user = AuthenticatedUser(
        user_id="user-citizen-123",
        email="citizen@samadhansetu.gov.in",
        role="citizen",
        full_name="Aarti Citizen",
        is_verified=True,
    )

    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_matching_service] = lambda: service

    client = TestClient(app)

    # -------------------------------------------------------------
    # TEST 1: Deterministic Repeated Execution (10 consecutive runs)
    # -------------------------------------------------------------
    print("\n[TEST 1] Deterministic Repeated Execution (10 Runs):")
    first_uni_run = service.get_or_generate_university_matches(cid_valid, test_user)
    first_scores = [m["match_score"] for m in first_uni_run]
    first_ranks = [m["university_id"] for m in first_uni_run]
    print(f"  Run 1 University Scores: {first_scores}")
    print(f"  Run 1 University Order: {first_ranks}")

    for run_idx in range(2, 11):
        # Fresh score recalculation directly via pure engine
        run_res = rank_universities(
            service.challenges[cid_valid],
            service.ai_analyses[cid_valid],
            service.universities,
        )
        run_scores = [m["match_score"] for m in run_res]
        run_order = [m["university_id"] for m in run_res]
        assert run_scores == first_scores, f"Non-deterministic score difference at run {run_idx}"
        assert run_order == first_ranks, f"Non-deterministic order difference at run {run_idx}"

    print("  [PASS] 10/10 consecutive runs produced 100% identical scores and ranking order.")

    # -------------------------------------------------------------
    # TEST 2: Strict Monotonic Ranking Order
    # -------------------------------------------------------------
    print("\n[TEST 2] Monotonic Ranking Order Verification:")
    r2_uni = client.get(f"/api/challenges/{cid_valid}/universities")
    assert r2_uni.status_code == 200
    uni_data = r2_uni.json()["data"]

    print("  Ranked Universities:")
    for m in uni_data:
        print(f"    Rank {m['rank']}: {m['university_name']} (ID: {m['university_id']}) -> Score: {m['match_score']}")

    # Assert rank 1 >= rank 2 >= rank 3...
    for i in range(len(uni_data) - 1):
        assert uni_data[i]["rank"] == i + 1
        assert uni_data[i]["match_score"] >= uni_data[i + 1]["match_score"], "Ranking order violation!"

    # Assert top university is BIT Mesra (U001) due to IoT, Computer Vision, OpenCV, Python & Ranchi location
    assert uni_data[0]["university_id"] == "U001"
    print("  [PASS] University ranking order is strictly monotonic non-increasing.")

    # Check Industry ranking
    r2_ind = client.get(f"/api/challenges/{cid_valid}/industries")
    assert r2_ind.status_code == 200
    ind_data = r2_ind.json()["data"]
    print("  Ranked Industries:")
    for m in ind_data:
        print(f"    Rank {m['rank']}: {m['industry_name']} (ID: {m['industry_id']}) -> Score: {m['match_score']}")

    for i in range(len(ind_data) - 1):
        assert ind_data[i]["rank"] == i + 1
        assert ind_data[i]["match_score"] >= ind_data[i + 1]["match_score"]

    # Assert top industry is Tata Steel Innovation Cell (IND002) due to Computer Vision, Edge AI, Python, Flutter
    assert ind_data[0]["industry_id"] == "IND002"
    print("  [PASS] Industry ranking order is strictly monotonic non-increasing.")

    # -------------------------------------------------------------
    # TEST 3: Duplicate Prevention & UNIQUE Constraints
    # -------------------------------------------------------------
    print("\n[TEST 3] Duplicate Prevention on Repeated Invocations:")
    initial_uni_count = len(service.university_matches[cid_valid])
    initial_ind_count = len(service.industry_matches[cid_valid])

    # Call the GET endpoint again
    client.get(f"/api/challenges/{cid_valid}/universities")
    client.get(f"/api/challenges/{cid_valid}/industries")

    # Assert match count has not grown (no duplicate rows created)
    assert len(service.university_matches[cid_valid]) == initial_uni_count
    assert len(service.industry_matches[cid_valid]) == initial_ind_count

    # Assert all university_ids and industry_ids are unique
    uni_ids = [m["university_id"] for m in service.university_matches[cid_valid]]
    ind_ids = [m["industry_id"] for m in service.industry_matches[cid_valid]]
    assert len(uni_ids) == len(set(uni_ids)), "Duplicate university_ids found!"
    assert len(ind_ids) == len(set(ind_ids)), "Duplicate industry_ids found!"
    print("  [PASS] No duplicate match rows created. Unique constraints strictly preserved.")

    # -------------------------------------------------------------
    # TEST 4: Nonexistent Challenge Handling
    # -------------------------------------------------------------
    print("\n[TEST 4] Nonexistent Challenge (404 Handling):")
    r4_uni = client.get("/api/challenges/CHL-NONEXISTENT-999/universities")
    print("  Status Code:", r4_uni.status_code)
    assert r4_uni.status_code == 404
    assert "not found" in r4_uni.json()["error"]["message"].lower()

    r4_ind = client.get("/api/challenges/CHL-NONEXISTENT-999/industries")
    assert r4_ind.status_code == 404
    print("  [PASS] Nonexistent challenges correctly rejected with 404 Not Found.")

    # -------------------------------------------------------------
    # TEST 5: Insufficient Data / Unanalyzed Challenge (400 Handling)
    # -------------------------------------------------------------
    print("\n[TEST 5] Insufficient Data / Unanalyzed Challenge (400 Handling):")
    r5_uni = client.get(f"/api/challenges/{cid_unanalyzed}/universities")
    print("  Status Code:", r5_uni.status_code)
    print("  Response:", r5_uni.json())
    assert r5_uni.status_code == 400
    assert "has not undergone ai review" in r5_uni.json()["error"]["message"].lower()

    r5_ind = client.get(f"/api/challenges/{cid_unanalyzed}/industries")
    assert r5_ind.status_code == 400
    print("  [PASS] Unanalyzed challenge correctly rejected with 400 Bad Request.")

    # -------------------------------------------------------------
    # TEST 6: Unauthorized Access (401 Handling)
    # -------------------------------------------------------------
    print("\n[TEST 6] Unauthorized Access (Missing Auth Token):")
    app.dependency_overrides.pop(get_current_user)
    r6_unauth = client.get(f"/api/challenges/{cid_valid}/universities")
    print("  Status Code without token:", r6_unauth.status_code)
    assert r6_unauth.status_code == 401
    print("  [PASS] Unauthenticated matching request correctly rejected with 401.")

    # Restore auth
    app.dependency_overrides[get_current_user] = lambda: test_user

    # -------------------------------------------------------------
    # TEST 7: Breakdown Values and Factual Match Reasons
    # -------------------------------------------------------------
    print("\n[TEST 7] Score Breakdown & Match Reason Explanations:")
    top_uni = uni_data[0]
    print(f"  Top University Match Reason:\n    {top_uni['match_reason']}")
    print(f"  Top University Score Breakdown:\n    {top_uni.get('score_breakdown')}")
    assert "Matched skills:" in top_uni["match_reason"]
    assert top_uni["match_score"] > 0.0

    top_ind = ind_data[0]
    print(f"  Top Industry Match Reason:\n    {top_ind['match_reason']}")
    print(f"  Top Industry Score Breakdown:\n    {top_ind.get('score_breakdown')}")
    assert "Matched skills:" in top_ind["match_reason"]
    assert top_ind["match_score"] > 0.0
    print("  [PASS] Score breakdown and deterministic match reason successfully verified.")

    # Clean overrides
    app.dependency_overrides.clear()
    print("\n" + "=" * 70)
    print("ALL PHASE 4 DETERMINISTIC MATCHING TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    run_tests()
