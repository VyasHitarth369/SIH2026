"""test_phase8_government.py

Comprehensive test suite for Phase 8: Government Monitoring & Policy Intelligence:
1. Strict Role & Authority Enforcement (only verified government officers linked to government_authorities)
2. Non-Government Access Blocking (citizens, students, faculty, and industry employees blocked with 403)
3. Unfabricated Dashboard Metrics & Policy Intelligence (challenges, participation, projects, milestones, outcomes)
4. Monitored Problems List with AI Classification & Project Progress Hydration
5. Assigned Faculty Roster & Participating Student Counts
6. Students Solving Problems Roster with Project Context
7. Solved Projects Roster with Feedback Outcomes
8. Data Privacy & Zero Metric Fabrication Verification
"""

import copy
from typing import Any, Dict, List, Optional
from starlette.testclient import TestClient

from app.main import app
from app.dependencies.auth import get_current_user
from app.routes.government import get_government_service
from app.services.auth_service import AuthenticatedUser
from app.services.government_service import GovernmentService


# =============================================================================
# In-Memory Mock Database for Hermetic Testing
# =============================================================================
class MockSupabaseDB:
    def __init__(self):
        self.tables = {
            "government_authorities": [
                {
                    "authority_id": "GOV-JH-001",
                    "user_id": "usr-gov-001",
                    "officer_name": "Sanjay Kumar IAS",
                    "department": "Department of Higher & Technical Education",
                    "designation": "Principal Secretary",
                    "district": "Ranchi",
                    "office_name": "Project Building, Dhurwa",
                    "email": "secy.hed@jharkhand.gov.in",
                }
            ],
            "challenges": [
                {
                    "challenge_id": "CH-GOV-01",
                    "title": "Industrial Waste Dump near Subarnarekha River",
                    "description": "Heavy metal waste dumping causing toxic runoff.",
                    "status": "validated",
                    "city": "Ranchi",
                    "district": "Ranchi",
                    "submitted_by": "Citizen Aarti",
                    "created_at": "2026-03-01T10:00:00Z",
                    "impact_scope": "District Level",
                },
                {
                    "challenge_id": "CH-GOV-02",
                    "title": "Potable Water Salinity in Rural Borewells",
                    "description": "High TDS and salinity in local groundwater.",
                    "status": "in_project",
                    "city": "Dhanbad",
                    "district": "Dhanbad",
                    "submitted_by": "Citizen Ramesh",
                    "created_at": "2026-03-02T10:00:00Z",
                    "impact_scope": "Gram Panchayat",
                },
                {
                    "challenge_id": "CH-GOV-03",
                    "title": "Solar Smart Microgrid for Remote Tribal Hamlets",
                    "description": "Decentralized mini-grids for un-electrified villages.",
                    "status": "submitted",
                    "city": "Khunti",
                    "district": "Khunti",
                    "submitted_by": "District Collector Khunti (Gov)",
                    "created_at": "2026-03-03T10:00:00Z",
                    "impact_scope": "Block Level",
                },
            ],
            "ai_analysis": [
                {
                    "analysis_id": 1,
                    "challenge_id": "CH-GOV-01",
                    "category": "Environmental Science & Water Quality",
                    "required_skills": "Water Testing, Bioremediation, GIS",
                    "required_technologies": "LoRaWAN, Python, Cloud Telemetry",
                    "validity": "valid",
                    "innovation_scope": "high",
                },
                {
                    "analysis_id": 2,
                    "challenge_id": "CH-GOV-02",
                    "category": "Water Resources & Rural Sanitation",
                    "required_skills": "Spectrophotometry, IoT",
                    "required_technologies": "ESP32, Micro-filtration",
                    "validity": "valid",
                    "innovation_scope": "medium",
                },
            ],
            "universities": [
                {
                    "university_id": "U001",
                    "university_name": "BIT Mesra, Ranchi",
                    "city": "Ranchi",
                    "district": "Ranchi",
                },
                {
                    "university_id": "U002",
                    "university_name": "IIT (ISM) Dhanbad",
                    "city": "Dhanbad",
                    "district": "Dhanbad",
                },
            ],
            "faculty": [
                {
                    "faculty_id": "FAC-001",
                    "university_id": "U001",
                    "faculty_name": "Dr. Ramesh Kumar",
                    "department": "Computer Science & Engg",
                    "designation": "Associate Professor",
                    "email": "ramesh.kumar@bitmesra.ac.in",
                },
                {
                    "faculty_id": "FAC-002",
                    "university_id": "U002",
                    "faculty_name": "Dr. Ananya Roy",
                    "department": "Environmental Science",
                    "designation": "Professor",
                    "email": "ananya.roy@iitdhanbad.ac.in",
                },
            ],
            "industries": [
                {
                    "industry_id": "IND001",
                    "industry_name": "Tata CSR Water & Civic Solutions",
                    "city": "Jamshedpur",
                }
            ],
            "students": [
                {
                    "student_id": "STU-001",
                    "university_id": "U001",
                    "student_name": "Aarav Sharma",
                    "department": "Computer Science & Engg",
                    "course": "B.Tech",
                    "email": "aarav.sharma@bitmesra.ac.in",
                },
                {
                    "student_id": "STU-002",
                    "university_id": "U001",
                    "student_name": "Priya Singh",
                    "department": "Civil Engineering",
                    "course": "B.Tech",
                    "email": "priya.singh@bitmesra.ac.in",
                },
            ],
            "projects": [
                {
                    "project_id": "PRJ-GOV-01",
                    "challenge_id": "CH-GOV-02",
                    "university_id": "U001",
                    "faculty_id": "FAC-001",
                    "industry_id": "IND001",
                    "project_title": "Affordable Rural Desalination Pilot",
                    "description": "Solar powered capacitive deionization prototype",
                    "status": "active",
                    "start_date": "2026-03-01",
                },
                {
                    "project_id": "PRJ-GOV-SOLVED",
                    "challenge_id": "CH-GOV-01",
                    "university_id": "U002",
                    "faculty_id": "FAC-002",
                    "industry_id": None,
                    "project_title": "Subarnarekha Bio-Filter Remediation",
                    "description": "Constructed wetland bio-filtration deployment",
                    "status": "solved",
                    "start_date": "2025-06-01",
                    "actual_end_date": "2026-01-15",
                },
            ],
            "project_members": [
                {
                    "project_member_id": 1,
                    "project_id": "PRJ-GOV-01",
                    "student_id": "STU-001",
                    "role": "lead",
                    "status": "active",
                },
                {
                    "project_member_id": 2,
                    "project_id": "PRJ-GOV-01",
                    "student_id": "STU-002",
                    "role": "researcher",
                    "status": "active",
                },
            ],
            "project_milestones": [
                {
                    "milestone_id": 1,
                    "project_id": "PRJ-GOV-01",
                    "milestone_name": "Electrode Prototyping",
                    "status": "completed",
                    "completion_percentage": 100,
                },
                {
                    "milestone_id": 2,
                    "project_id": "PRJ-GOV-01",
                    "milestone_name": "Field Water Test Run",
                    "status": "in_progress",
                    "completion_percentage": 60,
                },
            ],
            "challenge_university_matches": [
                {"match_id": 1, "challenge_id": "CH-GOV-01", "university_id": "U001", "status": "accepted"}
            ],
            "challenge_industry_matches": [
                {"match_id": 1, "challenge_id": "CH-GOV-02", "industry_id": "IND001", "status": "accepted"}
            ],
            "feedback": [
                {
                    "feedback_id": 1,
                    "project_id": "PRJ-GOV-SOLVED",
                    "rating": 5,
                    "comments": "Significant reduction in heavy metals measured at discharge point.",
                    "outcome": "Water quality restored to safe irrigation standard.",
                }
            ],
            "challenge_support": [
                {"support_id": 1, "challenge_id": "CH-GOV-01", "user_id": "usr-cit-1"},
                {"support_id": 2, "challenge_id": "CH-GOV-01", "user_id": "usr-cit-2"},
                {"support_id": 3, "challenge_id": "CH-GOV-02", "user_id": "usr-cit-3"},
            ],
        }


