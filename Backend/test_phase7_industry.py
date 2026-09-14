"""test_phase7_industry.py

Comprehensive test suite for Phase 7: Industry Collaboration Workflow:
1. Industry SPOC Access Control & Collaboration Response (accept/reject on challenge match)
2. Ordinary Employee vs SPOC Authority Restrictions (designation alone does NOT confer authority)
3. Strict Institutional Employee Boundaries (cross-industry interest rejection)
4. Duplicate Interest Expression Prevention & Reactivation Lifecycle
5. Anti-Self-Selection & SPOC Selection Authority
6. Interest Hydration & Project Stakeholder Visibility
"""

import copy
from typing import Any, Dict, List, Optional
from starlette.testclient import TestClient

from app.main import app
from app.dependencies.auth import get_current_user, get_current_user_optional
from app.routes.challenges import get_industry_workflow_service as get_ind_svc_challenges
from app.routes.projects import get_industry_workflow_service as get_ind_svc_projects
from app.services.auth_service import AuthenticatedUser
from app.services.industry_workflow_service import IndustryWorkflowService


# =============================================================================
# In-Memory Mock Database for Hermetic Testing
# =============================================================================
class MockSupabaseDB:
    def __init__(self):
        self.tables = {
            "challenges": [
                {
                    "challenge_id": "CH-IND-001",
                    "title": "Industrial Effluent Real-Time Detection Sensor Mesh",
                    "description": "Sensors to monitor and treat industrial runoff in river canals.",
                    "status": "validated",
                }
            ],
            "industries": [
                {
                    "industry_id": "IND001",
                    "industry_name": "Tata CSR Water & Civic Solutions",
                    "city": "Jamshedpur",
                },
                {
                    "industry_id": "IND002",
                    "industry_name": "Tata Steel Innovation Cell",
                    "city": "Jamshedpur",
                },
            ],
            "challenge_industry_matches": [
                {
                    "match_id": 1,
                    "challenge_id": "CH-IND-001",
                    "industry_id": "IND001",
                    "rank": 1,
                    "match_score": 85.5,
                    "match_reason": "High IoT and water treatment alignment",
                    "status": "recommended",
                    "created_at": "2026-03-01T10:00:00Z",
                },
                {
                    "match_id": 2,
                    "challenge_id": "CH-IND-001",
                    "industry_id": "IND002",
                    "rank": 2,
                    "match_score": 62.0,
                    "match_reason": "Moderate AI capabilities",
                    "status": "recommended",
                    "created_at": "2026-03-01T10:00:00Z",
                },
            ],
            "projects": [
                {
                    "project_id": "PRJ-IND-TEST-001",
                    "challenge_id": "CH-IND-001",
                    "university_id": "U001",
                    "faculty_id": "FAC-001",
                    "industry_id": "IND001",  # Partnered with IND001
                    "project_title": "Industrial Effluent Sensing Initiative",
                    "status": "active",
                    "created_at": "2026-03-02T10:00:00Z",
                },
                {
                    "project_id": "PRJ-NO-IND",
                    "challenge_id": "CH-NO-IND",
                    "university_id": "U001",
                    "faculty_id": "FAC-001",
                    "industry_id": None,  # No industry partner yet
                    "project_title": "Standalone Academic Research",
                    "status": "active",
                    "created_at": "2026-03-02T10:00:00Z",
                },
            ],
            "industry_employees": [
                {
                    "employee_id": "EMP-SPOC-01",
                    "user_id": "usr-spoc-ind001",
                    "industry_id": "IND001",
                    "employee_name": "Vikram Malhotra",
                    "designation": "Head of Corporate Relations & CSR",
                    "department": "CSR & Public Tech",
                    "email": "vikram.malhotra@tatacsr.com",
                    "verification_status": "verified",
                    "approval_authority": True,  # Authorized SPOC!
                },
                {
                    "employee_id": "EMP-STAFF-01",
                    "user_id": "usr-staff-ind001",
                    "industry_id": "IND001",
                    "employee_name": "Neha Gupta",
                    "designation": "Senior Embedded Firmware Engineer",
                    "department": "Hardware Engineering",
                    "email": "neha.gupta@tatacsr.com",
                    "verification_status": "verified",
                    "approval_authority": False,  # Regular employee, NOT SPOC
                },
                {
                    "employee_id": "EMP-STAFF-02",
                    "user_id": "usr-staff-ind001-two",
                    "industry_id": "IND001",
                    "employee_name": "Sameer Joshi",
                    "designation": "IoT Systems Specialist",
                    "department": "Hardware Engineering",
                    "email": "sameer.joshi@tatacsr.com",
                    "verification_status": "verified",
                    "approval_authority": False,
                },
                {
                    "employee_id": "EMP-FOREIGN-01",
                    "user_id": "usr-foreign-ind002",
                    "industry_id": "IND002",  # Belongs to IND002!
                    "employee_name": "Amit Trivedi",
                    "designation": "AI Research Scientist",
                    "department": "Innovation Cell",
                    "email": "amit.trivedi@tatasteel.com",
                    "verification_status": "verified",
                    "approval_authority": False,
                },
                {
                    "employee_id": "EMP-SPOC-IND002",
                    "user_id": "usr-spoc-ind002",
                    "industry_id": "IND002",
                    "employee_name": "Kavita Rao",
                    "designation": "Director of Technology",
                    "department": "Management",
                    "email": "kavita.rao@tatasteel.com",
                    "verification_status": "verified",
                    "approval_authority": True,
                },
            ],
            "project_employee_interests": [],
        }


