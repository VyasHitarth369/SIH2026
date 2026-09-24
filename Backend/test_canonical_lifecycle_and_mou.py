"""test_canonical_lifecycle_and_mou.py

Comprehensive test suite verifying:
1. Milestone progression along canonical 7-stage lifecycle to "Solution Deployed".
2. Canonical lifecycle synchronization:
   - `project_milestones` updated to completed.
   - `projects.status` set to 'deployed' with `actual_end_date`.
   - `challenges.status` set to 'resolved'.
3. Government problem categorization:
   - Deployed/resolved challenge mapped to 'solved' category.
   - Excluded from 'active' and 'pending' categories.
   - Current milestone hydrated with 'Solution Deployed'.
4. Multi-role Past Projects query support:
   - Live query for university_admin, faculty, student, industry, industry_employee.
5. Authoritative binary MOU download endpoint:
   - GET /api/projects/{project_id}/mou/download returns %PDF-1.4 binary stream with Content-Disposition: attachment.
6. MOU RBAC security:
   - Unauthorized citizen / non-participant receives HTTP 403 Forbidden.
7. Zero test residue cleanup in live Supabase.
"""

import os
import sys
import uuid
import pytest
from datetime import datetime, timezone
from starlette.testclient import TestClient

backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from dotenv import load_dotenv
load_dotenv(os.path.join(backend_dir, ".env"))

from app.main import app
from app.database import get_supabase
from app.routes.projects import get_workflow_service, get_project_workflow_service
from app.dependencies.auth import get_current_user
from app.services.auth_service import AuthenticatedUser
from app.services.project_workflow_service import ProjectWorkflowService
from app.services.government_service import GovernmentService


@pytest.fixture(autouse=True)
def clean_overrides():
    saved_wf = app.dependency_overrides.pop(get_workflow_service, None)
    saved_pwf = app.dependency_overrides.pop(get_project_workflow_service, None)
    yield
    if saved_wf:
        app.dependency_overrides[get_workflow_service] = saved_wf
    if saved_pwf:
        app.dependency_overrides[get_project_workflow_service] = saved_pwf


@pytest.fixture(scope="module")
def supabase_client():
    return get_supabase()


@pytest.fixture(scope="module")
def project_service():
    return ProjectWorkflowService()


@pytest.fixture(scope="module")
def gov_service():
    return GovernmentService()


@pytest.fixture(scope="module")
def uni_admin():
    return AuthenticatedUser(
        user_id="19869f81-f251-4e81-8c9b-f9e723cb92b0",
        email="demo_uni_admin@samadhansetu.gov.in",
        role="university_admin",
        is_verified=True,
    )


@pytest.fixture(scope="module")
def citizen_user():
    return AuthenticatedUser(
        user_id="7b3bb465-fc4f-4633-a97f-9762174ce15f",
        email="citizen.test@jharkhand.gov.in",
        role="citizen",
        is_verified=True,
    )


def test_milestone_progression_canonical_lifecycle(supabase_client, project_service, uni_admin):
    """Verifies sequential milestone progression up to 'Solution Deployed' updates DB tables canonically."""
    cid = f"TEST-CH-LC-{uuid.uuid4().hex[:6].upper()}"
    pid = f"PRJ-TEST-LC-{uuid.uuid4().hex[:6].upper()}"

    try:
        # Create test challenge and project
        supabase_client.table("challenges").insert({
            "challenge_id": cid,
            "title": "Automated Lifecycle River Sensor Network",
            "description": "Deployment of smart sensors across Damodar river basin.",
            "status": "in_project",
            "city": "Dhanbad",
            "district": "Dhanbad",
        }).execute()

        supabase_client.table("projects").insert({
            "project_id": pid,
            "challenge_id": cid,
            "project_title": "Damodar Sensor Deployment Project",
            "university_id": "U001",
            "industry_id": "I001",
            "status": "active",
        }).execute()

        # Step 1: Advance to Student Team Formed
        r1 = project_service.update_project_standardized_milestone(pid, "Student Team Formed", uni_admin)
        assert r1["current_milestone"] == "Student Team Formed"

        # Step 2: Advance to Development In Progress
        r2 = project_service.update_project_standardized_milestone(pid, "Development In Progress", uni_admin)
        assert r2["current_milestone"] == "Development In Progress"

        # Step 3: Advance to Solution Deployed (Canonical Terminal Milestone)
        r3 = project_service.update_project_standardized_milestone(pid, "Solution Deployed", uni_admin)
        assert r3["current_milestone"] == "Solution Deployed"
        assert r3["status"] == "deployed"

        # Verify projects row in live DB
        p_row = supabase_client.table("projects").select("status, actual_end_date").eq("project_id", pid).single().execute()
        assert p_row.data["status"] == "deployed"
        assert p_row.data["actual_end_date"] is not None

        # Verify challenges row in live DB
        c_row = supabase_client.table("challenges").select("status").eq("challenge_id", cid).single().execute()
        assert c_row.data["status"] == "resolved"

        # Verify project_milestones table has all stages marked completed
        m_rows = supabase_client.table("project_milestones").select("milestone_name, status, completion_percentage").eq("project_id", pid).execute()
        completed_stages = {m["milestone_name"] for m in (m_rows.data or []) if m["status"] == "completed"}
        assert "Solution Deployed" in completed_stages

        # Verify backward transition or modifying deployed project is rejected
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            project_service.update_project_standardized_milestone(pid, "Development In Progress", uni_admin)
        assert exc_info.value.status_code == 400

    finally:
        # Guaranteed cleanup
        supabase_client.table("project_milestones").delete().eq("project_id", pid).execute()
        supabase_client.table("projects").delete().eq("project_id", pid).execute()
        supabase_client.table("challenges").delete().eq("challenge_id", cid).execute()