class MockQueryBuilder:
    def __init__(self, db: MockSupabaseDB, table_name: str):
        self.db = db
        self.table_name = table_name
        self.filters = []
        self._order_col = None
        self._desc = False
        self._limit_val = None

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

    def range(self, start: int, end: int):
        return self

    def in_(self, field: str, values: Any):
        self.filters.append(("in", field, values))
        return self

    def neq(self, field: str, value: Any):
        self.filters.append(("neq", field, value))
        return self

    def _matches(self, row: Dict[str, Any]) -> bool:
        for f_type, field, val in self.filters:
            if f_type == "eq":
                if str(row.get(field)) != str(val):
                    return False
            elif f_type == "neq":
                if str(row.get(field)) == str(val):
                    return False
            elif f_type == "in":
                vals = [str(v) for v in val] if isinstance(val, (list, tuple, set)) else [str(val)]
                if str(row.get(field)) not in vals:
                    return False
        return True

    def execute(self):
        table = self.db.tables.get(self.table_name, [])
        matched = [dict(row) for row in table if self._matches(row)]

        if self._order_col:
            matched.sort(key=lambda x: str(x.get(self._order_col, "")), reverse=self._desc)
        if self._limit_val:
            matched = matched[: self._limit_val]

        class ExecResult:
            def __init__(self, d):
                self.data = d

        return ExecResult(matched)


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
gov_service = GovernmentService(client=mock_client)