class MockQueryBuilder:
    def __init__(self, db: MockSupabaseDB, table_name: str):
        self.db = db
        self.table_name = table_name
        self.filters = []
        self._order_col = None
        self._desc = False
        self._limit_val = None
        self._pending_result = None

    def select(self, *args, **kwargs):
        return self

    def eq(self, field: str, value: Any):
        self.filters.append(("eq", field, value))
        return self

    def order(self, field: str, desc: bool = False):
        self._order_col = field
        self._desc = desc
        return self

    def limit(self, count: int):
        self._limit_val = count
        return self

    def insert(self, record: Dict[str, Any]):
        new_row = dict(record)
        table = self.db.tables[self.table_name]
        if self.table_name == "project_employee_interests" and "interest_id" not in new_row:
            new_row["interest_id"] = len(table) + 1
        table.append(new_row)
        self._pending_result = [new_row]
        return self

    def update(self, patch: Dict[str, Any]):
        table = self.db.tables[self.table_name]
        updated_rows = []
        for row in table:
            if self._matches(row):
                row.update(patch)
                updated_rows.append(dict(row))
        self._pending_result = updated_rows
        return self

    def _matches(self, row: Dict[str, Any]) -> bool:
        for f_type, field, val in self.filters:
            if f_type == "eq":
                if str(row.get(field)) != str(val):
                    return False
        return True

    def execute(self):
        if self._pending_result is not None:
            res = self._pending_result
            self._pending_result = None
            return MockExecResult(res)

        table = self.db.tables[self.table_name]
        matched = [dict(row) for row in table if self._matches(row)]

        if self._order_col:
            matched.sort(key=lambda x: str(x.get(self._order_col, "")), reverse=self._desc)
        if self._limit_val:
            matched = matched[: self._limit_val]

        return MockExecResult(matched)


class MockExecResult:
    def __init__(self, data: List[Dict[str, Any]]):
        self.data = data


class MockClient:
    def __init__(self, db: MockSupabaseDB):
        self.db = db

    def table(self, table_name: str):
        return MockQueryBuilder(self.db, table_name)


# =============================================================================
# Test Setup & Fixtures
# =============================================================================
mock_db = MockSupabaseDB()
mock_client = MockClient(mock_db)
industry_service = IndustryWorkflowService(client=mock_client)

app.dependency_overrides[get_ind_svc_challenges] = lambda: industry_service
app.dependency_overrides[get_ind_svc_projects] = lambda: industry_service

