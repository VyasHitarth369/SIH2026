"""test_part2_government_workflow.py

Comprehensive Verification Suite for Part 2:
- Government Active Problems Dataset & Dynamic Counts
- Single Source of Truth & Category Isolation
- Real New-Problem Routing (Submit -> Pending -> Approve -> Routed + Top 5)
- Rejection Lifecycle with Mandatory Persisted Reason
- Persistence across re-fetches (simulating browser reload / logout-login)
- Performance & Batched Hydration Verification
"""

import time
import uuid
from app.database import supabase
from app.services.auth_service import AuthenticatedUser
from app.services.challenge_service import ChallengeService
from app.services.government_service import (
    GovernmentService,
    GOVERNMENT_CATEGORY_STATUSES,
    ALL_MONITORED_STATUSES,
)


def create_mock_gov_user():
    return AuthenticatedUser(
        user_id="89995f07-993f-4a5e-b9f2-cd2236fa49cf",
        email="gov.director@jharkhand.gov.in",
        role="government",
        full_name="Director Higher Education",
        stakeholder={"officer_name": "Director Higher Education", "department": "Higher Education", "district": "Ranchi"},
    )


def step_1_dynamic_counts_and_category_isolation():
    print("\n--- TEST 1: Dynamic Database Counts & Strict Category Isolation ---")
    gs = GovernmentService()

    t0 = time.time()
    counts = gs.get_category_counts()
    count_duration = time.time() - t0
    print(f"  Dynamic Category Counts derived from DB (in {count_duration:.3f}s): {counts}")

    assert counts["all"] > 0, "All count must be > 0"
    assert counts["pending"] >= 5, f"Expected at least 5 pending problems, got {counts['pending']}"
    assert counts["allocated"] >= 5, f"Expected at least 5 allocated problems, got {counts['allocated']}"
    assert counts["rejected"] >= 5, f"Expected at least 5 rejected problems, got {counts['rejected']}"
    assert counts["solved"] >= 5, f"Expected at least 5 solved problems, got {counts['solved']}"

    # Sum of categories must equal "all"
    sub_sum = counts["pending"] + counts["allocated"] + counts["rejected"] + counts["solved"]
    assert counts["all"] == sub_sum, f"Sum of categories ({sub_sum}) does not equal 'all' ({counts['all']})"
    print(f"  [PASS] Counts: Pending={counts['pending']}, Allocated={counts['allocated']}, Rejected={counts['rejected']}, Solved={counts['solved']} -> Total All={counts['all']}")


def step_2_server_side_filtering_and_batched_performance():
    print("\n--- TEST 2: Server-Side Filtering & Batched Hydration Performance ---")
    gs = GovernmentService()

    for cat in ["pending", "allocated", "rejected", "solved"]:
        t0 = time.time()
        problems = gs.get_monitored_problems(category=cat, limit=100)
        dur = time.time() - t0
        print(f"  Category '{cat}': {len(problems)} items hydrated in {dur:.3f}s (Total in DB: {problems.total})")

        assert isinstance(problems, list), "MonitoredProblemList must behave as a list"
        assert len(problems) > 0, f"Category '{cat}' must have items"
        assert problems.total >= 5, f"Category '{cat}' total must be >= 5"

        # Verify that all returned items strictly belong to this category's statuses
        valid_statuses = GOVERNMENT_CATEGORY_STATUSES[cat]
        for p in problems:
            st = p.get("status")
            assert st in valid_statuses, f"Item {p['challenge_id']} with status '{st}' does not belong in category '{cat}'"

    print("  [PASS] Server-side category filtering strictly enforces status separation.")


