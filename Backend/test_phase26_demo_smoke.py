"""test_phase26_demo_smoke.py

Focused Smoke Test Suite for Phase 26 Demo Readiness.
Verifies the complete demo story:
Citizen -> AI -> University -> Faculty -> Student -> Project -> Industry -> Employee -> Milestones -> Government Monitoring -> Citizen Visibility.
"""

import sys
import os
import unittest
from starlette.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.main import app
from app.services.auth_service import AuthenticatedUser
from app.dependencies.auth import get_current_user, get_current_user_optional, require_government_officer


class MockSupabaseTable:
    def __init__(self, data=None):
        self.data = data or []
        self._filtered = list(self.data)

    def select(self, *args, **kwargs):
        return self

    def eq(self, field, value):
        self._filtered = [r for r in self._filtered if r.get(field) == value]
        return self

    def in_(self, field, values):
        self._filtered = [r for r in self._filtered if r.get(field) in values]
        return self

    def order(self, *args, **kwargs):
        return self

    def limit(self, count):
        self._filtered = self._filtered[:count]
        return self

    def insert(self, record):
        if isinstance(record, dict):
            if "milestone_id" not in record:
                record["milestone_id"] = len(self.data) + 1
            if "project_member_id" not in record:
                record["project_member_id"] = len(self.data) + 1
            if "feedback_id" not in record:
                record["feedback_id"] = len(self.data) + 1
            self.data.append(record)
            self._filtered = [record]
        return self

    def update(self, patch):
        for r in self._filtered:
            r.update(patch)
        return self

    def execute(self):
        class Res:
            def __init__(self, data):
                self.data = data
        res_data = list(self._filtered)
        self._filtered = list(self.data)  # reset
        return Res(res_data)


class MockSupabaseClient:
    def __init__(self, tables=None):
        self.tables = tables or {}

    def table(self, name):
        if name not in self.tables:
            self.tables[name] = MockSupabaseTable()
        return self.tables[name]


def make_smoke_client():
    client = TestClient(app)

    db = MockSupabaseClient({
        "challenges": MockSupabaseTable([
            {
                "challenge_id": "CHL-SMOKE-001",
                "title": "Smart Solar Water Purifier for Villages",
                "description": "Lack of potable water in rural areas",
                "status": "university_selected",
                "submitted_by": "Citizen Ramesh",
                "user_id": "usr-cit-01",
            }
        ]),
        "universities": MockSupabaseTable([
            {"university_id": "U001", "university_name": "BIT Mesra"},
            {"university_id": "U002", "university_name": "IIT Dhanbad"},
        ]),
        "faculty": MockSupabaseTable([
            {
                "faculty_id": "FAC-001",
                "university_id": "U001",
                "faculty_name": "Dr. Verma",
                "department": "Environmental Engineering",
                "email": "verma@bitmesra.ac.in",
            },
            {
                "faculty_id": "FAC-002",
                "university_id": "U002",
                "faculty_name": "Dr. Sen",
                "department": "Chemical Engineering",
                "email": "sen@iitdhanbad.ac.in",
            }
        ]),
        "students": MockSupabaseTable([
            {
                "student_id": "STU-001",
                "university_id": "U001",
                "student_name": "Amit Kumar",
                "department": "Civil & Water",
            },
            {
                "student_id": "STU-002",
                "university_id": "U002",
                "student_name": "Rohan Gupta",
                "department": "Computer Science",
            }
        ]),
        "projects": MockSupabaseTable([
            {
                "project_id": "PRJ-SMOKE-001",
                "challenge_id": "CHL-SMOKE-001",
                "university_id": "U001",
                "faculty_id": "FAC-001",
                "industry_id": "IND001",
                "project_title": "Solar Water Purification Project",
                "status": "proposed",
            }
        ]),
        "project_members": MockSupabaseTable([]),
        "project_milestones": MockSupabaseTable([]),
        "project_employee_interests": MockSupabaseTable([]),
        "feedback": MockSupabaseTable([]),
        "industries": MockSupabaseTable([
            {"industry_id": "IND001", "industry_name": "Tata CleanTech Solutions"}
        ]),
        "industry_employees": MockSupabaseTable([
            {
                "employee_id": "EMP-001",
                "industry_id": "IND001",
                "employee_name": "Suresh SPOC",
                "approval_authority": True,
            },
            {
                "employee_id": "EMP-002",
                "industry_id": "IND001",
                "employee_name": "Neha Engineer",
                "approval_authority": False,
            }
        ]),
        "government_authorities": MockSupabaseTable([
            {
                "officer_id": "GOV-001",
                "officer_name": "Dr. K. Sharma",
                "department": "Dept of Science & Tech",
                "district": "Ranchi",
            }
        ]),
    })

    return client, db


