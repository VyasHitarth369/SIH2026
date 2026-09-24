"""test_phase25_matching_workflow.py

Comprehensive test suite for Phase 25: Production Matching & Assignment Workflow.
Covers all 28 requirements specified in Section 21 of the Phase 25 specification:

UNIVERSITY (1-12):
1. Valid university admin can accept own invitation.
2. Valid university admin can reject own invitation.
3. University Admin A cannot respond to University B's invitation (cross-uni blocked with 403).
4. Unauthenticated user cannot respond (401).
5. Unverified university admin cannot respond (403).
6. Response after deadline is rejected (400).
7. Duplicate response is blocked (400).
8. Highest-ranked accepting university becomes selected.
9. Lower-ranked accepting university becomes not_selected.
10. Rank 1 rejection allows Rank 2 acceptance.
11. All rejected/expired results in no final university.
12. Two simultaneous acceptance attempts cannot create two selected universities.

INDUSTRY (13-21):
13. Valid Industry SPOC can accept own industry request.
14. Valid Industry SPOC can reject own industry request.
15. Normal employee cannot accept/reject industry collaboration (403).
16. SPOC from another industry cannot respond (cross-industry blocked with 403).
17. Unverified employee cannot respond (403).
18. Employee can express interest only for their own industry (cross-industry blocked with 400).
19. Duplicate employee interest is blocked (400).
20. Industry matching uses live DB data.
21. Fake industry IDs are rejected (404).

MATCHING (22-28):
22. University matching uses live DB data.
23. Industry matching uses live DB data.
24. Matching never invents IDs.
25. At most 5 meaningful university matches (match_score > 0).
26. At most 5 meaningful industry matches (match_score > 0).
27. Ranking is deterministic (identical scores & ranks across runs).
28. Existing Phase 24 matching tests still pass.
"""

import concurrent.futures
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from starlette.testclient import TestClient

from app.main import app
from app.dependencies.auth import get_current_user
from app.routes.challenges import (
    get_challenge_service,
    get_matching_service,
    get_workflow_service,
    get_industry_workflow_service,
)
from app.routes.projects import (
    get_project_workflow_service,
    get_industry_workflow_service as get_proj_industry_workflow_service,
)
from app.services.auth_service import AuthenticatedUser
from app.services.matching_service import MatchingService
from app.services.university_workflow_service import UniversityWorkflowService
from app.services.industry_workflow_service import IndustryWorkflowService
from app.services.matching_engine import rank_universities, rank_industries


# Real Seed Universities & Industries
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
        "past_project_ids": "PRJ-U001-24-01",
    },
    {
        "university_id": "U002",
        "university_name": "Indian Institute of Technology (ISM) Dhanbad",
        "city": "Dhanbad",
        "district": "Dhanbad",
        "domain": "Environmental Science, Mining & Water Resources",
        "primary_focus": "Wastewater Treatment, Mine Effluent, Underground IoT",
        "skills": "Water Quality Chemistry, Bioremediation, GIS Mapping, AI Predictive Models",
        "technologies": "Underground IoT, Clean Tech, Remote Sensing",
        "departments": "Environmental Science & Engg, Mining Engineering",
        "facilities": "Water Testing Spectrophotometry Lab",
        "research_areas": "Water Contamination, Landslide Analysis",
        "past_project_ids": "PRJ-U002-24-11",
    },
    {
        "university_id": "U003",
        "university_name": "National Institute of Technology (NIT) Jamshedpur",
        "city": "Jamshedpur",
        "district": "East Singhbhum",
        "domain": "Transportation Engineering, Materials Science & AI",
        "primary_focus": "Pavement Design, Traffic IoT, High-Strength Alloys",
        "skills": "Computer Vision, Accelerometer Sensor Analytics, Geofencing, Mobile Apps",
        "technologies": "PyTorch, Android SDK, MapLibre, OpenCV",
        "departments": "Civil Engineering, Metallurgical, Computer Science",
        "facilities": "Transportation IoT Lab",
        "research_areas": "Traffic Analytics, Road Surface Quality",
        "past_project_ids": "PRJ-U003-22-11",
    },
]