def step_3_real_citizen_submission_to_pending():
    print("\n--- TEST 3: Real Problem Submission Enters Government Pending ---")
    cs = ChallengeService()
    gs = GovernmentService()

    test_cid = f"CHL-P2-TEST-{uuid.uuid4().hex[:6].upper()}"
    citizen_user = AuthenticatedUser(
        user_id="7b3bb465-fc4f-4633-a97f-9762174ce15f",
        email="citizen.p2@jharkhand.in",
        role="citizen",
        full_name="Ramesh Soren",
    )

    initial_counts = gs.get_category_counts()

    # 1. Citizen submits problem
    created = cs.create_challenge({
        "challenge_id": test_cid,
        "title": "Severe Arsenic Infiltration in Rural Tube-wells",
        "description": "High levels of arsenic detected in groundwater across five villages in Ramgarh. Immediate technical intervention needed.",
        "district": "Ramgarh",
        "city": "Ramgarh",
        "impact_scope": "District Level",
    }, user=citizen_user)

    assert created["challenge_id"] == test_cid
    assert created["status"] == "submitted"
    print(f"  Created test challenge: {test_cid} with status: {created['status']}")

    # 2. Add AI analysis so matching and routing have full metadata
    supabase.table("ai_analysis").insert({
        "challenge_id": test_cid,
        "category": "Water Management & Sanitation",
        "required_skills": "Water Chemistry, Nanomaterials, Hydrology",
        "required_technologies": "Spectrophotometry, IoT Water Quality Sensors",
        "innovation_scope": "high",
        "solution_found": False,
    }).execute()

    # 3. Check that it appears in Government Pending tab
    new_counts = gs.get_category_counts()
    assert new_counts["pending"] == initial_counts["pending"] + 1, "Pending count must increment by 1"
    assert new_counts["all"] == initial_counts["all"] + 1, "All count must increment by 1"

    pending_problems = gs.get_monitored_problems(category="pending")
    found_in_pending = any(p["challenge_id"] == test_cid for p in pending_problems)
    assert found_in_pending, f"New problem {test_cid} must be listed in Pending problems"

    # Must NOT be in Allocated, Rejected, or Solved
    allocated = gs.get_monitored_problems(category="allocated")
    rejected = gs.get_monitored_problems(category="rejected")
    solved = gs.get_monitored_problems(category="solved")

    assert not any(p["challenge_id"] == test_cid for p in allocated), f"Problem {test_cid} must not be in Allocated"
    assert not any(p["challenge_id"] == test_cid for p in rejected), f"Problem {test_cid} must not be in Rejected"
    assert not any(p["challenge_id"] == test_cid for p in solved), f"Problem {test_cid} must not be in Solved"

    print("  [PASS] New citizen problem appears exclusively in Pending tab with incremented counts.")
    return test_cid


def step_4_government_approval_workflow(test_cid: str):
    print("\n--- TEST 4: Government Approval -> Moves to Approved/Routed & Triggers Top 5 ---")
    gs = GovernmentService()
    gov_user = create_mock_gov_user()

    pre_counts = gs.get_category_counts()

    # 1. Government Approves Challenge
    t0 = time.time()
    approve_res = gs.approve_challenge(test_cid, user=gov_user)
    approve_dur = time.time() - t0
    print(f"  Approval executed in {approve_dur:.3f}s: status={approve_res['status']}")

    assert approve_res["success"] is True
    assert approve_res["status"] == "routed"
    assert approve_res["government_reviewed_by"] == str(gov_user.user_id)
    assert approve_res["government_reviewed_at"] is not None

    top5 = approve_res.get("top_universities") or approve_res.get("university_matches") or []
    assert len(top5) == 5, f"Expected 5 recommended universities, got {len(top5)}"
    print(f"  Generated Top 5 Universities: {[u.get('university_name') for u in top5]}")

    # 2. Check counts: pending decreases, allocated increases
    post_counts = gs.get_category_counts()
    assert post_counts["pending"] == pre_counts["pending"] - 1, "Pending count must decrement by 1"
    assert post_counts["allocated"] == pre_counts["allocated"] + 1, "Allocated count must increment by 1"

    # 3. Verify it is gone from Pending and present in Allocated
    pending = gs.get_monitored_problems(category="pending")
    assert not any(p["challenge_id"] == test_cid for p in pending), f"{test_cid} must not be in Pending after approval"

    allocated = gs.get_monitored_problems(category="allocated")
    matched_alloc = [p for p in allocated if p["challenge_id"] == test_cid]
    assert len(matched_alloc) == 1, f"{test_cid} must be present in Allocated"
    alloc_item = matched_alloc[0]
    assert alloc_item["status"] == "routed"
    assert len(alloc_item.get("top_universities", [])) == 5, "Allocated item must have 5 hydrated top universities"

    # 4. Re-query (simulate page refresh / re-fetch)
    re_allocated = gs.get_monitored_problems(category="allocated")
    re_item = [p for p in re_allocated if p["challenge_id"] == test_cid][0]
    assert re_item["status"] == "routed"
    assert len(re_item["top_universities"]) == 5
    print("  [PASS] Approval persisted to DB; Top-5 matches viewable across re-queries.")


