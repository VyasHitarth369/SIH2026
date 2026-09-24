"""test_phase6_faculty_student.py

Comprehensive test suite for Phase 6: Faculty + Student Project Workflow:
1. Faculty Authorization & Access Control (assigned faculty vs unrelated faculty vs university admin)
2. Strict Institutional Student Boundaries (cross-university student assignment rejection)
3. Duplicate Membership Prevention & Member Lifecycle (adding, removing, reactivating)
4. Milestone Creation & Completion Percentage Validation (0-100 constraint, invalid range rejection)
5. Milestone Update, Status Auto-Progression & Evidence Submission (evidence URL, completion = 100 auto-completes)
6. Role-Based Project Visibility (student, faculty, admin, and public scoping)
"""

import copy
from typing import Any, Dict, List, Optional
from starlette.testclient import TestClient

from app.main import app
from app.dependencies.auth import get_current_user, get_current_user_optional
from app.routes.projects import get_project_workflow_service, get_workflow_service
from app.services.auth_service import AuthenticatedUser
from app.services.project_workflow_service import ProjectWorkflowService



# =============================================================================
# In-Memory Mock Database for Hermetic Testing
# =============================================================================
class MockSupabaseDB:
    def __init__(self):
        self.tables = {
            "projects": [
                {
                    "project_id": "PRJ-TEST-001",
                    "challenge_id": "CH-001",
                    "university_id": "U001",
                    "faculty_id": "FAC-001",
                    "industry_id": "IND001",
                    "project_title": "Smart Civic Water Quality Monitor",
                    "description": "IoT water quality sensor mesh network",
                    "status": "proposed",
                    "created_at": "2026-03-01T10:00:00Z",
                },
                {
                    "project_id": "PRJ-TEST-002",
                    "challenge_id": "CH-002",
                    "university_id": "U002",
                    "faculty_id": "FAC-002",
                    "industry_id": None,
                    "project_title": "Mining Water Reclamation Platform",
                    "description": "Bioremediation and GIS mapping",
                    "status": "active",
                    "created_at": "2026-03-02T10:00:00Z",
                },
            ],
            "students": [
                {
                    "student_id": "STU-001",
                    "user_id": "usr-student-001",
                    "university_id": "U001",
                    "student_name": "Aarav Sharma",
                    "department": "Computer Science & Engg",
                    "course": "B.Tech",
                    "email": "aarav.sharma@bitmesra.ac.in",
                    "skills": "Python, IoT Sensors, FastAPI",
                },
                {
                    "student_id": "STU-002",
                    "user_id": "usr-student-002",
                    "university_id": "U001",
                    "student_name": "Priya Singh",
                    "department": "Civil Engineering",
                    "course": "B.Tech",
                    "email": "priya.singh@bitmesra.ac.in",
                    "skills": "CAD, Structural Analysis, Field Testing",
                },
                {
                    "student_id": "STU-FOREIGN",
                    "user_id": "usr-student-foreign",
                    "university_id": "U002",  # Belongs to U002, foreign to U001 project!
                    "student_name": "Rohan Verma",
                    "department": "Mining Engineering",
                    "course": "M.Tech",
                    "email": "rohan.verma@iitdhanbad.ac.in",
                    "skills": "Water Chemistry, Remote Sensing",
                },
            ],
            "faculty": [
                {
                    "faculty_id": "FAC-001",
                    "user_id": "usr-fac-001",
                    "university_id": "U001",
                    "faculty_name": "Dr. Ramesh Kumar",
                    "department": "Computer Science & Engg",
                },
                {
                    "faculty_id": "FAC-OTHER",
                    "user_id": "usr-fac-other",
                    "university_id": "U001",
                    "faculty_name": "Dr. Sunita Sen",
                    "department": "Civil Engineering",
                },
                {
                    "faculty_id": "FAC-002",
                    "user_id": "usr-fac-002",
                    "university_id": "U002",
                    "faculty_name": "Dr. Ananya Roy",
                    "department": "Mining Engineering",
                },
            ],
            "project_members": [],
            "project_milestones": [],
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

    def in_(self, field: str, values: List[Any]):
        self.filters.append(("in", field, values))
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
        if self.table_name == "project_members" and "project_member_id" not in new_row:
            new_row["project_member_id"] = len(table) + 1
        if self.table_name == "project_milestones" and "milestone_id" not in new_row:
            new_row["milestone_id"] = len(table) + 1
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
            elif f_type == "in":
                if row.get(field) not in val:
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
workflow_service = ProjectWorkflowService(client=mock_client)


class MockUniService:
    def __init__(self):
        self.client = mock_client

    def list_projects(self, **kwargs):
        return workflow_service.list_projects_for_user(None, **kwargs)

    def _get_project_or_404(self, project_id: str):
        return workflow_service._get_project_or_404(project_id)

    def _resolve_university_admin_record(self, user):
        return workflow_service._resolve_university_admin_record(user)

    def _resolve_faculty_record(self, user):
        return workflow_service._resolve_faculty_record(user)


app.dependency_overrides[get_project_workflow_service] = lambda: workflow_service
app.dependency_overrides[get_workflow_service] = lambda: MockUniService()

# Users
FACULTY_USER = AuthenticatedUser(
    user_id="usr-fac-001",
    email="ramesh.kumar@bitmesra.ac.in",
    role="faculty",
    is_verified=True,
    verification_status="verified",
    stakeholder={"faculty_id": "FAC-001", "university_id": "U001"},
)

UNRELATED_FACULTY_USER = AuthenticatedUser(
    user_id="usr-fac-other",
    email="sunita.sen@bitmesra.ac.in",
    role="faculty",
    is_verified=True,
    verification_status="verified",
    stakeholder={"faculty_id": "FAC-OTHER", "university_id": "U001"},
)

UNI_ADMIN_USER = AuthenticatedUser(
    user_id="usr-admin-u001",
    email="dean.research@bitmesra.ac.in",
    role="university_admin",
    is_verified=True,
    verification_status="verified",
    stakeholder={"university_id": "U001"},
)

FOREIGN_UNI_ADMIN = AuthenticatedUser(
    user_id="usr-admin-u002",
    email="admin@iitdhanbad.ac.in",
    role="university_admin",
    is_verified=True,
    verification_status="verified",
    stakeholder={"university_id": "U002"},
)

STUDENT_USER_1 = AuthenticatedUser(
    user_id="usr-student-001",
    email="aarav.sharma@bitmesra.ac.in",
    role="student",
    is_verified=True,
    verification_status="verified",
    stakeholder={"student_id": "STU-001", "university_id": "U001"},
)

STUDENT_USER_UNASSIGNED = AuthenticatedUser(
    user_id="usr-student-unassigned",
    email="unknown.student@test.edu",
    role="student",
    is_verified=True,
    verification_status="verified",
    stakeholder={"student_id": "STU-UNASSIGNED", "university_id": "U001"},
)

client = TestClient(app)


def test_suite():
    print("\n" + "=" * 75)
    print("RUNNING PHASE 6 VERIFICATION TEST SUITE: FACULTY + STUDENT WORKFLOW")
    print("=" * 75)

    # -------------------------------------------------------------------------
    # Test 1: Faculty Authorization for Project Member Management
    # -------------------------------------------------------------------------
    print("\n[TEST 1] Faculty & Admin Authorization for Member Management...")
    
    # 1A. Unrelated faculty cannot add student to PRJ-TEST-001
    app.dependency_overrides[get_current_user] = lambda: UNRELATED_FACULTY_USER
    resp = client.post(
        "/api/projects/PRJ-TEST-001/members",
        json={"student_id": "STU-001", "role": "lead"},
    )
    assert resp.status_code == 403, f"Expected 403 for unrelated faculty, got {resp.status_code}: {resp.text}"
    print("  -> PASSED: Unrelated faculty blocked with 403 Forbidden.")

    # 1B. Foreign university admin cannot manage PRJ-TEST-001
    app.dependency_overrides[get_current_user] = lambda: FOREIGN_UNI_ADMIN
    resp = client.post(
        "/api/projects/PRJ-TEST-001/members",
        json={"student_id": "STU-001", "role": "lead"},
    )
    assert resp.status_code == 403, f"Expected 403 for foreign admin, got {resp.status_code}: {resp.text}"
    print("  -> PASSED: Foreign university admin blocked with 403 Forbidden.")

    # -------------------------------------------------------------------------
    # Test 2: Institutional Student Boundaries (Cross-University Assignment)
    # -------------------------------------------------------------------------
    print("\n[TEST 2] Institutional Student Boundaries (Cross-University Prevention)...")

    # 2A. Attempting to add foreign university student STU-FOREIGN (from U002) to U001 project
    app.dependency_overrides[get_current_user] = lambda: FACULTY_USER
    resp = client.post(
        "/api/projects/PRJ-TEST-001/members",
        json={"student_id": "STU-FOREIGN", "role": "developer"},
    )
    assert resp.status_code == 400, f"Expected 400 for cross-university student, got {resp.status_code}: {resp.text}"
    assert "Cross-university student assignment is not permitted" in resp.json()["error"]["message"]
    print(f"  -> PASSED: Cross-university student blocked with 400: '{resp.json()['error']['message']}'.")

    # 2B. Attempting to add nonexistent student
    resp = client.post(
        "/api/projects/PRJ-TEST-001/members",
        json={"student_id": "STU-NONEXISTENT", "role": "developer"},
    )
    assert resp.status_code == 404, f"Expected 404 for nonexistent student, got {resp.status_code}: {resp.text}"
    print("  -> PASSED: Nonexistent student rejected with 404 Not Found.")

    # 2C. Valid addition: Enrolled student from U001 added to U001 project by assigned faculty
    resp = client.post(
        "/api/projects/PRJ-TEST-001/members",
        json={"student_id": "STU-001", "role": "lead"},
    )
    assert resp.status_code == 201, f"Expected 201 Created, got {resp.status_code}: {resp.text}"
    data = resp.json()["data"]
    assert data["student_id"] == "STU-001"
    assert data["role"] == "lead"
    assert data["status"] == "active"
    print("  -> PASSED: Enrolled student added successfully to project.")

    # 2D. Add second student Priya Singh via University Admin
    app.dependency_overrides[get_current_user] = lambda: UNI_ADMIN_USER
    resp = client.post(
        "/api/projects/PRJ-TEST-001/members",
        json={"student_id": "STU-002", "role": "researcher"},
    )
    assert resp.status_code == 201
    print("  -> PASSED: University Admin successfully added student to university project.")

    # -------------------------------------------------------------------------
    # Test 3: Duplicate Membership Prevention & Member Removal
    # -------------------------------------------------------------------------
    print("\n[TEST 3] Duplicate Membership Prevention & Removal Lifecycle...")

    # 3A. Adding STU-001 again must be rejected
    app.dependency_overrides[get_current_user] = lambda: FACULTY_USER
    resp = client.post(
        "/api/projects/PRJ-TEST-001/members",
        json={"student_id": "STU-001", "role": "member"},
    )
    assert resp.status_code == 400, f"Expected 400 duplicate membership, got {resp.status_code}: {resp.text}"
    assert "already an active member" in resp.json()["error"]["message"]
    print(f"  -> PASSED: Duplicate active membership rejected with 400: '{resp.json()['error']['message']}'.")

    # 3B. List members on project
    resp = client.get("/api/projects/PRJ-TEST-001/members")
    assert resp.status_code == 200
    members = resp.json()["data"]
    assert len(members) == 2
    student_names = [m.get("student_name") for m in members]
    assert "Aarav Sharma" in student_names
    assert "Priya Singh" in student_names
    print(f"  -> PASSED: Listed {len(members)} project members with hydrated student names: {student_names}.")

    # 3C. Remove student STU-002
    resp = client.delete("/api/projects/PRJ-TEST-001/members/STU-002")
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "removed"
    print("  -> PASSED: Removed student member marked with status 'removed'.")

    # 3D. Reactivate STU-002
    resp = client.post(
        "/api/projects/PRJ-TEST-001/members",
        json={"student_id": "STU-002", "role": "specialist"},
    )
    assert resp.status_code == 201
    assert resp.json()["data"]["status"] == "active"
    print("  -> PASSED: Reactivated previously removed member successfully.")

    # -------------------------------------------------------------------------
    # Test 4: Milestone Creation & Completion Percentage Validation (0-100)
    # -------------------------------------------------------------------------
    print("\n[TEST 4] Milestone Creation & Completion Percentage Validation...")

    # 4A. Negative completion percentage rejected
    resp = client.post(
        "/api/projects/PRJ-TEST-001/milestones",
        json={
            "milestone_name": "Invalid Negative Milestone",
            "completion_percentage": -15,
        },
    )
    assert resp.status_code == 422, f"Expected 422 for completion_percentage < 0, got {resp.status_code}"
    print("  -> PASSED: Negative completion_percentage rejected with HTTP 422.")

    # 4B. Completion percentage > 100 rejected
    resp = client.post(
        "/api/projects/PRJ-TEST-001/milestones",
        json={
            "milestone_name": "Invalid >100 Milestone",
            "completion_percentage": 105,
        },
    )
    assert resp.status_code == 422, f"Expected 422 for completion_percentage > 100, got {resp.status_code}"
    print("  -> PASSED: completion_percentage > 100 rejected with HTTP 422.")

    # 4C. Assignee validation: assignee must be member or faculty
    resp = client.post(
        "/api/projects/PRJ-TEST-001/milestones",
        json={
            "milestone_name": "Sensor Hardware Specification",
            "assigned_to": "UNKNOWN-PERSON",
            "completion_percentage": 0,
        },
    )
    assert resp.status_code == 400, f"Expected 400 for unassigned person, got {resp.status_code}"
    print(f"  -> PASSED: Non-member assignee rejected with 400: '{resp.json()['error']['message']}'.")

    # 4D. Valid milestone creation
    resp = client.post(
        "/api/projects/PRJ-TEST-001/milestones",
        json={
            "milestone_name": "Sensor Hardware Prototyping",
            "description": "Construct ESP32 turbidity and pH test bench",
            "assigned_to": "STU-001",
            "deadline": "2026-04-15",
            "completion_percentage": 0,
        },
    )
    assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
    milestone_1 = resp.json()["data"]
    m1_id = milestone_1["milestone_id"]
    assert milestone_1["status"] == "pending"
    assert milestone_1["completion_percentage"] == 0
    print(f"  -> PASSED: Milestone '{milestone_1['milestone_name']}' created (ID: {m1_id}).")

    # 4E. Verify that project PRJ-TEST-001 was progressed from 'proposed' to 'active'
    proj = [p for p in mock_db.tables["projects"] if p["project_id"] == "PRJ-TEST-001"][0]
    assert proj["status"] == "active", f"Expected project status 'active', got '{proj['status']}'"
    print("  -> PASSED: Project lifecycle state automatically advanced from 'proposed' to 'active'.")

    # -------------------------------------------------------------------------
    # Test 5: Milestone Progress Update & Evidence Submission
    # -------------------------------------------------------------------------
    print("\n[TEST 5] Milestone Progress Update, Auto-Transitions & Evidence...")

    # 5A. Unauthorized student cannot update milestone
    app.dependency_overrides[get_current_user] = lambda: STUDENT_USER_UNASSIGNED
    resp = client.patch(
        f"/api/milestones/{m1_id}",
        json={"completion_percentage": 50},
    )
    assert resp.status_code == 403, f"Expected 403 for unassigned student, got {resp.status_code}"
    print("  -> PASSED: Unassigned student blocked from milestone update with 403 Forbidden.")

    # 5B. Assigned student STU-001 updates milestone progress to 50% and provides evidence URL
    app.dependency_overrides[get_current_user] = lambda: STUDENT_USER_1
    resp = client.patch(
        f"/api/milestones/{m1_id}",
        json={
            "completion_percentage": 50,
            "evidence_url": "https://concordia.storage/evidence/sensor_schematic_v1.pdf",
        },
    )
    assert resp.status_code == 200, f"Expected 200 OK, got {resp.status_code}: {resp.text}"
    m_updated = resp.json()["data"]
    assert m_updated["completion_percentage"] == 50
    assert m_updated["status"] == "in_progress"
    assert m_updated["evidence_url"] == "https://concordia.storage/evidence/sensor_schematic_v1.pdf"
    print("  -> PASSED: Assigned student updated milestone to 50%; status auto-advanced to 'in_progress'.")

    # 5C. Milestone reaches 100% completion -> automatically marked as 'completed'
    resp = client.patch(
        f"/api/milestones/{m1_id}",
        json={
            "completion_percentage": 100,
            "evidence_url": "https://concordia.storage/evidence/sensor_prototype_tested.mp4",
        },
    )
    assert resp.status_code == 200
    m_completed = resp.json()["data"]
    assert m_completed["completion_percentage"] == 100
    assert m_completed["status"] == "completed"
    print("  -> PASSED: Milestone reached 100%; status auto-transitioned to 'completed'.")

    # 5D. List milestones for project
    resp = client.get("/api/projects/PRJ-TEST-001/milestones")
    assert resp.status_code == 200
    milestones = resp.json()["data"]
    assert len(milestones) == 1
    assert milestones[0]["status"] == "completed"
    print(f"  -> PASSED: Successfully retrieved {len(milestones)} project milestone(s).")

    # -------------------------------------------------------------------------
    # Test 6: Role-Based Project Visibility
    # -------------------------------------------------------------------------
    print("\n[TEST 6] Role-Based Project Visibility Scoping...")

    # 6A. Faculty sees only their assigned projects
    app.dependency_overrides[get_current_user_optional] = lambda: FACULTY_USER
    resp = client.get("/api/projects")
    assert resp.status_code == 200
    fac_projects = resp.json()["data"]
    assert len(fac_projects) == 1
    assert fac_projects[0]["project_id"] == "PRJ-TEST-001"
    print(f"  -> PASSED: Faculty saw exactly 1 project assigned to them (PRJ-TEST-001).")

    # 6B. University Admin sees all projects under their university (U001)
    app.dependency_overrides[get_current_user_optional] = lambda: UNI_ADMIN_USER
    resp = client.get("/api/projects")
    assert resp.status_code == 200
    admin_projects = resp.json()["data"]
    assert all(p["university_id"] == "U001" for p in admin_projects)
    print(f"  -> PASSED: University Admin saw only projects belonging to U001.")

    # 6C. Student sees their member project
    app.dependency_overrides[get_current_user_optional] = lambda: STUDENT_USER_1
    resp = client.get("/api/projects")
    assert resp.status_code == 200
    stu_projects = resp.json()["data"]
    assert any(p["project_id"] == "PRJ-TEST-001" for p in stu_projects)
    print(f"  -> PASSED: Student saw their assigned project (PRJ-TEST-001).")

    # 6D. Unauthenticated / Public sees all projects
    app.dependency_overrides[get_current_user_optional] = lambda: None
    resp = client.get("/api/projects")
    assert resp.status_code == 200
    all_projects = resp.json()["data"]
    assert len(all_projects) == 2
    print(f"  -> PASSED: Public/Unauthenticated sees all {len(all_projects)} projects.")

    print("\n" + "=" * 75)
    print("ALL PHASE 6 VERIFICATION TESTS PASSED SUCCESSFULLY! (100% SUCCESS)")
    print("=" * 75)


if __name__ == "__main__":
    test_suite()
