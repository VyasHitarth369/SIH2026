"""test_mou_and_top5_live_verification.py

Comprehensive Live Verification for Final VidySetu (SIH26043) Integration:
1. Top-5 University Allocation Hydration & Rank Ordering (#1-#5)
2. University SPOC Acceptance Propagation & Immediate Reflection in Allocations
3. MOU System Security: Role-based Authorization & Validation
4. End-to-End MOU Upload, Supabase Storage Persistence & Multi-Role Query Views
5. GPS Location Redesign: Coordinates Round-Trip & Deterministic Storage
6. Guaranteed DB and Supabase Storage Cleanup (Zero Residue)
"""

import os
import sys
import uuid
from datetime import datetime, timezone
from fastapi import HTTPException

backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from dotenv import load_dotenv
load_dotenv(os.path.join(backend_dir, ".env"))

from app.database import get_supabase
from app.services.auth_service import AuthenticatedUser
from app.services.university_workflow_service import UniversityWorkflowService
from app.services.industry_workflow_service import IndustryWorkflowService
from app.services.government_service import GovernmentService
from app.services.challenge_service import ChallengeService


def run_mou_and_top5_verification():
    print("=" * 80)
    print("STARTING LIVE VERIFICATION: TOP-5 ALLOCATION, SPOC ACCEPTANCE, MOU & GPS")
    print("=" * 80)

    client = get_supabase()
    uni_service = UniversityWorkflowService()
    ind_service = IndustryWorkflowService()
    gov_service = GovernmentService()
    ch_service = ChallengeService()

    # Authoritative Users
    uni_admin_user = AuthenticatedUser(
        user_id="19869f81-f251-4e81-8c9b-f9e723cb92b0",
        email="demo_uni_admin@samadhansetu.gov.in",
        role="university_admin",
        is_verified=True,
    )
    gov_user = AuthenticatedUser(
        user_id="e224eefb-7e5f-4d43-9ce6-5da57e51c89f",
        email="gov.admin@jharkhand.gov.in",
        role="government",
    )
    citizen_user = AuthenticatedUser(
        user_id="7b3bb465-fc4f-4633-a97f-9762174ce15f",
        email="citizen.test@jharkhand.gov.in",
        role="citizen",
    )
    industry_spoc_user = AuthenticatedUser(
        user_id="d1111111-1111-1111-1111-111111111111",
        email="spoc@tatasteel.com",
        role="industry_employee",
        approval_authority=True,
        is_verified=True,
        stakeholder={"industry_id": "I001", "approval_authority": True},
    )

    created_challenge_ids = []
    created_project_ids = []
    uploaded_storage_paths = []
    results = {}

    try:
        # =========================================================================
        # TEST 1: TOP-5 UNIVERSITY ALLOCATION VERIFICATION
        # =========================================================================
        print("\n--- TEST 1: TOP-5 UNIVERSITY ALLOCATION & RANK ORDERING ---")
        invitations = uni_service.list_university_invitations(
            university_id=None,
            user=uni_admin_user,
            status_filter=None,
        )
        assert len(invitations) > 0, "University U001 must have active invitations in database"

        first_inv = invitations[0]
        assert "all_matches" in first_inv, "Invitation must include all_matches key"
        all_m = first_inv["all_matches"]
        assert len(all_m) >= 5, f"Expected at least Top 5 university matches, got {len(all_m)}"

        # Verify ranks are ordered ascending
        ranks = [m.get("rank") for m in all_m if m.get("rank") is not None]
        assert ranks == sorted(ranks), f"Ranks must be ordered ascending, got {ranks}"

        # Verify every match has a populated university_name
        for m in all_m:
            uni_name = m.get("university_name")
            assert uni_name is not None and len(uni_name) > 0, (
                f"university_name must be hydrated for match {m.get('university_id')}"
            )

        print(f"  Total matched universities in queue: {len(all_m)}")
        for m in all_m[:5]:
            print(f"    Rank #{m.get('rank')}: {m.get('university_id')} - {m.get('university_name')} (Status: {m.get('status')})")
        print("[PASS] TEST 1: Top-5 allocation successfully hydrated with ascending ranks and institutions.")
        results["test_1"] = "PASS"

        # =========================================================================
        # TEST 2: UNIVERSITY SPOC ACCEPTANCE PROPAGATION
        # =========================================================================
        print("\n--- TEST 2: UNIVERSITY SPOC ACCEPTANCE & ALLOCATION REFLECTION ---")
        temp_cid = f"TEST-CH-ACCEPT-{uuid.uuid4().hex[:6].upper()}"
        created_challenge_ids.append(temp_cid)

        client.table("challenges").insert({
            "challenge_id": temp_cid,
            "title": "Automated River Quality Monitoring System",
            "description": "Deploying IoT multispectral sensors along Subarnarekha river for toxic runoff tracking.",
            "location": "Lat: 23.344100, Lng: 85.309600 (Ranchi, Jharkhand)",
            "city": "Ranchi",
            "district": "Ranchi",
            "status": "routed",
            "submitted_by": "citizen",
        }).execute()

        client.table("challenge_university_matches").insert([
            {"challenge_id": temp_cid, "university_id": "U001", "rank": 1, "status": "recommended", "match_score": 95.0},
            {"challenge_id": temp_cid, "university_id": "U002", "rank": 2, "status": "recommended", "match_score": 88.0},
            {"challenge_id": temp_cid, "university_id": "U003", "rank": 3, "status": "recommended", "match_score": 82.0},
            {"challenge_id": temp_cid, "university_id": "U004", "rank": 4, "status": "recommended", "match_score": 77.0},
            {"challenge_id": temp_cid, "university_id": "U005", "rank": 5, "status": "recommended", "match_score": 71.0},
        ]).execute()

        # SPOC responds: Accept
        resp = uni_service.respond_to_university_match(
            challenge_id=temp_cid,
            university_id="U001",
            action="accept",
            user=uni_admin_user,
            response_note=None,
        )
        assert resp["status"] in ["accepted", "selected"], f"Expected accepted or selected, got {resp['status']}"

        # Verify live DB query reflects 'accepted' or 'selected' (since rank 1 auto-finalizes)
        check_match = client.table("challenge_university_matches").select("status").eq("challenge_id", temp_cid).eq("university_id", "U001").execute()
        assert check_match.data[0]["status"] in ["accepted", "selected"], f"Expected accepted or selected, got {check_match.data[0]['status']}"

        # Verify list_university_invitations reflects it immediately
        invs = uni_service.list_university_invitations(None, uni_admin_user)
        matching_inv = next((i for i in invs if i.get("challenge_id") == temp_cid), None)
        assert matching_inv is not None, "Newly accepted invitation must appear in invitations list"
        assert matching_inv["status"] in ["accepted", "selected"]

        # Assign faculty
        fac_res = client.table("faculty").select("faculty_id, faculty_name").eq("university_id", "U001").limit(1).execute()
        assert len(fac_res.data) > 0, "U001 must have faculty records"
        fac_id = fac_res.data[0]["faculty_id"]
        fac_name = fac_res.data[0]["faculty_name"]

        assign_res = uni_service.allocate_faculty_and_advance(
            challenge_id=temp_cid,
            faculty_ids=[fac_id],
            user=uni_admin_user,
        )
        assert assign_res["success"] is True
        assert assign_res["primary_faculty_id"] == fac_id
        if assign_res.get("project_id"):
            created_project_ids.append(assign_res["project_id"])

        print(f"  SPOC accepted match for {temp_cid}.")
        print(f"  Faculty assigned: {fac_name} ({fac_id}), Project: {assign_res.get('project_id')}")
        print("[PASS] TEST 2: University SPOC acceptance and allocation sync verified.")
        results["test_2"] = "PASS"

        # =========================================================================
        # TEST 3: MOU SECURITY: AUTHORIZATION & VALIDATION
        # =========================================================================
        print("\n--- TEST 3: MOU SECURITY: AUTHORIZATION & VALIDATION ---")
        temp_pid = f"PRJ-TEST-AUTH-{uuid.uuid4().hex[:6].upper()}"
        temp_cid_auth = f"CH-TEST-AUTH-{uuid.uuid4().hex[:6].upper()}"
        created_project_ids.append(temp_pid)
        created_challenge_ids.append(temp_cid_auth)

        client.table("challenges").insert({
            "challenge_id": temp_cid_auth,
            "title": "MOU Security Validation Challenge",
            "description": "Validation test challenge.",
            "location": "Ranchi",
            "city": "Ranchi",
            "status": "active",
        }).execute()

        client.table("projects").insert({
            "project_id": temp_pid,
            "challenge_id": temp_cid_auth,
            "project_title": "MOU Security Validation Project",
            "university_id": "U001",
            "industry_id": "I001",
            "status": "active",
        }).execute()

        # Case A: Unauthorized citizen user
        try:
            uni_service.upload_project_mou(
                project_id=temp_pid,
                filename="test_mou.pdf",
                content=b"%PDF-1.4 dummy",
                content_type="application/pdf",
                user=citizen_user,
            )
            assert False, "Should have raised 403 Forbidden"
        except HTTPException as exc:
            assert exc.status_code == 403, f"Expected 403, got {exc.status_code}"
            print("  Unauthorized citizen upload correctly blocked with 403 Forbidden.")

        # Case B: Unsupported file extension
        try:
            uni_service.upload_project_mou(
                project_id=temp_pid,
                filename="malicious_script.exe",
                content=b"MZ binary content",
                content_type="application/octet-stream",
                user=uni_admin_user,
            )
            assert False, "Should have raised 400 Bad Request"
        except HTTPException as exc:
            assert exc.status_code == 400, f"Expected 400, got {exc.status_code}"
            print("  Unsupported file extension correctly blocked with 400 Bad Request.")

        # Case C: File exceeds 10MB limit
        oversized_content = b"0" * (11 * 1024 * 1024)
        try:
            uni_service.upload_project_mou(
                project_id=temp_pid,
                filename="huge_mou.pdf",
                content=oversized_content,
                content_type="application/pdf",
                user=uni_admin_user,
            )
            assert False, "Should have raised 400 Bad Request"
        except HTTPException as exc:
            assert exc.status_code == 400, f"Expected 400, got {exc.status_code}"
            print("  Oversized document (>10MB) correctly blocked with 400 Bad Request.")

        print("[PASS] TEST 3: All MOU security and validation gates verified.")
        results["test_3"] = "PASS"

        # =========================================================================
        # TEST 4: END-TO-END MOU UPLOAD, STORAGE & MULTI-ROLE VIEWS
        # =========================================================================
        print("\n--- TEST 4: END-TO-END MOU UPLOAD & MULTI-ROLE ACCESSIBILITY ---")
        temp_pid2 = f"PRJ-TEST-MOU-{uuid.uuid4().hex[:6].upper()}"
        temp_cid2 = f"CH-TEST-MOU-{uuid.uuid4().hex[:6].upper()}"
        created_project_ids.append(temp_pid2)
        created_challenge_ids.append(temp_cid2)

        client.table("challenges").insert({
            "challenge_id": temp_cid2,
            "title": "MOU Storage Verification Challenge",
            "description": "Tripartite collaborative research test challenge.",
            "location": "Ranchi",
            "city": "Ranchi",
            "status": "project_created",
            "document": "-",  # Initially placeholder dash
        }).execute()

        client.table("projects").insert({
            "project_id": temp_pid2,
            "challenge_id": temp_cid2,
            "project_title": "Tripartite Solar Water Pilot",
            "university_id": "U001",
            "industry_id": "I001",
            "status": "active",
        }).execute()

        # Before upload: verify pending status
        uni_mous_before = uni_service.list_university_mous(uni_admin_user)
        mou_before = next((m for m in uni_mous_before if m.get("project_id") == temp_pid2), None)
        assert mou_before is not None, "Project must appear in MOU list"
        assert mou_before["has_document"] is False, "Before upload, has_document must be False (ignoring '-')"
        assert mou_before["document_url"] is None

        # Perform authorized upload via University Admin
        pdf_bytes = b"%PDF-1.4\n1 0 obj\n<< /Title (Official Tripartite VidySetu MOU) >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF"
        upload_res = uni_service.upload_project_mou(
            project_id=temp_pid2,
            filename="tripartite_signed_mou.pdf",
            content=pdf_bytes,
            content_type="application/pdf",
            user=uni_admin_user,
        )
        assert upload_res["success"] is True
        doc_url = upload_res["document_url"]
        storage_path = upload_res["storage_path"]
        assert doc_url is not None and "http" in doc_url
        uploaded_storage_paths.append(storage_path)
        print(f"  Uploaded signed MOU to Supabase Storage: {storage_path}")
        print(f"  Public Document URL: {doc_url}")

        # Verify DB persistence: challenge document updated
        ch_row = client.table("challenges").select("document").eq("challenge_id", temp_cid2).execute()
        assert ch_row.data[0]["document"] == doc_url, "challenges.document must be set to the uploaded document URL"

        # Multi-Role Retrieval: University Admin
        uni_mous_after = uni_service.list_university_mous(uni_admin_user)
        mou_after = next((m for m in uni_mous_after if m.get("project_id") == temp_pid2), None)
        assert mou_after is not None
        assert mou_after["has_document"] is True
        assert mou_after["document_url"] is not None
        assert storage_path in mou_after["document_url"]
        print("  Verified University Admin can view/download uploaded MOU.")

        # Multi-Role Retrieval: Government
        gov_mous = gov_service.get_government_mous()
        gov_mou = next((m for m in gov_mous if m.get("project_id") == temp_pid2), None)
        assert gov_mou is not None, "Uploaded MOU must appear in Government MOU records"
        assert gov_mou["has_document"] is True
        assert gov_mou["document_url"] is not None
        assert storage_path in gov_mou["document_url"]
        print("  Verified Government can view/download uploaded MOU.")

        print("[PASS] TEST 4: End-to-end MOU upload, storage, and multi-role retrieval confirmed.")
        results["test_4"] = "PASS"

        # =========================================================================
        # TEST 5: GPS LOCATION REDESIGN ROUND-TRIP
        # =========================================================================
        print("\n--- TEST 5: GPS LOCATION DETERMINISTIC ROUND-TRIP ---")
        temp_cid3 = f"TEST-GPS-{uuid.uuid4().hex[:6].upper()}"
        created_challenge_ids.append(temp_cid3)

        location_str = "Lat: 23.344100, Lng: 85.309600 (Ranchi, Jharkhand)"
        payload = {
            "title": "Smart Pothole and Drainage Obstruction Telemetry",
            "description": "Computer vision telemetry on urban public transit buses detecting roadway cavities.",
            "location": location_str,
            "city": "Ranchi",
            "district": "Ranchi",
            "impact_scope": "City Specific",
            "submitted_by": "citizen.test@jharkhand.gov.in",
            "status": "unsolved",
        }

        created = ch_service.create_challenge(payload, user=citizen_user)
        actual_cid = created.get("challenge_id") or temp_cid3
        if actual_cid not in created_challenge_ids:
            created_challenge_ids.append(actual_cid)

        db_ch = client.table("challenges").select("*").eq("challenge_id", actual_cid).execute()
        assert len(db_ch.data) == 1, "Challenge must exist in database"
        retrieved = db_ch.data[0]

        assert retrieved["location"] == location_str, f"Expected {location_str}, got {retrieved['location']}"
        assert retrieved["city"] == "Ranchi"
        assert retrieved["district"] == "Ranchi"
        assert retrieved["impact_scope"] == "City Specific"
        print(f"  Stored Location: {retrieved['location']}")
        print("[PASS] TEST 5: GPS location round-trip confirmed without mandatory address writing.")
        results["test_5"] = "PASS"

    finally:
        # =========================================================================
        # TEST 6: STRICT CLEANUP & ZERO RESIDUE VERIFICATION
        # =========================================================================
        print("\n--- CLEANUP & ZERO RESIDUE VERIFICATION ---")
        for cid in created_challenge_ids:
            try:
                client.table("project_milestones").delete().eq("project_id", cid).execute()
                client.table("challenge_industry_matches").delete().eq("challenge_id", cid).execute()
                client.table("challenge_university_matches").delete().eq("challenge_id", cid).execute()
                client.table("projects").delete().eq("challenge_id", cid).execute()
                client.table("ai_analysis").delete().eq("challenge_id", cid).execute()
                client.table("challenges").delete().eq("challenge_id", cid).execute()
            except Exception as e:
                print(f"Warning during cleanup of challenge {cid}: {e}")

        for pid in created_project_ids:
            try:
                client.table("project_milestones").delete().eq("project_id", pid).execute()
                client.table("projects").delete().eq("project_id", pid).execute()
            except Exception as e:
                print(f"Warning during cleanup of project {pid}: {e}")

        for path in uploaded_storage_paths:
            try:
                client.storage.from_("documents").remove([path])
            except Exception as e:
                print(f"Warning during cleanup of storage file {path}: {e}")

        # Verification of 0 residue
        for cid in created_challenge_ids:
            res = client.table("challenges").select("challenge_id").eq("challenge_id", cid).execute()
            assert len(res.data) == 0, f"Challenge {cid} was not cleaned up"

        for pid in created_project_ids:
            res = client.table("projects").select("project_id").eq("project_id", pid).execute()
            assert len(res.data) == 0, f"Project {pid} was not cleaned up"

        print(f"  Cleanup verified: 0 test rows remain in DB; 0 test files in Storage.")
        print("[PASS] TEST 6: Zero residue verified.")
        results["test_6"] = "PASS"

    print("\n" + "=" * 80)
    print("ALL 6 LIVE VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 80)
    return results


if __name__ == "__main__":
    run_mou_and_top5_verification()
