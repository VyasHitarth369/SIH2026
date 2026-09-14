"""Phase 2 Authentication and Authorization Test Suite.

Tests the 7 mandatory requirements without modifying production data:
1. Unauthenticated request
2. Authenticated citizen
3. Authenticated privileged role
4. Invalid token
5. Missing profile
6. Inactive/rejected privileged user
7. Role spoofing attempt & designation vs permission
"""

from fastapi import Depends
from starlette.testclient import TestClient
from app.main import app
from app.dependencies.auth import (
    get_auth_service,
    get_current_user,
    require_role,
    require_industry_spoc,
    require_university_admin,
    require_verified_privileged_user,
)
from app.services.auth_service import AuthService, AuthenticatedUser

# Create test endpoints to verify role gates
@app.get("/test-gates/citizen-only", tags=["Testing"])
def citizen_gate(user: AuthenticatedUser = Depends(require_role(["citizen"]))):
    return {"access": "granted", "role": user.role}

@app.get("/test-gates/gov-only", tags=["Testing"])
def gov_gate(user: AuthenticatedUser = Depends(require_role(["government"]))):
    return {"access": "granted", "role": user.role}

@app.get("/test-gates/uni-admin-verified", tags=["Testing"])
def uni_admin_gate(user: AuthenticatedUser = Depends(require_university_admin())):
    return {"access": "granted", "admin_id": user.stakeholder.get("admin_id")}

@app.get("/test-gates/industry-spoc-only", tags=["Testing"])
def industry_spoc_gate(user: AuthenticatedUser = Depends(require_industry_spoc())):
    return {"access": "granted", "is_spoc": user.is_spoc}


class MockAuthService(AuthService):
    """Mock AuthService that tests authorization logic against simulated profiles and records."""

    def __init__(self, mock_scenario: str):
        self.mock_scenario = mock_scenario

    def validate_token(self, token: str):
        if token == "invalid-token":
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token validation failed: invalid JWT signature",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return "test-user-id-12345", "test@samadhansetu.gov.in"

    def get_profile(self, user_id: str):
        if self.mock_scenario == "missing_profile":
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found. User account may not be initialized in profiles table.",
            )
        elif self.mock_scenario == "citizen" or self.mock_scenario == "spoof_attempt":
            return {"user_id": user_id, "role": "citizen", "full_name": "Ramesh Citizen"}
        elif self.mock_scenario == "university_admin":
            return {"user_id": user_id, "role": "university_admin", "full_name": "Dr. Registrar"}
        elif self.mock_scenario == "industry_spoc":
            return {"user_id": user_id, "role": "industry_employee", "full_name": "Vikram Industry SPOC"}
        elif self.mock_scenario == "industry_ordinary_with_high_designation":
            return {"user_id": user_id, "role": "industry_employee", "full_name": "Arun Manager"}
        elif self.mock_scenario == "inactive_privileged":
            return {"user_id": user_id, "role": "industry_employee", "full_name": "Ex-Employee"}
        elif self.mock_scenario == "government":
            return {"user_id": user_id, "role": "government", "full_name": "Collector Official"}
        return {"user_id": user_id, "role": "citizen", "full_name": "Default"}

    def resolve_stakeholder(self, user_id: str, role: str):
        if self.mock_scenario == "university_admin":
            return {"admin_id": "ADM-BIT-01", "university_id": "bit-mesra", "verification_status": "verified"}, "verified", True, False
        elif self.mock_scenario == "industry_spoc":
            return {"employee_id": "EMP-TATA-01", "industry_id": "tata-csr", "verification_status": "verified", "approval_authority": True}, "verified", True, True
        elif self.mock_scenario == "industry_ordinary_with_high_designation":
            # High designation like 'General Manager' but approval_authority is FALSE
            return {"employee_id": "EMP-TATA-02", "designation": "General Manager & SPOC", "verification_status": "verified", "approval_authority": False}, "verified", True, False
        elif self.mock_scenario == "inactive_privileged":
            return {"employee_id": "EMP-TATA-03", "verification_status": "inactive", "approval_authority": False}, "inactive", False, False
        elif self.mock_scenario == "government":
            return {"authority_id": "GOV-JH-01", "department": "Rural Development", "district": "Ranchi"}, "verified", True, False
        return None, "verified", True, False


