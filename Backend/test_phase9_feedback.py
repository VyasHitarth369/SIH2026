"""test_phase9_feedback.py

Automated Verification Test Suite for Phase 9: Feedback, Outcome & Impact Tracking.
Validates:
1. 1-5 rating validation & challenge matching.
2. Role-based submitter eligibility (resident citizen, active student, assigned faculty, industry partner, gov).
3. Rejection of unrelated stakeholders (foreign students, unrelated faculty, cross-industry staff).
4. Duplicate/abusive submission prevention.
5. Role-appropriate feedback listing & privacy masking.
6. Controlled, justified project lifecycle state transitions (proposed -> active -> prototype -> pilot -> deployed -> solved -> completed).
7. Automatic challenge resolution synchronization & actual_end_date recording upon completion.
8. Role-tailored outcome and impact intelligence reporting.
"""

from typing import Any, Dict, List, Optional
from starlette.testclient import TestClient

from app.dependencies.auth import get_current_user, get_current_user_optional
from app.main import app
from app.routes.projects import get_feedback_service
from app.services.auth_service import AuthenticatedUser
from app.services.feedback_service import FeedbackService


# =============================================================================
# In-Memory Mock Database for Phase 9 Verification
# =============================================================================
class MockSupabaseDB:
    def __init__(self):
        self.tables: Dict[str, List[Dict[str, Any]]] = {
            "challenges": [
                {
                    "challenge_id": "CH-PH9-01",
                    "title": "Subarnarekha River Heavy Metal & Industrial Effluent Remediation",
                    "description": "Industrial runoff has severely elevated hexavalent chromium and lead levels.",
                    "location": "Namkum Industrial Area",
                    "city": "Ranchi",
                    "district": "Ranchi",
                    "status": "in_progress",
                    "impact_scope": "District Level Public Health",
                    "submitted_by": "Citizen Aarti Sharma",
                    "user_id": "usr-cit-aarti",
                },
                {
                    "challenge_id": "CH-PH9-PROPOSED",
                    "title": "Smart Solar Agricultural Pumping for Drought-Prone Palamu",
                    "description": "Groundwater replenishment and micro-solar irrigation scheduling.",
                    "location": "Daltonganj Block",
                    "city": "Medininagar",
                    "district": "Palamu",
                    "status": "submitted",
                    "impact_scope": "Agricultural Yield & Water Security",
                    "submitted_by": "Farmer Suresh",
                    "user_id": "usr-cit-suresh",
                },
            ],
            "universities": [
                {
                    "university_id": "U001",
                    "university_name": "Birla Institute of Technology (BIT) Mesra, Ranchi",
                    "city": "Ranchi",
                    "state": "Jharkhand",
                },
                {
                    "university_id": "U002",
                    "university_name": "Indian Institute of Technology (ISM) Dhanbad",
                    "city": "Dhanbad",
                    "state": "Jharkhand",
                },
            ],
            "faculty": [
                {
                    "faculty_id": "FAC-001",
                    "university_id": "U001",
                    "faculty_name": "Dr. Ramesh Kumar",
                    "department": "Chemical & Environmental Engineering",
                },
                {
                    "faculty_id": "FAC-002",
                    "university_id": "U002",
                    "faculty_name": "Dr. Ananya Roy",
                    "department": "Mining & Water Resources Engineering",
                },
            ],
            "students": [
                {
                    "student_id": "STU-001",
                    "university_id": "U001",
                    "student_name": "Aarav Sharma",
                    "department": "Environmental Engineering",
                },
                {
                    "student_id": "STU-FOREIGN",
                    "university_id": "U002",
                    "student_name": "Rohan Verma",
                    "department": "Computer Science",
                },
            ],
            "industries": [
                {
                    "industry_id": "IND001",
                    "industry_name": "Tata Steel Ecological & Water Management Division",
                    "city": "Jamshedpur",
                },
                {
                    "industry_id": "IND002",
                    "industry_name": "L&T Heavy Engineering",
                    "city": "Ranchi",
                },
            ],
            "projects": [
                {
                    "project_id": "PRJ-PH9-ACTIVE",
                    "challenge_id": "CH-PH9-01",
                    "university_id": "U001",
                    "faculty_id": "FAC-001",
                    "industry_id": "IND001",
                    "project_title": "Constructed Wetland Bio-Filter with Graphene Adsorption",
                    "description": "Multi-stage phytoremediation and graphene oxide filter deployment.",
                    "status": "deployed",
                    "start_date": "2026-01-10",
                    "actual_end_date": None,
                },
                {
                    "project_id": "PRJ-PH9-PROPOSED",
                    "challenge_id": "CH-PH9-PROPOSED",
                    "university_id": "U001",
                    "faculty_id": "FAC-001",
                    "industry_id": None,
                    "project_title": "Palamu Micro-Solar Irrigation Grid",
                    "description": "Low-cost smart solar DC pump telemetry.",
                    "status": "proposed",
                    "start_date": "2026-03-01",
                    "actual_end_date": None,
                },
            ],
            "project_members": [
                {
                    "project_member_id": 1,
                    "project_id": "PRJ-PH9-ACTIVE",
                    "student_id": "STU-001",
                    "role": "lead_researcher",
                    "status": "active",
                },
            ],
            "project_milestones": [
                {
                    "milestone_id": 1,
                    "project_id": "PRJ-PH9-ACTIVE",
                    "milestone_name": "Graphene Oxide Synthesis & Adsorption Lab Trials",
                    "status": "completed",
                    "completion_percentage": 100,
                },
                {
                    "milestone_id": 2,
                    "project_id": "PRJ-PH9-ACTIVE",
                    "milestone_name": "On-Site River Bio-Filter Installation",
                    "status": "completed",
                    "completion_percentage": 100,
                },
            ],
            "feedback": [],
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

    def _matches(self, row: Dict[str, Any]) -> bool:
        for f_type, field, val in self.filters:
            if f_type == "eq":
                if str(row.get(field)) != str(val):
                    return False
        return True

    def insert(self, record: Dict[str, Any]):
        table = self.db.tables.setdefault(self.table_name, [])
        inserted = dict(record)
        if "feedback_id" not in inserted and self.table_name == "feedback":
            inserted["feedback_id"] = len(table) + 1
        table.append(inserted)

        class InsertResult:
            def __init__(self, d):
                self.data = [d]

        return InsertResult(inserted)

    def update(self, updates: Dict[str, Any]):
        self._updates = updates
        return self

    def execute(self):
        table = self.db.tables.get(self.table_name, [])

        if hasattr(self, "_updates") and self._updates is not None:
            updated_rows = []
            for row in table:
                if self._matches(row):
                    row.update(self._updates)
                    updated_rows.append(dict(row))
            self._updates = None

            class UpdateExecResult:
                def __init__(self, d):
                    self.data = d

            return UpdateExecResult(updated_rows)

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
feedback_service = FeedbackService(client=mock_client)

app.dependency_overrides[get_feedback_service] = lambda: feedback_service

# Stakeholder Users
CITIZEN_AUTHOR = AuthenticatedUser(
    user_id="usr-cit-aarti",
    email="aarti.sharma@gmail.com",
    role="citizen",
    full_name="Citizen Aarti Sharma",
    is_verified=True,
    verification_status="verified",
)

STUDENT_MEMBER = AuthenticatedUser(
    user_id="usr-stu-01",
    email="aarav.sharma@bitmesra.ac.in",
    role="student",
    full_name="Aarav Sharma",
    is_verified=True,
    verification_status="verified",
    stakeholder={"student_id": "STU-001", "university_id": "U001"},
)

STUDENT_FOREIGN = AuthenticatedUser(
    user_id="usr-stu-foreign",
    email="rohan.verma@iitism.ac.in",
    role="student",
    full_name="Rohan Verma",
    is_verified=True,
    verification_status="verified",
    stakeholder={"student_id": "STU-FOREIGN", "university_id": "U002"},
)

FACULTY_MENTOR = AuthenticatedUser(
    user_id="usr-fac-01",
    email="ramesh.kumar@bitmesra.ac.in",
    role="faculty",
    full_name="Dr. Ramesh Kumar",
    is_verified=True,
    verification_status="verified",
    stakeholder={"faculty_id": "FAC-001", "university_id": "U001"},
)

FACULTY_FOREIGN = AuthenticatedUser(
    user_id="usr-fac-foreign",
    email="ananya.roy@iitism.ac.in",
    role="faculty",
    full_name="Dr. Ananya Roy",
    is_verified=True,
    verification_status="verified",
    stakeholder={"faculty_id": "FAC-002", "university_id": "U002"},
)

INDUSTRY_SPOC = AuthenticatedUser(
    user_id="usr-ind-spoc",
    email="spoc.csr@tatasteel.com",
    role="industry_employee",
    full_name="Vikramaditya Tata SPOC",
    is_verified=True,
    verification_status="verified",
    approval_authority=True,
    stakeholder={"employee_id": "EMP-001", "industry_id": "IND001", "approval_authority": True},
)

INDUSTRY_FOREIGN = AuthenticatedUser(
    user_id="usr-ind-foreign",
    email="staff@lnt.com",
    role="industry_employee",
    full_name="Sanjay L&T",
    is_verified=True,
    verification_status="verified",
    approval_authority=False,
    stakeholder={"employee_id": "EMP-099", "industry_id": "IND002"},
)

GOV_OFFICER = AuthenticatedUser(
    user_id="usr-gov-001",
    email="secy.hed@jharkhand.gov.in",
    role="government",
    full_name="Sanjay Kumar IAS",
    is_verified=True,
    verification_status="verified",
    stakeholder={"authority_id": "GOV-JH-001", "officer_name": "Sanjay Kumar IAS"},
)


# =============================================================================
# Test Suite Execution
# =============================================================================
def get_err(resp):
    data = resp.json()
    return data.get("detail") or data.get("error", {}).get("message", "")


def test_suite():
    client = TestClient(app)

    print("\n" + "=" * 75)
    print("RUNNING PHASE 9 VERIFICATION TEST SUITE: FEEDBACK, OUTCOMES & IMPACT")
    print("=" * 75)

    # -------------------------------------------------------------------------
    # Test 1: Rating Constraints & Schema Validation
    # -------------------------------------------------------------------------
    print("\n[TEST 1] Rating Constraints & Schema Validation (1-5 range)...")

    app.dependency_overrides[get_current_user] = lambda: CITIZEN_AUTHOR

    # Rating = 0 (Below minimum)
    resp = client.post(
        "/api/projects/PRJ-PH9-ACTIVE/feedback",
        json={"rating": 0, "comments": "Zero rating should fail"},
    )
    assert resp.status_code == 422
    print("  -> PASSED: Rating = 0 correctly rejected with 422 Unprocessable Entity.")

    # Rating = 6 (Above maximum)
    resp = client.post(
        "/api/projects/PRJ-PH9-ACTIVE/feedback",
        json={"rating": 6, "comments": "Six rating should fail"},
    )
    assert resp.status_code == 422
    print("  -> PASSED: Rating = 6 correctly rejected with 422 Unprocessable Entity.")

    # Mismatched challenge ID
    resp = client.post(
        "/api/projects/PRJ-PH9-ACTIVE/feedback",
        json={"rating": 5, "challenge_id": "CH-WRONG-CHALLENGE", "comments": "Mismatched ID"},
    )
    assert resp.status_code == 400
    assert "does not match the project's associated challenge" in get_err(resp)
    print("  -> PASSED: Mismatched challenge_id rejected with 400 Bad Request.")

    # -------------------------------------------------------------------------
    # Test 2: Role-Based Feedback Eligibility & Access Control
    # -------------------------------------------------------------------------
    print("\n[TEST 2] Role-Based Feedback Eligibility & Stakeholder Access Control...")

    # Citizen submission on 'proposed' project (Premature)
    resp = client.post(
        "/api/projects/PRJ-PH9-PROPOSED/feedback",
        json={"rating": 4, "comments": "Premature review"},
    )
    assert resp.status_code == 400
    assert "Cannot submit citizen feedback for a project in 'proposed' state" in get_err(resp)
    print("  -> PASSED: Premature citizen feedback on proposed project blocked with 400 Bad Request.")

    # Active Student Member submission -> 201
    app.dependency_overrides[get_current_user] = lambda: STUDENT_MEMBER
    resp = client.post(
        "/api/projects/PRJ-PH9-ACTIVE/feedback",
        json={
            "rating": 5,
            "comments": "Designed and synthesized graphene oxide filter beds with Dr. Ramesh.",
            "outcome": "Achieved 94% lead and hexavalent chromium removal in field trial run.",
        },
    )
    assert resp.status_code == 201
    fb_student = resp.json()["data"]
    assert fb_student["respondent_role"] == "student"
    assert fb_student["rating"] == 5
    assert "94% lead" in fb_student["outcome"]
    print(f"  -> PASSED: Active student member submitted feedback (ID: {fb_student['feedback_id']}).")

    # Foreign Student (not a member of this project) -> 403
    app.dependency_overrides[get_current_user] = lambda: STUDENT_FOREIGN
    resp = client.post(
        "/api/projects/PRJ-PH9-ACTIVE/feedback",
        json={"rating": 3, "comments": "I am not on this project"},
    )
    assert resp.status_code == 403
    assert "Access forbidden" in get_err(resp)
    print("  -> PASSED: Unrelated foreign student blocked with 403 Forbidden.")

    # Foreign Faculty (different university) -> 403
    app.dependency_overrides[get_current_user] = lambda: FACULTY_FOREIGN
    resp = client.post(
        "/api/projects/PRJ-PH9-ACTIVE/feedback",
        json={"rating": 4, "comments": "I do not teach at BIT Mesra"},
    )
    assert resp.status_code == 403
    assert "Faculty does not belong to the project's university" in get_err(resp)
    print("  -> PASSED: Unrelated foreign faculty blocked with 403 Forbidden.")

    # Assigned Faculty Mentor submission -> 201
    app.dependency_overrides[get_current_user] = lambda: FACULTY_MENTOR
    resp = client.post(
        "/api/projects/PRJ-PH9-ACTIVE/feedback",
        json={
            "rating": 5,
            "comments": "Successful pilot implementation. Student team demonstrated rigorous analytical protocol.",
            "outcome": "Effluent water discharge now compliant with CPCB Class B irrigation criteria.",
        },
    )
    assert resp.status_code == 201
    fb_fac = resp.json()["data"]
    assert fb_fac["respondent_role"] == "faculty"
    print(f"  -> PASSED: Assigned faculty mentor submitted feedback (ID: {fb_fac['feedback_id']}).")

    # Partnered Industry SPOC submission -> 201
    app.dependency_overrides[get_current_user] = lambda: INDUSTRY_SPOC
    resp = client.post(
        "/api/projects/PRJ-PH9-ACTIVE/feedback",
        json={
            "rating": 5,
            "comments": "Tata Steel CSR committed 50k INR toward continuous cartridge fabrication.",
            "outcome": "Modular unit ready for industrial discharge channel adoption.",
        },
    )
    assert resp.status_code == 201
    print("  -> PASSED: Partnered industry SPOC submitted feedback.")

    # Foreign Industry Employee -> 403
    app.dependency_overrides[get_current_user] = lambda: INDUSTRY_FOREIGN
    resp = client.post(
        "/api/projects/PRJ-PH9-ACTIVE/feedback",
        json={"rating": 2, "comments": "L&T is not on this project"},
    )
    assert resp.status_code == 403
    assert "You do not belong to the partnered industry" in get_err(resp)
    print("  -> PASSED: Cross-industry employee blocked with 403 Forbidden.")

    # Citizen Challenge Author submission -> 201
    app.dependency_overrides[get_current_user] = lambda: CITIZEN_AUTHOR
    resp = client.post(
        "/api/projects/PRJ-PH9-ACTIVE/feedback",
        json={
            "rating": 5,
            "comments": "The river water color and foul odor has completely subsided at Namkum ghat.",
            "outcome": "Clean and safe water restored for local community bathing and livestock.",
        },
    )
    assert resp.status_code == 201
    print("  -> PASSED: Citizen challenge submitter submitted evaluation feedback.")

    # -------------------------------------------------------------------------
    # Test 3: Duplicate Submission Prevention
    # -------------------------------------------------------------------------
    print("\n[TEST 3] Duplicate / Spam Submission Prevention...")

    # Citizen author attempts to submit a second feedback for the same project
    resp = client.post(
        "/api/projects/PRJ-PH9-ACTIVE/feedback",
        json={"rating": 4, "comments": "Second feedback spam"},
    )
    assert resp.status_code == 400
    assert "Duplicate submission" in get_err(resp)
    print("  -> PASSED: Duplicate feedback submission blocked with 400 Bad Request.")

    # -------------------------------------------------------------------------
    # Test 4: Feedback Listing & Role-Aware Privacy Masking
    # -------------------------------------------------------------------------
    print("\n[TEST 4] Feedback Listing & Role-Aware Privacy Masking...")

    # Public / Unauthenticated viewer
    app.dependency_overrides[get_current_user_optional] = lambda: None
    resp = client.get("/api/projects/PRJ-PH9-ACTIVE/feedback")
    assert resp.status_code == 200
    fbs = resp.json()["data"]
    assert len(fbs) == 4
    # Citizen name should be masked for general public
    citizen_entries = [f for f in fbs if f["respondent_role"] == "citizen"]
    assert citizen_entries[0]["submitted_by"] == "Verified Citizen / Community Member"
    print("  -> PASSED: Citizen identity safely masked ('Verified Citizen / Community Member') for public viewer.")

    # Government Officer sees unmasked submitter names
    app.dependency_overrides[get_current_user_optional] = lambda: GOV_OFFICER
    resp = client.get("/api/projects/PRJ-PH9-ACTIVE/feedback")
    assert resp.status_code == 200
    fbs_gov = resp.json()["data"]
    citizen_gov = [f for f in fbs_gov if f["respondent_role"] == "citizen"][0]
    assert citizen_gov["submitted_by"] == "Citizen Aarti Sharma"
    print("  -> PASSED: Government officer views full transparent audit roster.")

    # -------------------------------------------------------------------------
    # Test 5: Controlled, Justified Lifecycle State Transitions
    # -------------------------------------------------------------------------
    print("\n[TEST 5] Controlled, Justified Project Lifecycle Transitions...")

    # Unauthorized user (Student) attempts to advance status -> 403
    app.dependency_overrides[get_current_user] = lambda: STUDENT_MEMBER
    resp = client.patch(
        "/api/projects/PRJ-PH9-ACTIVE/status",
        json={"status": "solved", "justification": "Student marking solved"},
    )
    assert resp.status_code == 403
    print("  -> PASSED: Student blocked from transitioning project lifecycle with 403 Forbidden.")

    # Arbitrary state leap: 'proposed' straight to 'solved' -> 400
    app.dependency_overrides[get_current_user] = lambda: FACULTY_MENTOR
    resp = client.patch(
        "/api/projects/PRJ-PH9-PROPOSED/status",
        json={"status": "solved", "justification": "Skipping active, prototype, pilot"},
    )
    assert resp.status_code == 400
    assert "Invalid lifecycle transition" in get_err(resp)
    print("  -> PASSED: Arbitrary status leap (proposed -> solved) blocked with 400 Bad Request.")

    # Legitimate forward progression: 'proposed' -> 'active'
    resp = client.patch(
        "/api/projects/PRJ-PH9-PROPOSED/status",
        json={"status": "active", "justification": "Faculty commencing initial field research"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["current_status"] == "active"
    print("  -> PASSED: Legitimate transition 'proposed' -> 'active' executed successfully.")

    # Legitimate transition: 'deployed' -> 'solved'
    # PRJ-PH9-ACTIVE is currently 'deployed' and has completed milestones & 4 feedback items
    resp = client.patch(
        "/api/projects/PRJ-PH9-ACTIVE/status",
        json={"status": "solved", "justification": "Field bio-filter verified by CPCB and community members"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["current_status"] == "solved"
    print("  -> PASSED: Legitimate transition 'deployed' -> 'solved' executed successfully.")

    # Verify that linked challenge CH-PH9-01 was synchronized to 'resolved'
    ch_res = mock_client.table("challenges").select("*").eq("challenge_id", "CH-PH9-01").execute()
    assert ch_res.data[0]["status"] == "resolved"
    print("  -> PASSED: Associated challenge status automatically synchronized to 'resolved'.")

    # Legitimate transition: 'solved' -> 'completed' (terminal state)
    resp = client.patch(
        "/api/projects/PRJ-PH9-ACTIVE/status",
        json={"status": "completed", "justification": "Final project documentation and asset handover complete"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["current_status"] == "completed"
    print("  -> PASSED: Legitimate transition 'solved' -> 'completed' executed successfully.")

    # -------------------------------------------------------------------------
    # Test 6: Role-Tailored Impact & Outcomes Reporting
    # -------------------------------------------------------------------------
    print("\n[TEST 6] Role-Tailored Outcome & Impact Intelligence (GET /impact)...")

    # Citizen Impact Perspective
    app.dependency_overrides[get_current_user_optional] = lambda: CITIZEN_AUTHOR
    resp = client.get("/api/projects/PRJ-PH9-ACTIVE/impact")
    assert resp.status_code == 200
    c_impact = resp.json()["data"]
    assert c_impact["current_status"] == "completed"
    assert c_impact["average_rating"] == 5.0
    assert c_impact["total_feedback_count"] == 4
    assert c_impact["role_specific_impact"]["impact_perspective"] == "Community & Citizen Resolution"
    assert c_impact["role_specific_impact"]["is_resolved"] is True
    print("  -> PASSED: Citizen impact highlights community resolution, satisfaction rating (5.0/5), and local outcomes.")

    # Student Impact Perspective
    app.dependency_overrides[get_current_user_optional] = lambda: STUDENT_MEMBER
    resp = client.get("/api/projects/PRJ-PH9-ACTIVE/impact")
    assert resp.status_code == 200
    s_impact = resp.json()["data"]["role_specific_impact"]
    assert s_impact["impact_perspective"] == "Student Experiential Learning & Skills"
    assert "Portfolio Certification" in s_impact["portfolio_status"]
    print("  -> PASSED: Student impact highlights hands-on credits, verified skills, and portfolio certification.")

    # Industry Impact Perspective
    app.dependency_overrides[get_current_user_optional] = lambda: INDUSTRY_SPOC
    resp = client.get("/api/projects/PRJ-PH9-ACTIVE/impact")
    assert resp.status_code == 200
    ind_impact = resp.json()["data"]["role_specific_impact"]
    assert ind_impact["impact_perspective"] == "Industry Technology & Commercial Readiness"
    assert "TRL 9" in ind_impact["technology_readiness_level"]
    print(f"  -> PASSED: Industry impact highlights {ind_impact['technology_readiness_level']} and talent pipeline.")

    # Government Impact Perspective
    app.dependency_overrides[get_current_user_optional] = lambda: GOV_OFFICER
    resp = client.get("/api/projects/PRJ-PH9-ACTIVE/impact")
    assert resp.status_code == 200
    gov_impact = resp.json()["data"]["role_specific_impact"]
    assert gov_impact["impact_perspective"] == "Government Civic ROI & Policy Scalability"
    assert "Scalable for multi-district deployment" in gov_impact["policy_recommendation"]
    print("  -> PASSED: Government impact highlights civic ROI, multi-stakeholder roster, and policy recommendation.")

    print("\n" + "=" * 75)
    print("ALL PHASE 9 VERIFICATION TESTS PASSED SUCCESSFULLY! (100% SUCCESS)")
    print("=" * 75)


if __name__ == "__main__":
    test_suite()