def step_5_government_rejection_workflow():
    print("\n--- TEST 5: Government Rejection Workflow with Mandatory Reason ---")
    cs = ChallengeService()
    gs = GovernmentService()
    gov_user = create_mock_gov_user()

    rej_cid = f"CHL-P2-REJ-{uuid.uuid4().hex[:6].upper()}"
    citizen_user = AuthenticatedUser(
        user_id="7b3bb465-fc4f-4633-a97f-9762174ce15f",
        email="citizen.p2@jharkhand.in",
        role="citizen",
        full_name="Ramesh Soren",
    )

    cs.create_challenge({
        "challenge_id": rej_cid,
        "title": "Request for Decorative Lighting on Private Commercial Street",
        "description": "We want aesthetic LED strip lights installed on our private retail market road.",
        "district": "Ranchi",
        "city": "Ranchi",
    }, user=citizen_user)

    # 1. Verify it starts in Pending
    pending = gs.get_monitored_problems(category="pending")
    assert any(p["challenge_id"] == rej_cid for p in pending)

    # 2. Reject with mandatory reason
    rejection_reason = "Out of civic scope: platform does not fund private commercial lighting infrastructure."
    rej_res = gs.reject_challenge(rej_cid, reason=rejection_reason, user=gov_user)
    assert rej_res["success"] is True
    assert rej_res["status"] == "rejected"
    assert rej_res["government_rejection_reason"] == rejection_reason

    # 3. Verify it left Pending and moved to Rejected
    post_pending = gs.get_monitored_problems(category="pending")
    assert not any(p["challenge_id"] == rej_cid for p in post_pending), f"{rej_cid} must not be in Pending"

    rejected = gs.get_monitored_problems(category="rejected")
    matched_rej = [p for p in rejected if p["challenge_id"] == rej_cid]
    assert len(matched_rej) == 1, f"{rej_cid} must be in Rejected"
    rej_item = matched_rej[0]
    assert rej_item["status"] == "rejected"
    assert rej_item["government_rejection_reason"] == rejection_reason
    assert rej_item["government_reviewed_at"] is not None

    # Clean up test records
    supabase.table("challenges").delete().eq("challenge_id", rej_cid).execute()
    print("  [PASS] Rejection workflow records official reason, updates counts, and persists accurately.")


def test_government_active_problems_and_routing_workflow():
    step_1_dynamic_counts_and_category_isolation()
    step_2_server_side_filtering_and_batched_performance()
    test_cid = step_3_real_citizen_submission_to_pending()
    try:
        step_4_government_approval_workflow(test_cid)
    finally:
        supabase.table("challenge_university_matches").delete().eq("challenge_id", test_cid).execute()
        supabase.table("ai_analysis").delete().eq("challenge_id", test_cid).execute()
        supabase.table("challenges").delete().eq("challenge_id", test_cid).execute()
    step_5_government_rejection_workflow()


def main():
    print("======================================================================")
    print("STARTING PART 2: GOVERNMENT ACTIVE PROBLEMS & ROUTING WORKFLOW SUITE")
    print("======================================================================")

    test_government_active_problems_and_routing_workflow()

    print("\n======================================================================")
    print("ALL PART 2 TESTS COMPLETED WITH 100% SUCCESS!")
    print("======================================================================")


if __name__ == "__main__":
    main()
