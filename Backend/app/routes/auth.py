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


@router.get("/universities")
def list_universities():
    """Returns the authoritative list of universities from database for registration and profiles."""
    from app.database import get_supabase
    from fastapi import HTTPException, status
    try:
        sb = get_supabase()
        res = (
            sb.table("universities")
            .select("university_id, university_name, city, district")
            .order("university_id")
            .execute()
        )
        return {
            "success": True,
            "data": res.data or [],
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to load universities: {str(e)}",
        )


@router.get("/industries")
def list_industries():
    """Returns the authoritative list of industries from database for registration and profiles."""
    from app.database import get_supabase
    from fastapi import HTTPException, status
    try:
        sb = get_supabase()
        res = (
            sb.table("industries")
            .select("industry_id, industry_name, domain, city, district")
            .order("industry_id")
            .execute()
        )
        return {
            "success": True,
            "data": res.data or [],
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to load industries: {str(e)}",
        )
