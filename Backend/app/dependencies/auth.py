from typing import List, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.services.auth_service import AuthService, AuthenticatedUser

security = HTTPBearer(auto_error=False)


def get_auth_service() -> AuthService:
    """Dependency providing AuthService instance."""
    return AuthService()


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    auth_service: AuthService = Depends(get_auth_service),
) -> Optional[AuthenticatedUser]:
    """Optional authentication dependency.

    Returns None if no Authorization Bearer header is present.
    If a Bearer token is provided, validates it against Supabase Auth.
    """
    if not credentials or not credentials.credentials:
        return None

    user_id, email = auth_service.validate_token(credentials.credentials)
    return auth_service.get_authenticated_user(user_id=user_id, email=email)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthenticatedUser:
    """Strict authentication dependency.

    1. Reads Bearer JWT from Authorization header.
    2. Validates JWT with Supabase Auth (cryptographically verified).
    3. Fetches user ID from verified token.
    4. Queries profiles table (profiles.role is authoritative; never frontend input).
    5. Resolves organizational/stakeholder link.
    6. Blocks inactive or rejected privileged accounts.
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id, email = auth_service.validate_token(credentials.credentials)
    user = auth_service.get_authenticated_user(user_id=user_id, email=email)

    # Rejection of inactive or rejected privileged accounts
    if user.verification_status in ("inactive", "rejected"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: User account is {user.verification_status}.",
        )

    return user


def require_role(allowed_roles: List[str]):
    """Role-based authorization dependency factory.

    Checks profiles.role (authoritative) against allowed_roles.
    Rejects unauthorized access with HTTP 403 Forbidden.
    """

    async def role_checker(user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden: Role '{user.role}' does not have permission for this resource.",
            )
        return user

    return role_checker


def require_verified_privileged_user(allowed_roles: Optional[List[str]] = None):
    """Requires that the user belongs to a privileged role AND has verified status."""

    async def verifier(user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
        if allowed_roles and user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden: Role '{user.role}' does not have permission for this resource.",
            )

        if not user.is_verified or user.verification_status != "verified":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden: Account verification status is '{user.verification_status}'. Verified status is required.",
            )
        return user

    return verifier


def require_industry_spoc():
    """Industry SPOC authorization dependency.

    Enforces that:
    1. profiles.role == 'industry_employee'
    2. Account is verified in industry_employees table
    3. approval_authority is TRUE (designation alone is NOT permission).
    """

    async def spoc_checker(user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
        if user.role != "industry_employee":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: Only industry representatives may access this resource.",
            )

        if not user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden: Industry employee is not verified (status: '{user.verification_status}').",
            )

        if not user.approval_authority:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: SPOC approval authority is required. Designation alone does not confer permission.",
            )
        return user

    return spoc_checker


def require_university_admin():
    """University Administration authorization dependency.

    Enforces that:
    1. profiles.role == 'university_admin'
    2. Account is verified in university_admins table
    """

    async def admin_checker(user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
        if user.role != "university_admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: Only University Administration may access this resource.",
            )

        if not user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden: University Admin account is not verified (status: '{user.verification_status}').",
            )
        return user

    return admin_checker


def require_government_officer():
    """Government Officer authorization dependency.

    Enforces that:
    1. profiles.role == 'government'
    2. Account is linked to a valid record in government_authorities table
    3. User account is verified
    """

    async def gov_checker(user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
        if user.role != "government":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: Only verified government officers may access government monitoring resources.",
            )

        if not user.stakeholder:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: User is not linked to a valid government authority record.",
            )

        if not user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden: Government officer account is not verified (status: '{user.verification_status}').",
            )
        return user

    return gov_checker