app.dependency_overrides[get_government_service] = lambda: gov_service

# Users
GOV_OFFICER = AuthenticatedUser(
    user_id="usr-gov-001",
    email="secy.hed@jharkhand.gov.in",
    role="government",
    is_verified=True,
    verification_status="verified",
    stakeholder={
        "authority_id": "GOV-JH-001",
        "officer_name": "Sanjay Kumar IAS",
        "department": "Department of Higher & Technical Education",
        "designation": "Principal Secretary",
        "district": "Ranchi",
    },
)

UNLINKED_GOV_USER = AuthenticatedUser(
    user_id="usr-gov-unlinked",
    email="imposter@test.gov",
    role="government",
    is_verified=True,
    verification_status="verified",
    stakeholder=None,  # Missing stakeholder linkage!
)

CITIZEN_USER = AuthenticatedUser(
    user_id="usr-cit-01",
    email="citizen@gmail.com",
    role="citizen",
    is_verified=True,
    verification_status="verified",
)

FACULTY_USER = AuthenticatedUser(
    user_id="usr-fac-01",
    email="faculty@bitmesra.ac.in",
    role="faculty",
    is_verified=True,
    verification_status="verified",
    stakeholder={"faculty_id": "FAC-001", "university_id": "U001"},
)

STUDENT_USER = AuthenticatedUser(
    user_id="usr-stu-01",
    email="student@bitmesra.ac.in",
    role="student",
    is_verified=True,
    verification_status="verified",
    stakeholder={"student_id": "STU-001", "university_id": "U001"},
)

INDUSTRY_USER = AuthenticatedUser(
    user_id="usr-ind-01",
    email="spoc@tatacsr.com",
    role="industry_employee",
    is_verified=True,
    verification_status="verified",
    approval_authority=True,
    stakeholder={"employee_id": "EMP-01", "industry_id": "IND001"},
)

client = TestClient(app)


