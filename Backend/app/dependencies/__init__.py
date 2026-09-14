from app.dependencies.auth import (
    AuthenticatedUser,
    get_auth_service,
    get_current_user,
    get_current_user_optional,
    require_role,
    require_verified_privileged_user,
    require_industry_spoc,
    require_university_admin,
)

__all__ = [
    "AuthenticatedUser",
    "get_auth_service",
    "get_current_user",
    "get_current_user_optional",
    "require_role",
    "require_verified_privileged_user",
    "require_industry_spoc",
    "require_university_admin",
]