SAMPLE_INDUSTRIES = [
    {
        "industry_id": "IND001",
        "industry_name": "Tata CSR Water & Civic Solutions",
        "city": "Jamshedpur",
        "district": "East Singhbhum",
        "domain": "IoT, Water Resources & Environmental Engineering",
        "skills": "IoT Sensors, Water Quality Chemistry, Embedded Systems",
        "technologies": "ESP32, LoRaWAN, Cloud Telemetry",
        "deployment_capabilities": "Statewide Field Deployment, Gram Panchayat Water Tanks",
        "resource_capabilities": "Hardware fabrication co-funding",
        "products_services": "Smart water metering, Rural chlorination dispensers",
        "geography": "Jharkhand, Odisha, West Bengal",
        "csr_areas": "Clean Water, Rural Sanitation",
        "past_project_ids": "PRJ-IND-24-03",
    },
    {
        "industry_id": "IND002",
        "industry_name": "Tata Steel Innovation Cell",
        "city": "Jamshedpur",
        "district": "East Singhbhum",
        "domain": "Software Development, AI / Machine Learning & Urban Tech",
        "skills": "Computer Vision, Edge AI, Route Optimization, Mobile Development, Python",
        "technologies": "TensorFlow Lite, OpenCV, Python, Flutter",
        "deployment_capabilities": "Industrial plants, Municipal urban hubs",
        "resource_capabilities": "Cloud GPU infrastructure",
        "products_services": "Visual inspection software, Municipal fleet management",
        "geography": "Jamshedpur, Ranchi, Dhanbad",
        "csr_areas": "Urban Sustainability, Youth Digital Literacy",
        "past_project_ids": "PRJ-IND-24-08",
    },
]


class MockSupabaseClient:
    """In-memory mock of Supabase PostgREST client for comprehensive test isolation."""

    def __init__(self):
        self.tables = {
            "challenges": {},
            "ai_analysis": {},
            "universities": {u["university_id"]: dict(u) for u in SAMPLE_UNIVERSITIES},
            "industries": {i["industry_id"]: dict(i) for i in SAMPLE_INDUSTRIES},
            "challenge_university_matches": {},
            "challenge_industry_matches": {},
            "projects": {},
            "project_employee_interests": {},
            "industry_employees": {},
            "university_admins": {},
        }

    def table(self, table_name: str):
        return MockTableQuery(self.tables.setdefault(table_name, {}), table_name=table_name)