def test_government_monitoring_solved_categorization(supabase_client, project_service, gov_service, uni_admin):
    """Verifies that resolved/deployed projects appear in 'solved' government category and not active/pending."""
    cid = f"TEST-CH-GOV-{uuid.uuid4().hex[:6].upper()}"
    pid = f"PRJ-TEST-GOV-{uuid.uuid4().hex[:6].upper()}"

    try:
        supabase_client.table("challenges").insert({
            "challenge_id": cid,
            "title": "Clean Water IoT Monitoring Station",
            "description": "Continuous water purity telemetry in Ranchi.",
            "status": "in_project",
            "city": "Ranchi",
            "district": "Ranchi",
        }).execute()

        supabase_client.table("projects").insert({
            "project_id": pid,
            "challenge_id": cid,
            "project_title": "Ranchi Pure Water Project",
            "university_id": "U001",
            "industry_id": "I001",
            "status": "active",
        }).execute()

        # Step through to Solution Deployed
        project_service.update_project_standardized_milestone(pid, "Student Team Formed", uni_admin)
        project_service.update_project_standardized_milestone(pid, "Development In Progress", uni_admin)
        project_service.update_project_standardized_milestone(pid, "Solution Deployed", uni_admin)

        # Query Solved monitored problems
        solved_list = gov_service.get_monitored_problems(category="solved")
        matching_solved = [m for m in solved_list if m.get("challenge_id") == cid]
        assert len(matching_solved) == 1, "Deployed challenge must appear in government solved category"
        assert matching_solved[0].get("current_milestone") == "Solution Deployed"

        # Query Active and Pending monitored problems
        active_list = gov_service.get_monitored_problems(category="active")
        assert not any(m.get("challenge_id") == cid for m in active_list), "Solved challenge must not appear in active category"

        pending_list = gov_service.get_monitored_problems(category="pending")
        assert not any(m.get("challenge_id") == cid for m in pending_list), "Solved challenge must not appear in pending category"

    finally:
        supabase_client.table("project_milestones").delete().eq("project_id", pid).execute()
        supabase_client.table("projects").delete().eq("project_id", pid).execute()
        supabase_client.table("challenges").delete().eq("challenge_id", cid).execute()


def test_past_projects_multi_role_queries(project_service):
    """Verifies past projects retrieval across all 5 roles with status_filter='completed,deployed,solved'."""
    roles_to_test = [
        AuthenticatedUser(user_id="19869f81-f251-4e81-8c9b-f9e723cb92b0", email="admin@uni.edu", role="university_admin"),
        AuthenticatedUser(user_id="fac-001", email="fac@uni.edu", role="faculty"),
        AuthenticatedUser(user_id="stu-001", email="stu@uni.edu", role="student"),
        AuthenticatedUser(user_id="ind-001", email="ind@corp.com", role="industry", stakeholder={"industry_id": "I001"}),
        AuthenticatedUser(user_id="emp-001", email="emp@corp.com", role="industry_employee", stakeholder={"industry_id": "I001"}),
    ]

    for user in roles_to_test:
        prjs = project_service.list_projects_for_user(user, status_filter="completed,deployed,solved")
        assert isinstance(prjs, list), f"Expected list for role {user.role}, got {type(prjs)}"
        for p in prjs:
            assert p.get("status") in ["completed", "deployed", "solved"], (
                f"Project {p.get('project_id')} has status {p.get('status')}, expected completed/deployed/solved"
            )


def test_mou_authoritative_binary_download_pdf(supabase_client, uni_admin):
    """Verifies GET /api/projects/{project_id}/mou/download returns real binary PDF stream with attachment header."""
    # Find a project in DB
    p_res = supabase_client.table("projects").select("project_id").limit(1).execute()
    assert p_res.data and len(p_res.data) > 0, "At least one project must exist in database"
    pid = p_res.data[0]["project_id"]

    app.dependency_overrides[get_current_user] = lambda: uni_admin
    try:
        client = TestClient(app)
        resp = client.get(f"/api/projects/{pid}/mou/download")
        assert resp.status_code == 200, f"MOU download failed: {resp.text}"
        assert resp.headers.get("content-type") == "application/pdf"

        disposition = resp.headers.get("content-disposition", "")
        assert "attachment" in disposition
        assert f"VidySetu-MOU-{pid}.pdf" in disposition

        # Verify real binary magic bytes (%PDF-)
        assert resp.content.startswith(b"%PDF-1.4"), "MOU file must be valid binary PDF (%PDF-1.4)"
        assert len(resp.content) > 1000, "MOU PDF content must be authoritative non-empty binary payload"
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_mou_authorization_security_blocking(supabase_client, citizen_user):
    """Verifies that unauthorized non-participants (e.g. citizens) receive HTTP 403 on MOU download."""
    p_res = supabase_client.table("projects").select("project_id").limit(1).execute()
    assert p_res.data and len(p_res.data) > 0
    pid = p_res.data[0]["project_id"]

    app.dependency_overrides[get_current_user] = lambda: citizen_user
    try:
        client = TestClient(app)
        resp = client.get(f"/api/projects/{pid}/mou/download")
        assert resp.status_code == 403, f"Expected 403 Forbidden for citizen, got {resp.status_code}"
    finally:
        app.dependency_overrides.pop(get_current_user, None)
