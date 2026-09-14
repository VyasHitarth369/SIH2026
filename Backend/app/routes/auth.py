from fastapi import APIRouter, Depends
from app.dependencies.auth import get_current_user
from app.services.auth_service import AuthenticatedUser

router = APIRouter(prefix="/api/auth", tags=["Authentication & Identity"])


@router.get("/me")
def get_current_user_profile(user: AuthenticatedUser = Depends(get_current_user)):
    """Returns the authenticated user's ID, authoritative profile, role,

    and verified organizational stakeholder status.

    Never exposes secret keys or backend credentials.
    """
    return {
        "success": True,
        "data": {
            "user_id": user.user_id,
            "email": user.email,
            "role": user.role,
            "full_name": user.full_name,
            "profile": user.profile,
            "stakeholder": user.stakeholder,
            "verification_status": user.verification_status,
            "is_verified": user.is_verified,
            "is_spoc": user.is_spoc,
            "approval_authority": user.approval_authority,
        },
    }