# Users
SPOC_IND001 = AuthenticatedUser(
    user_id="usr-spoc-ind001",
    email="vikram.malhotra@tatacsr.com",
    role="industry_employee",
    is_verified=True,
    verification_status="verified",
    approval_authority=True,
    stakeholder={
        "employee_id": "EMP-SPOC-01",
        "industry_id": "IND001",
        "employee_name": "Vikram Malhotra",
        "approval_authority": True,
    },
)

STAFF_IND001_A = AuthenticatedUser(
    user_id="usr-staff-ind001",
    email="neha.gupta@tatacsr.com",
    role="industry_employee",
    is_verified=True,
    verification_status="verified",
    approval_authority=False,  # NOT SPOC
    stakeholder={
        "employee_id": "EMP-STAFF-01",
        "industry_id": "IND001",
        "employee_name": "Neha Gupta",
        "approval_authority": False,
    },
)

STAFF_IND001_B = AuthenticatedUser(
    user_id="usr-staff-ind001-two",
    email="sameer.joshi@tatacsr.com",
    role="industry_employee",
    is_verified=True,
    verification_status="verified",
    approval_authority=False,
    stakeholder={
        "employee_id": "EMP-STAFF-02",
        "industry_id": "IND001",
        "employee_name": "Sameer Joshi",
        "approval_authority": False,
    },
)

STAFF_FOREIGN_IND002 = AuthenticatedUser(
    user_id="usr-foreign-ind002",
    email="amit.trivedi@tatasteel.com",
    role="industry_employee",
    is_verified=True,
    verification_status="verified",
    approval_authority=False,
    stakeholder={
        "employee_id": "EMP-FOREIGN-01",
        "industry_id": "IND002",  # From IND002!
        "employee_name": "Amit Trivedi",
        "approval_authority": False,
    },
)

SPOC_FOREIGN_IND002 = AuthenticatedUser(
    user_id="usr-spoc-ind002",
    email="kavita.rao@tatasteel.com",
    role="industry_employee",
    is_verified=True,
    verification_status="verified",
    approval_authority=True,
    stakeholder={
        "employee_id": "EMP-SPOC-IND002",
        "industry_id": "IND002",
        "employee_name": "Kavita Rao",
        "approval_authority": True,
    },
)

CITIZEN_USER = AuthenticatedUser(
    user_id="usr-citizen-001",
    email="citizen@test.in",
    role="citizen",
    is_verified=True,
    verification_status="verified",
)

client = TestClient(app)