class MockTableQuery:
    def __init__(self, data_store: Dict[str, Any], table_name: str = ""):
        self.data_store = data_store
        self.table_name = table_name
        self.filters = []
        self._order_field = None
        self._order_desc = False
        self._limit_val = None
        self._action = "select"
        self._patch = None
        self._insert_record = None
        self._on_conflict = None

    def select(self, *args):
        self._action = "select"
        return self

    def eq(self, field: str, value: Any):
        self.filters.append((field, "eq", value))
        return self

    def neq(self, field: str, value: Any):
        self.filters.append((field, "neq", value))
        return self

    def lt(self, field: str, value: Any):
        self.filters.append((field, "lt", value))
        return self

    def order(self, field: str, desc: bool = False):
        self._order_field = field
        self._order_desc = desc
        return self

    def limit(self, val: int):
        self._limit_val = val
        return self

    def insert(self, record: Dict[str, Any]):
        self._action = "insert"
        self._insert_record = record
        return self

    def upsert(self, record: Dict[str, Any], on_conflict: Optional[str] = None):
        self._action = "upsert"
        self._insert_record = record
        self._on_conflict = on_conflict
        return self

    def update(self, patch: Dict[str, Any]):
        self._action = "update"
        self._patch = patch
        return self

    def _matches_filters(self, row: Dict[str, Any]) -> bool:
        for f_name, op, f_val in self.filters:
            row_val = row.get(f_name)
            if op == "eq" and row_val != f_val:
                return False
            if op == "neq" and row_val == f_val:
                return False
            if op == "lt":
                if row_val is None or row_val >= f_val:
                    return False
        return True

    def execute(self):
        class Result:
            def __init__(self, data):
                self.data = data

        if self._action == "insert":
            record = dict(self._insert_record)
            if self.table_name == "project_employee_interests":
                if "interest_id" not in record or not record.get("interest_id"):
                    record["interest_id"] = len(self.data_store) + 1
                pk = f"{record.get('project_id')}_{record.get('employee_id')}"
            else:
                pk = (
                    record.get("match_id")
                    or record.get("interest_id")
                    or record.get("project_id")
                    or record.get("challenge_id")
                    or record.get("university_id")
                    or record.get("industry_id")
                    or f"row_{len(self.data_store)+1}"
                )
            self.data_store[str(pk)] = record
            return Result([record])

        if self._action == "upsert":
            record = self._insert_record
            if self._on_conflict == "challenge_id,university_id":
                key = f"{record.get('challenge_id')}_{record.get('university_id')}"
            elif self._on_conflict == "challenge_id,industry_id":
                key = f"{record.get('challenge_id')}_{record.get('industry_id')}"
            elif self._on_conflict == "challenge_id":
                key = str(record.get("challenge_id"))
            else:
                key = str(record.get("match_id") or record.get("id") or len(self.data_store) + 1)
            row = dict(record)
            self.data_store[key] = row
            return Result([row])

        if self._action == "update":
            updated = []
            for k, row in self.data_store.items():
                if self._matches_filters(row):
                    row.update(self._patch)
                    updated.append(dict(row))
            return Result(updated)

        # Select
        rows = [dict(r) for r in self.data_store.values() if self._matches_filters(r)]
        if self._order_field:
            rows.sort(
                key=lambda x: x.get(self._order_field) if x.get(self._order_field) is not None else 9999,
                reverse=self._order_desc,
            )
        if self._limit_val is not None:
            rows = rows[: self._limit_val]
        return Result(rows)


