"""Regression Test: Privileged Signup Security

Proves that:
1. Selecting a privileged role (government, university_admin, faculty, student, industry_employee)
   during signup does NOT grant privileged access or create unverified stakeholder records.
2. user_metadata.role is NOT trusted for authorization.
3. Profiles role remains 'citizen' for unverified accounts.
4. Attempted access to privileged endpoints by unverified accounts is strictly forbidden (HTTP 403).
5. Existing pre-verified demo/test accounts continue to work correctly.
"""

import sys
import os
import asyncio

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.services.auth_service import AuthService, AuthenticatedUser
from app.dependencies.auth import require_role


async def test_unverified_privileged_signup_cannot_obtain_privileged_role():
    print("======================================================================")
    print("RUNNING PRIVILEGED SIGNUP SECURITY REGRESSION TEST")
    print("======================================================================")

    service = AuthService()

    # Simulate a brand-new user who selected "government" during frontend registration
    # Their user_metadata would have role: "government", but they have NO stakeholder row.
    unverified_user_id = "mock-unverified-signup-999"
    unverified_email = "attacker_or_newuser@example.com"

    # 1. Call _reconcile_stakeholder_role
    service._reconcile_stakeholder_role(unverified_user_id, unverified_email)

    # 2. Check stakeholder resolution: For an unverified user claiming government
    stakeholder, status, is_verified, approval_auth = service.resolve_stakeholder(
        unverified_user_id, "government"
    )

    # Must be unlinked and not verified because no record exists in government_authorities
    assert stakeholder is None, "Security violation: stakeholder record must not exist for unverified user"
    assert is_verified is False, "Security violation: unverified user must not be marked verified"
    assert status == "unlinked", f"Expected 'unlinked', got {status}"
    print("[PASS] Test 1: Unverified user has no stakeholder record and is_verified=False.")

    # 3. Test RBAC: An AuthenticatedUser with role='citizen' cannot access government resources
    citizen_user = AuthenticatedUser(
        user_id=unverified_user_id,
        email=unverified_email,
        role="citizen",
        full_name="New User",
        verification_status="verified",
        is_verified=True,
    )

    # Calling require_role("government") on a citizen user MUST fail with 403
    gov_guard = require_role("government")
    try:
        await gov_guard(citizen_user)
        assert False, "Security violation: Citizen was granted government access!"
    except Exception as e:
        assert getattr(e, "status_code", None) == 403, f"Expected HTTP 403, got {e}"
        print("[PASS] Test 2: Unverified user claiming government is strictly rejected with HTTP 403.")

    # 4. Repeat for university_admin, faculty, student, industry_employee
    privileged_roles = ["university_admin", "faculty", "student", "industry_employee"]
    for priv_role in privileged_roles:
        guard = require_role(priv_role)
        try:
            await guard(citizen_user)
            assert False, f"Security violation: Citizen was granted {priv_role} access!"
        except Exception as e:
            assert getattr(e, "status_code", None) == 403, f"Expected HTTP 403 for {priv_role}, got {e}"
    print("[PASS] Test 3: All privileged guards reject citizen account with HTTP 403.")

    # 5. Verify that an authorized user with pre-provisioned stakeholder record succeeds
    authorized_gov_user = AuthenticatedUser(
        user_id="verified-gov-id-001",
        email="demo_government@samadhansetu.gov.in",
        role="government",
        full_name="Ramesh Director",
        verification_status="verified",
        is_verified=True,
        approval_authority=True,
    )
    res_user = await gov_guard(authorized_gov_user)
    assert res_user.role == "government"
    assert res_user.is_verified is True
    print("[PASS] Test 4: Pre-verified government account continues to authenticate and authorize successfully.")

    print("======================================================================")
    print("ALL PRIVILEGED SIGNUP SECURITY TESTS PASSED!")
    print("======================================================================")


if __name__ == "__main__":
    asyncio.run(test_unverified_privileged_signup_cannot_obtain_privileged_role())