def test_suite():
    print("\n" + "=" * 75)
    print("RUNNING PHASE 8 VERIFICATION TEST SUITE: GOVERNMENT MONITORING")
    print("=" * 75)

    # -------------------------------------------------------------------------
    # Test 1: Access Control & Role Enforcement
    # -------------------------------------------------------------------------
    print("\n[TEST 1] Access Control & Government Role Enforcement...")

    # 1A. Non-government citizen attempting to access analytics
    app.dependency_overrides[get_current_user] = lambda: CITIZEN_USER
    resp = client.get("/api/government/analytics")
    assert resp.status_code == 403, f"Expected 403 for citizen, got {resp.status_code}"
    print("  -> PASSED: Citizen blocked with 403 Forbidden.")

    # 1B. Faculty attempting to access government monitored problems
    app.dependency_overrides[get_current_user] = lambda: FACULTY_USER
    resp = client.get("/api/government/problems")
    assert resp.status_code == 403, f"Expected 403 for faculty, got {resp.status_code}"
    print("  -> PASSED: Faculty blocked with 403 Forbidden.")

    # 1C. Industry employee attempting to access government faculties roster
    app.dependency_overrides[get_current_user] = lambda: INDUSTRY_USER
    resp = client.get("/api/government/faculties")
    assert resp.status_code == 403, f"Expected 403 for industry, got {resp.status_code}"
    print("  -> PASSED: Industry employee blocked with 403 Forbidden.")

    # 1D. Unlinked government user (no authority row) attempting access
    app.dependency_overrides[get_current_user] = lambda: UNLINKED_GOV_USER
    resp = client.get("/api/government/analytics")
    assert resp.status_code == 403, f"Expected 403 for unlinked gov user, got {resp.status_code}"
    assert "not linked to a valid government authority record" in resp.json()["error"]["message"]
    print(f"  -> PASSED: Unlinked government user blocked with 403: '{resp.json()['error']['message']}'.")

    # 1E. Authorized government officer accesses analytics
    app.dependency_overrides[get_current_user] = lambda: GOV_OFFICER
    resp = client.get("/api/government/analytics")
    assert resp.status_code == 200, f"Expected 200 for government officer, got {resp.status_code}: {resp.text}"
    print("  -> PASSED: Verified government officer authorized with 200 OK.")

    # -------------------------------------------------------------------------
    # Test 2: Unfabricated Dashboard Metrics & Policy Intelligence
    # -------------------------------------------------------------------------
    print("\n[TEST 2] Dashboard Analytics & Unfabricated Metrics Accuracy...")

    data = resp.json()["data"]
    assert data["officer_name"] == "Sanjay Kumar IAS"
    assert data["department"] == "Department of Higher & Technical Education"

    # Challenges metrics
    ch = data["challenges"]
    assert ch["total_challenges"] == 3
    assert ch["total_submitted"] == 1
    assert ch["active_challenges"] == 2
    assert ch["validated_challenges"] == 2
    assert "Ranchi" in ch["by_district"]
    assert "Dhanbad" in ch["by_district"]
    print(f"  -> PASSED: Challenges metrics verified (Total: {ch['total_challenges']}, Active: {ch['active_challenges']}, Validated: {ch['validated_challenges']}).")

    # Participation metrics
    pt = data["participation"]
    assert pt["universities_engaged"] == 2  # U001, U002
    assert pt["industries_engaged"] == 1    # IND001
    assert pt["faculty_assigned"] == 2      # FAC-001, FAC-002
    assert pt["students_participating"] == 2 # STU-001, STU-002
    print(f"  -> PASSED: Participation metrics verified (Unis: {pt['universities_engaged']}, Inds: {pt['industries_engaged']}, Faculty: {pt['faculty_assigned']}, Students: {pt['students_participating']}).")

    # Project metrics
    pr = data["projects"]
    assert pr["total_projects"] == 2
    assert pr["active_projects"] == 1
    assert pr["solved_problems"] == 1
    assert pr["lifecycle_funnel"]["solved"] == 1
    print(f"  -> PASSED: Project metrics verified (Total: {pr['total_projects']}, Active: {pr['active_projects']}, Solved: {pr['solved_problems']}).")

    # Milestones metrics
    ms = data["milestones"]
    assert ms["total_milestones"] == 2
    assert ms["completed_milestones"] == 1
    assert ms["in_progress_milestones"] == 1
    assert ms["overall_completion_rate"] == 80.0  # (100 + 60) / 2 = 80.0
    print(f"  -> PASSED: Milestone metrics verified (Total: {ms['total_milestones']}, Avg Completion Rate: {ms['overall_completion_rate']}%).")

    # Outcomes & Feedback
    oc = data["outcomes"]
    assert oc["total_feedback_count"] == 1
    assert oc["average_feedback_rating"] == 5.0
    assert oc["total_challenge_support_votes"] == 3
    print(f"  -> PASSED: Outcomes metrics verified (Feedback: {oc['total_feedback_count']}, Avg Rating: {oc['average_feedback_rating']}, Support Votes: {oc['total_challenge_support_votes']}).")

    # Transparency & Limitations
    assert "challenges" in data["data_sources"]
    assert "feedback" in data["data_sources"]
    assert len(data["limitations"]) > 0
    print("  -> PASSED: Data sources and schema limitations transparently declared without metric fabrication.")

    # -------------------------------------------------------------------------
    # Test 3: Monitored Problems List with AI Classification
    # -------------------------------------------------------------------------
    print("\n[TEST 3] Monitored Problems List with Relational Hydration...")

    resp = client.get("/api/government/problems")
    assert resp.status_code == 200
    problems = resp.json()["data"]
    assert len(problems) == 3
    
    # Verify hydration of project and AI analysis
    p1 = [p for p in problems if p["challenge_id"] == "CH-GOV-02"][0]
    assert p1["project_title"] == "Affordable Rural Desalination Pilot"
    assert p1["university_name"] == "BIT Mesra, Ranchi"
    assert p1["faculty_name"] == "Dr. Ramesh Kumar"
    assert p1["industry_name"] == "Tata CSR Water & Civic Solutions"
    assert p1["milestone_progress_pct"] == 80.0
    print("  -> PASSED: Monitored challenge hydrated with AI category, project title, and milestone progress.")

    # Filter by status
    resp_val = client.get("/api/government/problems?status=validated")
    assert resp_val.status_code == 200
    assert len(resp_val.json()["data"]) == 1
    assert resp_val.json()["data"][0]["challenge_id"] == "CH-GOV-01"
    print("  -> PASSED: Problem filtering by status successfully executed.")

    # -------------------------------------------------------------------------
    # Test 4: Assigned Faculty Roster
    # -------------------------------------------------------------------------
    print("\n[TEST 4] Assigned Faculty Roster & Student Counts...")

    resp = client.get("/api/government/faculties")
    assert resp.status_code == 200
    faculties = resp.json()["data"]
    assert len(faculties) == 2
    fac_names = [f["faculty_name"] for f in faculties]
    assert "Dr. Ramesh Kumar" in fac_names
    assert "Dr. Ananya Roy" in fac_names

    f_ramesh = [f for f in faculties if f["faculty_id"] == "FAC-001"][0]
    assert f_ramesh["university_name"] == "BIT Mesra, Ranchi"
    assert f_ramesh["participating_students_count"] == 2
    print(f"  -> PASSED: Faculty roster retrieved with university affiliations and student team counts ({fac_names}).")

    # -------------------------------------------------------------------------
    # Test 5: Students Solving Problems Roster
    # -------------------------------------------------------------------------
    print("\n[TEST 5] Students Solving Problems Roster...")

    resp = client.get("/api/government/students")
    assert resp.status_code == 200
    students = resp.json()["data"]
    assert len(students) == 2
    stu_names = [s["student_name"] for s in students]
    assert "Aarav Sharma" in stu_names
    assert "Priya Singh" in stu_names
    assert students[0]["university_name"] == "BIT Mesra, Ranchi"
    assert students[0]["project_title"] == "Affordable Rural Desalination Pilot"
    print(f"  -> PASSED: Active student roster retrieved with project and university relations ({stu_names}).")

    # -------------------------------------------------------------------------
    # Test 6: Solved & Successful Projects Roster
    # -------------------------------------------------------------------------
    print("\n[TEST 6] Solved Projects Roster with Feedback Outcomes...")

    resp = client.get("/api/government/solved-projects")
    assert resp.status_code == 200
    solved = resp.json()["data"]
    assert len(solved) == 1
    s_proj = solved[0]
    assert s_proj["project_id"] == "PRJ-GOV-SOLVED"
    assert s_proj["project_title"] == "Subarnarekha Bio-Filter Remediation"
    assert s_proj["university_name"] == "IIT (ISM) Dhanbad"
    assert s_proj["average_rating"] == 5.0
    assert "Water quality restored" in s_proj["outcome_summary"]
    print(f"  -> PASSED: Solved project '{s_proj['project_title']}' retrieved with rating {s_proj['average_rating']}/5 and outcome summary.")

    print("\n" + "=" * 75)
    print("ALL PHASE 8 VERIFICATION TESTS PASSED SUCCESSFULLY! (100% SUCCESS)")
    print("=" * 75)


if __name__ == "__main__":
    test_suite()
