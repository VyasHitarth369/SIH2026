from fastapi import APIRouter
from app.database import get_supabase

router = APIRouter(tags=["Health & Status"])


@router.get("/")
@router.get("/health")
@router.get("/api/health")
def root():
    return {
        "status": "healthy",
        "message": "Concordia backend is running",
        "service": "Concordia / Samadhan Setu API",
        "phase": "Phase 9 - Feedback, Outcome & Impact Tracking",
    }


@router.get("/api/test-supabase")
def test_supabase():
    """Preserved endpoint to verify connectivity to Supabase without writing data."""
    client = get_supabase()
    result = client.table("challenges").select("challenge_id, title").limit(5).execute()
    return {
        "success": True,
        "data": result.data or [],
    }