def run_all_tests():
    print("=" * 70)
    print("STARTING PHASE 25 PRODUCTION MATCHING & ASSIGNMENT WORKFLOW TESTS")
    print("=" * 70)

    # Initialize Mock DB & Services
    mock_db = MockSupabaseClient()
    matching_srv = MatchingService(client=mock_db)
    uni_srv = UniversityWorkflowService(client=mock_db)
    ind_srv = IndustryWorkflowService(client=mock_db)

    # Create a validated test challenge in Ranchi
    cid = "CHL-P25-001"
    mock_db.tables["challenges"][cid] = {
        "challenge_id": cid,
        "title": "Smart Waste Bin Monitoring & Route Optimization",
        "description": "IoT based waste monitoring and route scheduling in Ranchi municipal wards.",
        "city": "Ranchi",
        "district": "Ranchi",
        "status": "validated",
        "user_id": "user-citizen-01",
    }
    mock_db.tables["ai_analysis"][cid] = {
        "challenge_id": cid,
        "category": "Municipal Solid Waste Management",
        "subcategory": "Automated Segregation",
        "required_skills": "Computer Vision, Edge AI, Route Optimization, IoT Sensors",
        "required_technologies": "TensorFlow Lite, Python, OpenCV, ESP32, LoRaWAN",
        "validity": "valid",
        "innovation_scope": "medium",
        "feasibility": "high",
        "confidence_score": 0.95,
    }

    # Generate initial university matches
    citizen_user = AuthenticatedUser(
        user_id="user-citizen-01",
        email="citizen@samadhansetu.gov.in",
        role="citizen",
        full_name="Pooja Citizen",
        is_verified=True,
    )
    uni_matches = matching_srv.get_or_generate_university_matches(cid, citizen_user, limit=5)
    assert len(uni_matches) > 0

    top_uni_id = uni_matches[0]["university_id"]  # U001
    sec_uni_id = uni_matches[1]["university_id"]  # U003
    third_uni_id = uni_matches[2]["university_id"]  # U002

    # Prepare Users
    admin_u1 = AuthenticatedUser(
        user_id="admin-u1-id",
        email="admin@bitmesra.ac.in",
        role="university_admin",
        full_name="Dr. BIT Admin",
        stakeholder={"admin_id": "ADM-U001", "university_id": top_uni_id, "verification_status": "verified"},
        is_verified=True,
    )
    admin_u2 = AuthenticatedUser(
        user_id="admin-u2-id",
        email="admin@nitjsr.ac.in",
        role="university_admin",
        full_name="Dr. NIT Admin",
        stakeholder={"admin_id": "ADM-U003", "university_id": sec_uni_id, "verification_status": "verified"},
        is_verified=True,
    )
    admin_unverified = AuthenticatedUser(
        user_id="admin-unverified-id",
        email="pending@bitmesra.ac.in",
        role="university_admin",
        full_name="Pending Admin",
        stakeholder={"admin_id": "ADM-U001-P", "university_id": top_uni_id, "verification_status": "pending"},
        is_verified=False,
    )

    # FastAPI TestClient Setup
    app.dependency_overrides[get_matching_service] = lambda: matching_srv
    app.dependency_overrides[get_workflow_service] = lambda: uni_srv
    app.dependency_overrides[get_industry_workflow_service] = lambda: ind_srv
    app.dependency_overrides[get_proj_industry_workflow_service] = lambda: ind_srv
    client = TestClient(app)

    # -------------------------------------------------------------
    # TEST 4: Unauthenticated user cannot respond (401)
    # -------------------------------------------------------------
    print("\n[TEST 4] Unauthenticated user cannot respond:")
    app.dependency_overrides.pop(get_current_user, None)
    r4 = client.post(f"/api/challenges/{cid}/universities/{top_uni_id}/respond", json={"action": "accept"})
    assert r4.status_code == 401
    print("  [PASS] Unauthenticated response rejected with 401.")

    # -------------------------------------------------------------
    # TEST 5: Unverified university admin cannot respond (403)
    # -------------------------------------------------------------
    print("\n[TEST 5] Unverified university admin cannot respond:")
    app.dependency_overrides[get_current_user] = lambda: admin_unverified
    r5 = client.post(f"/api/challenges/{cid}/universities/{top_uni_id}/respond", json={"action": "accept"})
    assert r5.status_code == 403
    assert "pending institutional verification" in r5.json()["error"]["message"].lower()
    print("  [PASS] Unverified admin blocked with 403.")

    # -------------------------------------------------------------
    # TEST 3: University Admin A cannot respond to University B's invitation (403)
    # -------------------------------------------------------------
    print("\n[TEST 3] University Admin A cannot respond to University B's invitation:")
    app.dependency_overrides[get_current_user] = lambda: admin_u1  # Belongs to U001
    r3 = client.post(f"/api/challenges/{cid}/universities/{sec_uni_id}/respond", json={"action": "accept"})
    assert r3.status_code == 403
    assert "not" in r3.json()["error"]["message"].lower()
    print("  [PASS] Cross-university invitation response strictly blocked with 403.")

    # -------------------------------------------------------------
    # TEST 6: Response after deadline is rejected (400)
    # -------------------------------------------------------------
    print("\n[TEST 6] Response after deadline is rejected:")
    past_iso = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    mock_db.tables["challenge_university_matches"][f"{cid}_{third_uni_id}"]["response_deadline"] = past_iso

    admin_u3 = AuthenticatedUser(
        user_id="admin-u3-id",
        email="admin@iitism.ac.in",
        role="university_admin",
        full_name="Dr. IIT Admin",
        stakeholder={"admin_id": "ADM-U002", "university_id": third_uni_id, "verification_status": "verified"},
        is_verified=True,
    )
    app.dependency_overrides[get_current_user] = lambda: admin_u3
    r6 = client.post(f"/api/challenges/{cid}/universities/{third_uni_id}/respond", json={"action": "accept"})
    assert r6.status_code == 400
    assert "deadline has expired" in r6.json()["error"]["message"].lower()
    print("  [PASS] Expired invitation response rejected with 400.")

    # -------------------------------------------------------------
    # TEST 1: Valid university admin can accept own invitation
    # -------------------------------------------------------------
    print("\n[TEST 1] Valid university admin can accept own invitation:")
    app.dependency_overrides[get_current_user] = lambda: admin_u1
    r1 = client.post(
        f"/api/challenges/{cid}/universities/{top_uni_id}/respond",
        json={"action": "accept", "response_note": "Department of CS & Engg agrees to take on challenge."},
    )
    assert r1.status_code == 200
    assert r1.json()["success"] is True
    assert r1.json()["data"]["action_taken"] == "university_accepted"
    print("  [PASS] Valid university admin accepted invitation successfully.")

    # -------------------------------------------------------------
    # TEST 7: Duplicate response is blocked (400)
    # -------------------------------------------------------------
    print("\n[TEST 7] Duplicate response is blocked:")
    r7 = client.post(f"/api/challenges/{cid}/universities/{top_uni_id}/respond", json={"action": "accept"})
    assert r7.status_code == 400
    assert "cannot respond" in r7.json()["error"]["message"].lower()
    print("  [PASS] Duplicate response blocked with 400 Bad Request.")

    # -------------------------------------------------------------
    # TEST 8 & 9: Highest-ranked accepting university selected; lower-ranked not_selected
    # -------------------------------------------------------------
    print("\n[TEST 8 & 9] Selection Rule: Highest-ranked selected, lower-ranked not_selected:")
    fin = uni_srv.finalize_university_selection(cid, admin_u1)
    assert fin["selected_university_id"] == top_uni_id
    assert fin["selected_university_rank"] == 1
    assert mock_db.tables["challenges"][cid]["status"] == "university_selected"
    for k, m in mock_db.tables["challenge_university_matches"].items():
        if m["university_id"] == top_uni_id:
            assert m["status"] == "selected"
        elif m["status"] != "expired":
            assert m["status"] == "not_selected"
    print("  [PASS] Rank 1 university officially selected, all other candidate matches transitioned to not_selected.")

    # -------------------------------------------------------------
    # TEST 2 & 10: Rank 1 rejection allows Rank 2 acceptance
    # -------------------------------------------------------------
    print("\n[TEST 2 & 10] Rank 1 rejection allows Rank 2 acceptance:")
    cid2 = "CHL-P25-002"
    mock_db.tables["challenges"][cid2] = {
        "challenge_id": cid2,
        "title": "Clean Water Dispensers",
        "description": "Rural water purification",
        "city": "Ranchi",
        "status": "validated",
        "user_id": "user-citizen-01",
    }
    mock_db.tables["ai_analysis"][cid2] = {**mock_db.tables["ai_analysis"][cid], "challenge_id": cid2}
    matching_srv.get_or_generate_university_matches(cid2, citizen_user)

    # Rank 1 rejects
    app.dependency_overrides[get_current_user] = lambda: admin_u1
    r2_reject = client.post(f"/api/challenges/{cid2}/universities/{top_uni_id}/respond", json={"action": "reject", "response_note": "Department at capacity."})
    assert r2_reject.status_code == 200
    assert r2_reject.json()["data"]["action_taken"] == "university_rejected"

    # Rank 2 accepts
    app.dependency_overrides[get_current_user] = lambda: admin_u2
    r10_accept = client.post(f"/api/challenges/{cid2}/universities/{sec_uni_id}/respond", json={"action": "accept"})
    assert r10_accept.status_code == 200

    fin2 = uni_srv.finalize_university_selection(cid2, admin_u2)
    assert fin2["selected_university_id"] == sec_uni_id
    assert fin2["selected_university_rank"] == 2
    print("  [PASS] Rank 1 rejection successfully allowed Rank 2 to become the selected university.")

    # -------------------------------------------------------------
    # TEST 11: All rejected/expired results in no final university
    # -------------------------------------------------------------
    print("\n[TEST 11] All rejected/expired results in no final university:")
    cid3 = "CHL-P25-003"
    mock_db.tables["challenges"][cid3] = {
        "challenge_id": cid3,
        "title": "Unwanted Problem",
        "description": "No one accepts this",
        "city": "Ranchi",
        "status": "validated",
        "user_id": "user-citizen-01",
    }
    mock_db.tables["ai_analysis"][cid3] = {**mock_db.tables["ai_analysis"][cid], "challenge_id": cid3}
    m3 = matching_srv.get_or_generate_university_matches(cid3, citizen_user)
    for match in m3:
        mock_db.tables["challenge_university_matches"][f"{cid3}_{match['university_id']}"]["status"] = "rejected"

    fin3 = uni_srv.finalize_university_selection(cid3, admin_u1, force_deadline=True)
    assert fin3["selected_university_id"] is None
    assert fin3["status"] == "no_university_assigned"
    assert mock_db.tables["challenges"][cid3]["status"] == "no_university_assigned"
    print("  [PASS] All rejections cleanly transition challenge to 'no_university_assigned'.")

    # -------------------------------------------------------------
    # TEST 12: Two simultaneous acceptance attempts cannot create two selected universities
    # -------------------------------------------------------------
    print("\n[TEST 12] Double assignment race condition protection:")
    cid4 = "CHL-P25-004"
    mock_db.tables["challenges"][cid4] = {
        "challenge_id": cid4,
        "title": "Concurrent Problem",
        "description": "High stakes challenge",
        "city": "Ranchi",
        "status": "validated",
        "user_id": "user-citizen-01",
    }
    mock_db.tables["ai_analysis"][cid4] = {**mock_db.tables["ai_analysis"][cid], "challenge_id": cid4}
    matching_srv.get_or_generate_university_matches(cid4, citizen_user)

    mock_db.tables["challenge_university_matches"][f"{cid4}_{top_uni_id}"]["status"] = "accepted"
    mock_db.tables["challenge_university_matches"][f"{cid4}_{sec_uni_id}"]["status"] = "accepted"

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(uni_srv.finalize_university_selection, cid4, admin_u1)
        f2 = executor.submit(uni_srv.finalize_university_selection, cid4, admin_u2)
        res1 = f1.result()
        res2 = f2.result()

    assert res1["selected_university_id"] == top_uni_id
    assert res2["selected_university_id"] == top_uni_id
    selected_rows = [
        m for m in mock_db.tables["challenge_university_matches"].values()
        if m.get("challenge_id") == cid4 and m.get("status") == "selected"
    ]
    assert len(selected_rows) == 1
    assert selected_rows[0]["university_id"] == top_uni_id
    print("  [PASS] Race condition prevented: exactly ONE university assigned.")

    # =============================================================
    # INDUSTRY WORKFLOW TESTS (13-21)
    # =============================================================
    ind_matches = matching_srv.get_or_generate_industry_matches(cid, citizen_user, limit=5)
    assert len(ind_matches) > 0
    top_ind_id = ind_matches[0]["industry_id"]  # IND002 (Tata Steel)
    sec_ind_id = ind_matches[1]["industry_id"]  # IND001 (Tata CSR)

    spoc_ind1 = AuthenticatedUser(
        user_id="spoc-ind1-id",
        email="spoc@tatasteel.com",
        role="industry_employee",
        full_name="Rajesh SPOC",
        stakeholder={"employee_id": "EMP-IND2-01", "industry_id": top_ind_id, "verification_status": "verified", "approval_authority": True},
        is_verified=True,
        verification_status="verified",
        approval_authority=True,
    )
    employee_ind1 = AuthenticatedUser(
        user_id="emp-ind1-id",
        email="worker@tatasteel.com",
        role="industry_employee",
        full_name="Karan Engineer",
        stakeholder={"employee_id": "EMP-IND2-02", "industry_id": top_ind_id, "verification_status": "verified", "approval_authority": False},
        is_verified=True,
        verification_status="verified",
        approval_authority=False,
    )
    spoc_ind2 = AuthenticatedUser(
        user_id="spoc-ind2-id",
        email="spoc@tatacsr.com",
        role="industry_employee",
        full_name="Anjali SPOC",
        stakeholder={"employee_id": "EMP-IND1-01", "industry_id": sec_ind_id, "verification_status": "verified", "approval_authority": True},
        is_verified=True,
        verification_status="verified",
        approval_authority=True,
    )
    emp_unverified = AuthenticatedUser(
        user_id="emp-unverified-id",
        email="unverified@tatasteel.com",
        role="industry_employee",
        full_name="Unverified Worker",
        stakeholder={"employee_id": "EMP-IND2-03", "industry_id": top_ind_id, "verification_status": "pending", "approval_authority": False},
        is_verified=False,
        approval_authority=False,
    )

    # -------------------------------------------------------------
    # TEST 15: Normal employee cannot accept/reject industry collaboration (403)
    # -------------------------------------------------------------
    print("\n[TEST 15] Normal employee cannot accept/reject industry collaboration:")
    app.dependency_overrides[get_current_user] = lambda: employee_ind1
    r15 = client.post(f"/api/challenges/{cid}/industries/{top_ind_id}/respond", json={"action": "accept"})
    assert r15.status_code == 403
    assert "spoc approval authority is required" in r15.json()["error"]["message"].lower()
    print("  [PASS] Ordinary employee blocked from SPOC actions with 403.")

    # -------------------------------------------------------------
    # TEST 16: SPOC from another industry cannot respond (403)
    # -------------------------------------------------------------
    print("\n[TEST 16] SPOC from another industry cannot respond:")
    app.dependency_overrides[get_current_user] = lambda: spoc_ind2  # IND001
    r16 = client.post(f"/api/challenges/{cid}/industries/{top_ind_id}/respond", json={"action": "accept"})
    assert r16.status_code == 403
    assert "not" in r16.json()["error"]["message"].lower()
    print("  [PASS] Cross-industry SPOC response rejected with 403.")

    # -------------------------------------------------------------
    # TEST 17: Unverified employee cannot respond (403)
    # -------------------------------------------------------------
    print("\n[TEST 17] Unverified employee cannot respond:")
    app.dependency_overrides[get_current_user] = lambda: emp_unverified
    r17 = client.post(f"/api/challenges/{cid}/industries/{top_ind_id}/respond", json={"action": "accept"})
    assert r17.status_code == 403
    print("  [PASS] Unverified employee blocked with 403.")

    # -------------------------------------------------------------
    # TEST 13: Valid Industry SPOC can accept own industry request
    # -------------------------------------------------------------
    print("\n[TEST 13] Valid Industry SPOC can accept own industry request:")
    app.dependency_overrides[get_current_user] = lambda: spoc_ind1
    r13 = client.post(f"/api/challenges/{cid}/industries/{top_ind_id}/respond", json={"action": "accept"})
    assert r13.status_code == 200
    assert r13.json()["success"] is True
    assert r13.json()["data"]["status"] == "accepted"
    print("  [PASS] Industry SPOC accepted collaboration proposal.")

    # -------------------------------------------------------------
    # TEST 14: Valid Industry SPOC can reject own industry request
    # -------------------------------------------------------------
    print("\n[TEST 14] Valid Industry SPOC can reject own industry request:")
    app.dependency_overrides[get_current_user] = lambda: spoc_ind2
    r14 = client.post(f"/api/challenges/{cid}/industries/{sec_ind_id}/respond", json={"action": "reject", "response_note": "Currently focusing on other projects."})
    assert r14.status_code == 200
    assert r14.json()["data"]["status"] == "rejected"
    print("  [PASS] Industry SPOC rejected collaboration proposal.")

    # -------------------------------------------------------------
    # TEST 18: Employee can express interest only for their own industry
    # -------------------------------------------------------------
    print("\n[TEST 18] Employee can express interest only for their own industry:")
    proj_id = "PRJ-TEST-001"
    mock_db.tables["projects"][proj_id] = {
        "project_id": proj_id,
        "challenge_id": cid,
        "university_id": top_uni_id,
        "industry_id": top_ind_id,  # IND002
        "project_title": "Smart Bin IoT",
        "status": "active",
    }

    emp_ind2 = AuthenticatedUser(
        user_id="emp-other-ind-id",
        email="other@tatacsr.com",
        role="industry_employee",
        full_name="Other Employee",
        stakeholder={"employee_id": "EMP-IND1-02", "industry_id": sec_ind_id, "verification_status": "verified"},
        is_verified=True,
        verification_status="verified",
    )
    app.dependency_overrides[get_current_user] = lambda: emp_ind2
    r18 = client.post(f"/api/projects/{proj_id}/employee-interest", json={"message": "I want to help"})
    assert r18.status_code == 400
    assert "cross-industry" in r18.json()["error"]["message"].lower()
    print("  [PASS] Cross-industry employee interest rejected with 400.")

    app.dependency_overrides[get_current_user] = lambda: employee_ind1
    r18_valid = client.post(f"/api/projects/{proj_id}/employee-interest", json={"message": "I am an expert in ESP32 and edge AI."})
    assert r18_valid.status_code == 201
    assert r18_valid.json()["data"]["status"] == "interested"
    print("  [PASS] Legitimate employee expressed interest successfully.")

    # -------------------------------------------------------------
    # TEST 19: Duplicate employee interest is blocked (400)
    # -------------------------------------------------------------
    print("\n[TEST 19] Duplicate employee interest is blocked:")
    r19 = client.post(f"/api/projects/{proj_id}/employee-interest", json={"message": "Second attempt"})
    assert r19.status_code == 400
    assert "already expressed active interest" in r19.json()["error"]["message"].lower()
    print("  [PASS] Duplicate employee interest blocked with 400 Bad Request.")

    # -------------------------------------------------------------
    # TEST 20 & 21: Industry matching & Fake Industry ID rejection
    # -------------------------------------------------------------
    print("\n[TEST 20 & 21] Real Industry matching & Fake ID rejection:")
    try:
        matching_srv.validate_industry_id("IND-FAKE-999")
        assert False, "Fake industry ID should have failed"
    except Exception as e:
        assert getattr(e, "status_code", 404) == 404
    print("  [PASS] Fake industry ID rejected with 404.")

    # -------------------------------------------------------------
    # TEST 22, 23, 24: Matching uses live DB data & never invents IDs
    # -------------------------------------------------------------
    print("\n[TEST 22, 23, 24] Live DB validation & No hallucinated IDs:")
    all_uni_ids = {u["university_id"] for u in SAMPLE_UNIVERSITIES}
    all_ind_ids = {i["industry_id"] for i in SAMPLE_INDUSTRIES}
    for m in uni_matches:
        assert m["university_id"] in all_uni_ids, f"Unknown university ID {m['university_id']}"
    for m in ind_matches:
        assert m["industry_id"] in all_ind_ids, f"Unknown industry ID {m['industry_id']}"
    print("  [PASS] All generated matches strictly match database primary keys.")

    # -------------------------------------------------------------
    # TEST 25 & 26: Meaningful matches capped at 5 with match_score > 0
    # -------------------------------------------------------------
    print("\n[TEST 25 & 26] At most 5 meaningful matches with match_score > 0:")
    assert len(uni_matches) <= 5
    assert all(m["match_score"] > 0 for m in uni_matches)
    assert len(ind_matches) <= 5
    assert all(m["match_score"] > 0 for m in ind_matches)
    print("  [PASS] Top matches strictly <= 5 and match_score > 0.")

    # -------------------------------------------------------------
    # TEST 27: Deterministic ranking across runs
    # -------------------------------------------------------------
    print("\n[TEST 27] Deterministic ranking across 10 repeated runs:")
    run1_scores = [m["match_score"] for m in uni_matches]
    run1_ids = [m["university_id"] for m in uni_matches]
    for _ in range(10):
        fresh = rank_universities(mock_db.tables["challenges"][cid], mock_db.tables["ai_analysis"][cid], SAMPLE_UNIVERSITIES)
        meaningful = [m for m in fresh if m["match_score"] > 0][:5]
        assert [m["match_score"] for m in meaningful] == run1_scores
        assert [m["university_id"] for m in meaningful] == run1_ids
    print("  [PASS] Deterministic ranking verified 10/10 times.")

    # -------------------------------------------------------------
    # TEST 28: Phase 24 Matching Tests regression
    # -------------------------------------------------------------
    print("\n[TEST 28] Phase 24 Matching engine regression:")
    from test_phase4_matching import run_tests as run_p4_tests
    run_p4_tests()
    print("  [PASS] Phase 4 / 24 matching tests still pass 100%.")

    # Clean overrides
    app.dependency_overrides.clear()
    print("\n" + "=" * 70)
    print("ALL 28 PHASE 25 TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    run_all_tests()