def run_tests():
    print("=" * 70)
    print("STARTING PHASE 2 AUTHENTICATION & AUTHORIZATION TEST SUITE")
    print("=" * 70)

    client = TestClient(app)

    # -------------------------------------------------------------
    # TEST 1: Unauthenticated Request
    # -------------------------------------------------------------
    print("\n[TEST 1] Unauthenticated Request:")
    r1 = client.get("/api/auth/me")
    print("  Status Code:", r1.status_code)
    print("  Response:", r1.json())
    assert r1.status_code == 401
    assert r1.json()["success"] is False
    assert "token is required" in r1.json()["error"]["message"].lower() or "not provided" in r1.json()["error"]["message"].lower()
    print("  [PASS] Unauthenticated request correctly rejected with 401.")

    # -------------------------------------------------------------
    # TEST 2: Invalid Token
    # -------------------------------------------------------------
    print("\n[TEST 2] Invalid Token:")
    # First against live Supabase Auth API
    r2_live = client.get("/api/auth/me", headers={"Authorization": "Bearer invalid_malformed_token_999"})
    print("  Status Code (Live Supabase call):", r2_live.status_code)
    print("  Response:", r2_live.json())
    assert r2_live.status_code == 401
    assert r2_live.json()["success"] is False
    print("  [PASS] Live Supabase Auth rejected malformed token with 401.")

    # -------------------------------------------------------------
    # TEST 3: Authenticated Citizen
    # -------------------------------------------------------------
    print("\n[TEST 3] Authenticated Citizen:")
    app.dependency_overrides[get_auth_service] = lambda: MockAuthService("citizen")
    r3 = client.get("/api/auth/me", headers={"Authorization": "Bearer valid-mock-token"})
    print("  Status Code:", r3.status_code)
    print("  Response:", r3.json())
    assert r3.status_code == 200
    assert r3.json()["success"] is True
    assert r3.json()["data"]["role"] == "citizen"
    assert r3.json()["data"]["is_verified"] is True

    # Citizen trying citizen gate
    r3_gate = client.get("/test-gates/citizen-only", headers={"Authorization": "Bearer valid-mock-token"})
    assert r3_gate.status_code == 200
    print("  [PASS] Authenticated citizen can access /api/auth/me and citizen endpoints.")

    # -------------------------------------------------------------
    # TEST 4: Authenticated Privileged Roles
    # -------------------------------------------------------------
    print("\n[TEST 4] Authenticated Privileged Roles:")
    # 4a. University Admin
    app.dependency_overrides[get_auth_service] = lambda: MockAuthService("university_admin")
    r4_admin = client.get("/api/auth/me", headers={"Authorization": "Bearer valid-mock-token"})
    assert r4_admin.status_code == 200
    assert r4_admin.json()["data"]["role"] == "university_admin"
    assert r4_admin.json()["data"]["stakeholder"]["admin_id"] == "ADM-BIT-01"
    assert r4_admin.json()["data"]["is_verified"] is True

    r4_admin_gate = client.get("/test-gates/uni-admin-verified", headers={"Authorization": "Bearer valid-mock-token"})
    assert r4_admin_gate.status_code == 200
    print("  [PASS] 4a: Verified University Admin successfully authenticated and authorized.")

    # 4b. Industry SPOC
    app.dependency_overrides[get_auth_service] = lambda: MockAuthService("industry_spoc")
    r4_spoc = client.get("/api/auth/me", headers={"Authorization": "Bearer valid-mock-token"})
    assert r4_spoc.status_code == 200
    assert r4_spoc.json()["data"]["role"] == "industry_employee"
    assert r4_spoc.json()["data"]["is_spoc"] is True
    assert r4_spoc.json()["data"]["approval_authority"] is True

    r4_spoc_gate = client.get("/test-gates/industry-spoc-only", headers={"Authorization": "Bearer valid-mock-token"})
    assert r4_spoc_gate.status_code == 200
    print("  [PASS] 4b: Industry SPOC with approval_authority=True granted access to SPOC actions.")

    # -------------------------------------------------------------
    # TEST 5: Missing Profile
    # -------------------------------------------------------------
    print("\n[TEST 5] Missing Profile (User in Auth but no row in profiles):")
    app.dependency_overrides[get_auth_service] = lambda: MockAuthService("missing_profile")
    r5 = client.get("/api/auth/me", headers={"Authorization": "Bearer valid-mock-token"})
    print("  Status Code:", r5.status_code)
    print("  Response:", r5.json())
    assert r5.status_code == 404
    assert r5.json()["success"] is False
    assert "profile not found" in r5.json()["error"]["message"].lower()
    print("  [PASS] Missing profiles record rejected with 404.")

    # -------------------------------------------------------------
    # TEST 6: Inactive / Rejected Privileged User
    # -------------------------------------------------------------
    print("\n[TEST 6] Inactive / Rejected Privileged User:")
    app.dependency_overrides[get_auth_service] = lambda: MockAuthService("inactive_privileged")
    r6 = client.get("/api/auth/me", headers={"Authorization": "Bearer valid-mock-token"})
    print("  Status Code:", r6.status_code)
    print("  Response:", r6.json())
    assert r6.status_code == 403
    assert r6.json()["success"] is False
    assert "inactive" in r6.json()["error"]["message"].lower()
    print("  [PASS] Inactive privileged user rejected with 403 Forbidden.")

    # -------------------------------------------------------------
    # TEST 7: Role Spoofing Attempt & Designation vs Permission
    # -------------------------------------------------------------
    print("\n[TEST 7] Role Spoofing Attempt & Designation Checks:")
    # 7a. Citizen attempts to spoof government role via header and query param
    app.dependency_overrides[get_auth_service] = lambda: MockAuthService("citizen")
    r7_spoof = client.get(
        "/test-gates/gov-only?role=government",
        headers={
            "Authorization": "Bearer valid-mock-token",
            "X-Role": "government",
            "Role": "government",
        }
    )
    print("  Spoofing attempt response status:", r7_spoof.status_code)
    print("  Spoofing attempt response body:", r7_spoof.json())
    assert r7_spoof.status_code == 403
    assert "Role 'citizen' does not have permission" in r7_spoof.json()["error"]["message"]
    print("  [PASS] 7a: Frontend role spoofing thwarted; backend strictly enforced profiles.role.")

    # 7b. Designation alone is NOT permission:
    # Industry employee has designation='General Manager & SPOC', but approval_authority=False
    app.dependency_overrides[get_auth_service] = lambda: MockAuthService("industry_ordinary_with_high_designation")
    r7_desig = client.get("/test-gates/industry-spoc-only", headers={"Authorization": "Bearer valid-mock-token"})
    print("  Designation test status:", r7_desig.status_code)
    print("  Designation test body:", r7_desig.json())
    assert r7_desig.status_code == 403
    assert "SPOC approval authority is required" in r7_desig.json()["error"]["message"]
    print("  [PASS] 7b: High designation rejected without database approval_authority.")

    # Reset dependency overrides
    app.dependency_overrides.clear()
    print("\n" + "=" * 70)
    print("ALL 7 PHASE 2 AUTHENTICATION & AUTHORIZATION TESTS PASSED!")
    print("=" * 70)


if __name__ == "__main__":
    run_tests()