def run_smoke_tests():
    print("=" * 70)
    print("STARTING PHASE 26 DEMO-CRITICAL WORKFLOW SMOKE TESTS")
    print("=" * 70)

    client, mock_db = make_smoke_client()

    from app.routes import projects as prj_routes
    from app.services.project_workflow_service import ProjectWorkflowService
    from app.services.university_workflow_service import UniversityWorkflowService
    from app.services.industry_workflow_service import IndustryWorkflowService
    from app.services.feedback_service import FeedbackService
    from app.services.government_service import GovernmentService

    # Inject mock db into route services
    app.dependency_overrides[prj_routes.get_project_workflow_service] = lambda: ProjectWorkflowService(client=mock_db)
    app.dependency_overrides[prj_routes.get_workflow_service] = lambda: UniversityWorkflowService(client=mock_db)
    app.dependency_overrides[prj_routes.get_industry_workflow_service] = lambda: IndustryWorkflowService(client=mock_db)
    app.dependency_overrides[prj_routes.get_feedback_service] = lambda: FeedbackService(client=mock_db)

    # -------------------------------------------------------------------------
    # TEST 1: Student Project Discovery (Own university vs cross-university)
    # -------------------------------------------------------------------------
    student_u1 = AuthenticatedUser(
        user_id="usr-stu-01",
        email="amit@bitmesra.ac.in",
        role="student",
        stakeholder={"student_id": "STU-001", "university_id": "U001"},
    )
    student_u2 = AuthenticatedUser(
        user_id="usr-stu-02",
        email="rohan@iitdhanbad.ac.in",
        role="student",
        stakeholder={"student_id": "STU-002", "university_id": "U002"},
    )

    app.dependency_overrides[get_current_user] = lambda: student_u1
    app.dependency_overrides[get_current_user_optional] = lambda: student_u1

    res = client.get("/api/projects")
    assert res.status_code == 200
    projects = res.json()["data"]
    assert len(projects) == 1
    assert projects[0]["project_id"] == "PRJ-SMOKE-001"
    print("[PASS] 1. Student from U001 discovers eligible project PRJ-SMOKE-001.")

    # Student from U002 discovers nothing for U001
    app.dependency_overrides[get_current_user] = lambda: student_u2
    app.dependency_overrides[get_current_user_optional] = lambda: student_u2
    res2 = client.get("/api/projects")
    assert res2.status_code == 200
    assert len(res2.json()["data"]) == 0
    print("[PASS] 2. Student from U002 correctly sees 0 projects for U001 (cross-university isolation).")

    # -------------------------------------------------------------------------
    # TEST 2: Student Expresses Interest in Project
    # -------------------------------------------------------------------------
    app.dependency_overrides[get_current_user] = lambda: student_u1
    res_int = client.post(
        "/api/projects/PRJ-SMOKE-001/student-interest",
        json={"role": "researcher"}
    )
    assert res_int.status_code == 201, f"Expected 201, got {res_int.status_code}: {res_int.text}"
    assert res_int.json()["data"]["status"] == "pending"
    print("[PASS] 3. Student STU-001 successfully expressed interest (status: pending).")

    # Duplicate interest blocked
    res_dup = client.post(
        "/api/projects/PRJ-SMOKE-001/student-interest",
        json={"role": "researcher"}
    )
    assert res_dup.status_code == 400
    print("[PASS] 4. Duplicate student interest blocked with HTTP 400.")

    # Cross-university student expression blocked
    app.dependency_overrides[get_current_user] = lambda: student_u2
    res_cross = client.post(
        "/api/projects/PRJ-SMOKE-001/student-interest",
        json={"role": "researcher"}
    )
    assert res_cross.status_code == 400
    print("[PASS] 5. Cross-university student interest blocked with HTTP 400.")

    # -------------------------------------------------------------------------
    # TEST 3: Faculty Reviews & Selects Student
    # -------------------------------------------------------------------------
    faculty_u1 = AuthenticatedUser(
        user_id="usr-fac-01",
        email="verma@bitmesra.ac.in",
        role="faculty",
        stakeholder={"faculty_id": "FAC-001", "university_id": "U001"},
    )
    faculty_u2 = AuthenticatedUser(
        user_id="usr-fac-02",
        email="sen@iitdhanbad.ac.in",
        role="faculty",
        stakeholder={"faculty_id": "FAC-002", "university_id": "U002"},
    )

    # Faculty U2 tries to select -> 403 Forbidden
    app.dependency_overrides[get_current_user] = lambda: faculty_u2
    res_unauth = client.patch(
        "/api/projects/PRJ-SMOKE-001/members/STU-001",
        json={"status": "active"}
    )
    assert res_unauth.status_code == 403
    print("[PASS] 6. Unauthorized faculty (FAC-002) blocked with HTTP 403.")

    # Assigned Faculty U1 selects student -> 200 OK
    app.dependency_overrides[get_current_user] = lambda: faculty_u1
    res_sel = client.patch(
        "/api/projects/PRJ-SMOKE-001/members/STU-001",
        json={"status": "active"}
    )
    assert res_sel.status_code == 200
    assert res_sel.json()["data"]["status"] == "active"
    print("[PASS] 7. Assigned Faculty (FAC-001) successfully selected student to active team.")

    # -------------------------------------------------------------------------
    # TEST 4: Project Milestones & Completion Validation
    # -------------------------------------------------------------------------
    # Invalid completion percentage (> 100) -> 422 Unprocessable Entity
    res_inv_m = client.post(
        "/api/projects/PRJ-SMOKE-001/milestones",
        json={"milestone_name": "Field Sampling", "completion_percentage": 150}
    )
    assert res_inv_m.status_code == 422
    print("[PASS] 8. Invalid completion percentage (> 100) rejected with HTTP 422.")

    # Valid milestone creation
    res_m = client.post(
        "/api/projects/PRJ-SMOKE-001/milestones",
        json={
            "milestone_name": "Sensor Breadboard Prototype",
            "completion_percentage": 50,
            "description": "Assemble telemetry circuit with ESP32"
        }
    )
    assert res_m.status_code == 201
    mid = res_m.json()["data"]["milestone_id"]
    print(f"[PASS] 9. Valid milestone created with ID: {mid} (Status: in_progress/pending).")

    # Milestone update via /api/milestones/{id}
    res_upd_m = client.patch(
        f"/api/milestones/{mid}",
        json={"completion_percentage": 100, "evidence_url": "https://cdn.samadhansetu.gov.in/telemetry.pdf"}
    )
    assert res_upd_m.status_code == 200
    assert res_upd_m.json()["data"]["status"] == "completed"
    print("[PASS] 10. Milestone updated to 100% and automatically marked completed.")

    # -------------------------------------------------------------------------
    # TEST 5: Project Lifecycle Progression (proposed -> active -> prototype)
    # -------------------------------------------------------------------------
    # Student cannot advance project status -> 403
    app.dependency_overrides[get_current_user] = lambda: student_u1
    res_st_stat = client.patch(
        "/api/projects/PRJ-SMOKE-001/status",
        json={"status": "prototype"}
    )
    assert res_st_stat.status_code == 403
    print("[PASS] 11. Student blocked from advancing project lifecycle with HTTP 403.")

    # Faculty advances project status: (already moved to active by milestone creation) -> prototype
    app.dependency_overrides[get_current_user] = lambda: faculty_u1
    res_proto = client.patch(
        "/api/projects/PRJ-SMOKE-001/status",
        json={"status": "prototype", "justification": "Sensor breadboard completed"}
    )
    assert res_proto.status_code == 200, f"Expected 200, got {res_proto.status_code}: {res_proto.text}"
    assert res_proto.json()["data"]["current_status"] == "prototype"
    print("[PASS] 12. Faculty successfully advanced project through valid lifecycle (active -> prototype).")

    # Invalid jump (prototype -> completed) -> 400 Bad Request
    res_jump = client.patch(
        "/api/projects/PRJ-SMOKE-001/status",
        json={"status": "completed"}
    )
    assert res_jump.status_code == 400
    print("[PASS] 13. Invalid lifecycle leap rejected with HTTP 400.")

    # -------------------------------------------------------------------------
    # TEST 6: Industry SPOC Selection
    # -------------------------------------------------------------------------
    emp_spoc = AuthenticatedUser(
        user_id="usr-emp-01",
        email="suresh@tatacleantech.com",
        role="industry_employee",
        stakeholder={"employee_id": "EMP-001", "industry_id": "IND001", "approval_authority": True},
        is_verified=True,
        verification_status="verified",
        approval_authority=True,
    )
    emp_norm = AuthenticatedUser(
        user_id="usr-emp-02",
        email="neha@tatacleantech.com",
        role="industry_employee",
        stakeholder={"employee_id": "EMP-002", "industry_id": "IND001", "approval_authority": False},
        is_verified=True,
        verification_status="verified",
        approval_authority=False,
    )

    # Employee expresses interest
    app.dependency_overrides[get_current_user] = lambda: emp_norm
    res_emp_int = client.post(
        "/api/projects/PRJ-SMOKE-001/employee-interest",
        json={"message": "I specialize in clean water filtration systems."}
    )
    assert res_emp_int.status_code == 201
    iid = res_emp_int.json()["data"]["interest_id"]
    print(f"[PASS] 14. Industry employee expressed interest with ID: {iid}.")

    # SPOC selects employee
    app.dependency_overrides[get_current_user] = lambda: emp_spoc
    res_spoc_sel = client.patch(
        f"/api/projects/PRJ-SMOKE-001/employee-interests/{iid}",
        json={"status": "selected"}
    )
    assert res_spoc_sel.status_code == 200
    assert res_spoc_sel.json()["data"]["status"] == "selected"
    print("[PASS] 15. Industry SPOC officially selected employee for project.")

    # -------------------------------------------------------------------------
    # TEST 7: Stakeholder Feedback & Outcomes
    # -------------------------------------------------------------------------
    res_fb = client.post(
        "/api/projects/PRJ-SMOKE-001/feedback",
        json={"rating": 5, "comments": "Excellent prototype progress", "outcome": "Hardware verified"}
    )
    assert res_fb.status_code == 201
    print("[PASS] 16. Stakeholder feedback successfully recorded (Rating: 5/5).")

    # Invalid rating (> 5) -> 422
    res_bad_fb = client.post(
        "/api/projects/PRJ-SMOKE-001/feedback",
        json={"rating": 10, "comments": "Invalid rating"}
    )
    assert res_bad_fb.status_code == 422
    print("[PASS] 17. Invalid rating rejected with HTTP 422.")

    # -------------------------------------------------------------------------
    # TEST 8: Government Monitoring Roster & Analytics
    # -------------------------------------------------------------------------
    gov_officer = AuthenticatedUser(
        user_id="usr-gov-01",
        email="sharma@dst.gov.in",
        role="government",
        stakeholder={"officer_id": "GOV-001", "department": "DST", "district": "Ranchi"},
        is_verified=True,
        verification_status="verified",
    )
    from app.routes import government as gov_routes
    app.dependency_overrides[gov_routes.get_government_service] = lambda: GovernmentService(client=mock_db)
    app.dependency_overrides[get_current_user] = lambda: gov_officer

    res_gov_kpi = client.get("/api/government/analytics")
    assert res_gov_kpi.status_code == 200
    assert res_gov_kpi.json()["success"] is True
    print("[PASS] 18. Government KPI monitoring analytics retrieved successfully.")

    # Non-government user blocked from monitoring -> 403
    app.dependency_overrides[get_current_user] = lambda: student_u1
    res_gov_blocked = client.get("/api/government/analytics")
    assert res_gov_blocked.status_code in [401, 403]
    print("[PASS] 19. Non-government user strictly blocked from government monitoring.")

    # -------------------------------------------------------------------------
    # TEST 9: Citizen Safe Project Visibility
    # -------------------------------------------------------------------------
    cit_user = AuthenticatedUser(
        user_id="usr-cit-01",
        email="ramesh@citizen.in",
        role="citizen",
        stakeholder=None,
    )
    from app.routes import challenges as ch_routes
    from app.services.challenge_service import ChallengeService
    app.dependency_overrides[ch_routes.get_challenge_service] = lambda: ChallengeService(client=mock_db)
    app.dependency_overrides[get_current_user] = lambda: cit_user
    app.dependency_overrides[get_current_user_optional] = lambda: cit_user

    res_cit_ch = client.get("/api/challenges/CHL-SMOKE-001")
    assert res_cit_ch.status_code == 200
    ch_data = res_cit_ch.json()["data"]
    assert ch_data["project"] is not None
    assert ch_data["project"]["project_title"] == "Solar Water Purification Project"
    # Ensure no private student or employee lists leaked in citizen challenge view
    assert "students" not in ch_data["project"]
    assert "employees" not in ch_data["project"]
    print("[PASS] 20. Citizen views high-level project progress without sensitive data leakage.")

    print("=" * 70)
    print("ALL 20 PHASE 26 DEMO-CRITICAL SMOKE TESTS PASSED!")
    print("=" * 70)


if __name__ == "__main__":
    run_smoke_tests()