def test_suite():
    print("\n" + "=" * 75)
    print("RUNNING PHASE 7 VERIFICATION TEST SUITE: INDUSTRY COLLABORATION WORKFLOW")
    print("=" * 75)

    # -------------------------------------------------------------------------
    # Test 1: Industry SPOC Access Control & Collaboration Response
    # -------------------------------------------------------------------------
    print("\n[TEST 1] Industry SPOC Access Control & Collaboration Response...")

    # 1A. Ordinary employee without approval_authority cannot respond to match
    app.dependency_overrides[get_current_user] = lambda: STAFF_IND001_A
    resp = client.post(
        "/api/challenges/CH-IND-001/industries/IND001/respond",
        json={"action": "accept", "response_note": "I would love to work on this"},
    )
    assert resp.status_code == 403, f"Expected 403 for ordinary employee, got {resp.status_code}: {resp.text}"
    assert "SPOC approval authority is required" in resp.json()["error"]["message"]
    print(f"  -> PASSED: Ordinary employee blocked with 403: '{resp.json()['error']['message']}'.")

    # 1B. Foreign SPOC cannot respond for another industry
    app.dependency_overrides[get_current_user] = lambda: SPOC_FOREIGN_IND002
    resp = client.post(
        "/api/challenges/CH-IND-001/industries/IND001/respond",
        json={"action": "accept", "response_note": "Tata Steel accepting on behalf of Tata CSR"},
    )
    assert resp.status_code == 403, f"Expected 403 for foreign SPOC, got {resp.status_code}: {resp.text}"
    print("  -> PASSED: Foreign SPOC blocked with 403 Forbidden.")

    # 1C. Non-industry citizen cannot respond
    app.dependency_overrides[get_current_user] = lambda: CITIZEN_USER
    resp = client.post(
        "/api/challenges/CH-IND-001/industries/IND001/respond",
        json={"action": "accept"},
    )
    assert resp.status_code == 403, f"Expected 403 for citizen, got {resp.status_code}: {resp.text}"
    print("  -> PASSED: Non-industry user blocked with 403 Forbidden.")

    # 1D. Authorized Industry SPOC accepts collaboration proposal
    app.dependency_overrides[get_current_user] = lambda: SPOC_IND001
    resp = client.post(
        "/api/challenges/CH-IND-001/industries/IND001/respond",
        json={
            "action": "accept",
            "response_note": "Tata CSR pledges Rs 5L hardware seed grant and 2 technical mentors.",
        },
    )
    assert resp.status_code == 200, f"Expected 200 OK, got {resp.status_code}: {resp.text}"
    match_data = resp.json()["data"]
    assert match_data["status"] == "accepted"
    assert match_data["responded_by"] == SPOC_IND001.user_id
    print(f"  -> PASSED: Industry SPOC accepted collaboration proposal; status='accepted'.")

    # -------------------------------------------------------------------------
    # Test 2: Employee Interest Expression & Institutional Boundaries
    # -------------------------------------------------------------------------
    print("\n[TEST 2] Employee Interest Expression & Institutional Boundaries...")

    # 2A. Citizen or student cannot express employee interest
    app.dependency_overrides[get_current_user] = lambda: CITIZEN_USER
    resp = client.post(
        "/api/projects/PRJ-IND-TEST-001/employee-interest",
        json={"message": "I am interested"},
    )
    assert resp.status_code == 403, f"Expected 403 for citizen, got {resp.status_code}: {resp.text}"
    print("  -> PASSED: Non-industry citizen blocked with 403 Forbidden.")

    # 2B. Cross-industry employee (IND002) attempting interest in IND001 project
    app.dependency_overrides[get_current_user] = lambda: STAFF_FOREIGN_IND002
    resp = client.post(
        "/api/projects/PRJ-IND-TEST-001/employee-interest",
        json={"message": "I want to join this project"},
    )
    assert resp.status_code == 400, f"Expected 400 for cross-industry interest, got {resp.status_code}: {resp.text}"
    assert "Cross-industry participation is not permitted" in resp.json()["error"]["message"]
    print(f"  -> PASSED: Cross-industry employee blocked with 400: '{resp.json()['error']['message']}'.")

    # 2C. Express interest in project with no industry partner
    app.dependency_overrides[get_current_user] = lambda: STAFF_IND001_A
    resp = client.post(
        "/api/projects/PRJ-NO-IND/employee-interest",
        json={"message": "Interest in academic project"},
    )
    assert resp.status_code == 400, f"Expected 400 for unpartnered project, got {resp.status_code}: {resp.text}"
    print("  -> PASSED: Unpartnered project interest rejected with 400 Bad Request.")

    # 2D. Legitimate verified employee from IND001 expresses interest
    resp = client.post(
        "/api/projects/PRJ-IND-TEST-001/employee-interest",
        json={"message": "5 years experience in ESP32 firmware and water sensor telemetry."},
    )
    assert resp.status_code == 201, f"Expected 201 Created, got {resp.status_code}: {resp.text}"
    int_data = resp.json()["data"]
    assert int_data["employee_id"] == "EMP-STAFF-01"
    assert int_data["status"] == "interested"
    assert int_data["employee_name"] == "Neha Gupta"
    interest_id_1 = int_data["interest_id"]
    print(f"  -> PASSED: Employee '{int_data['employee_name']}' expressed interest (ID: {interest_id_1}).")

    # 2E. Second employee expresses interest
    app.dependency_overrides[get_current_user] = lambda: STAFF_IND001_B
    resp = client.post(
        "/api/projects/PRJ-IND-TEST-001/employee-interest",
        json={"message": "Expert in sensor hardware calibration and LoRa protocol."},
    )
    assert resp.status_code == 201
    interest_id_2 = resp.json()["data"]["interest_id"]
    print(f"  -> PASSED: Second employee '{resp.json()['data']['employee_name']}' expressed interest (ID: {interest_id_2}).")

    # 2F. Duplicate active interest expression
    resp = client.post(
        "/api/projects/PRJ-IND-TEST-001/employee-interest",
        json={"message": "Submitting again"},
    )
    assert resp.status_code == 400, f"Expected 400 for duplicate, got {resp.status_code}: {resp.text}"
    assert "already expressed active interest" in resp.json()["error"]["message"]
    print(f"  -> PASSED: Duplicate active interest rejected with 400: '{resp.json()['error']['message']}'.")

    # -------------------------------------------------------------------------
    # Test 3: List Employee Interests & Profile Hydration
    # -------------------------------------------------------------------------
    print("\n[TEST 3] Listing Employee Interests & Profile Hydration...")

    app.dependency_overrides[get_current_user] = lambda: SPOC_IND001
    resp = client.get("/api/projects/PRJ-IND-TEST-001/employee-interests")
    assert resp.status_code == 200
    interests_list = resp.json()["data"]
    assert len(interests_list) == 2
    emp_names = [i.get("employee_name") for i in interests_list]
    assert "Neha Gupta" in emp_names
    assert "Sameer Joshi" in emp_names
    print(f"  -> PASSED: SPOC retrieved {len(interests_list)} interests with hydrated names: {emp_names}.")

    # -------------------------------------------------------------------------
    # Test 4: SPOC Selection & Anti-Self-Selection Enforcement
    # -------------------------------------------------------------------------
    print("\n[TEST 4] SPOC Selection & Anti-Self-Selection Rules...")

    # 4A. Ordinary employee attempting to select themselves or others
    app.dependency_overrides[get_current_user] = lambda: STAFF_IND001_A
    resp = client.patch(
        f"/api/projects/PRJ-IND-TEST-001/employee-interests/{interest_id_1}",
        json={"status": "selected"},
    )
    assert resp.status_code == 403, f"Expected 403 for employee selecting self, got {resp.status_code}: {resp.text}"
    assert "SPOC approval authority is required" in resp.json()["error"]["message"]
    print(f"  -> PASSED: Ordinary employee blocked from self-selection with 403: '{resp.json()['error']['message']}'.")

    # 4B. SPOC selects employee Neha Gupta (EMP-STAFF-01)
    app.dependency_overrides[get_current_user] = lambda: SPOC_IND001
    resp = client.patch(
        f"/api/projects/PRJ-IND-TEST-001/employee-interests/{interest_id_1}",
        json={"status": "selected", "note": "Selected as Industry Lead Mentor"},
    )
    assert resp.status_code == 200, f"Expected 200 OK, got {resp.status_code}: {resp.text}"
    sel_data = resp.json()["data"]
    assert sel_data["status"] == "selected"
    assert sel_data["employee_name"] == "Neha Gupta"
    print(f"  -> PASSED: SPOC selected '{sel_data['employee_name']}' as official project participant.")

    # 4C. Employee Sameer Joshi withdraws their interest
    app.dependency_overrides[get_current_user] = lambda: STAFF_IND001_B
    resp = client.patch(
        f"/api/projects/PRJ-IND-TEST-001/employee-interests/{interest_id_2}",
        json={"status": "withdrawn", "note": "Assigned to another corporate project"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "withdrawn"
    print("  -> PASSED: Employee successfully withdrew their own interest.")

    # 4D. Sameer Joshi reactivates withdrawn interest
    resp = client.post(
        "/api/projects/PRJ-IND-TEST-001/employee-interest",
        json={"message": "Availability reopened, re-expressing interest."},
    )
    assert resp.status_code == 201
    assert resp.json()["data"]["status"] == "interested"
    print("  -> PASSED: Reactivated withdrawn interest back to 'interested'.")

    print("\n" + "=" * 75)
    print("ALL PHASE 7 VERIFICATION TESTS PASSED SUCCESSFULLY! (100% SUCCESS)")
    print("=" * 75)


if __name__ == "__main__":
    test_suite()
