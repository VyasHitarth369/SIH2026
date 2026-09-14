from app.routes.health import router as health_router
from app.routes.challenges import router as challenges_router
from app.routes.auth import router as auth_router
from app.routes.projects import router as projects_router
from app.routes.milestones import router as milestones_router
from app.routes.government import router as government_router

__all__ = [
    "health_router",
    "challenges_router",
    "auth_router",
    "projects_router",
    "milestones_router",
    "government_router",
]


