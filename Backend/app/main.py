from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.routes.health import router as health_router
from app.routes.challenges import router as challenges_router
from app.routes.auth import router as auth_router
from app.routes.projects import router as projects_router
from app.routes.milestones import router as milestones_router
from app.routes.government import router as government_router



app = FastAPI(
    title="Concordia API",
    description="Digital platform crowdsourcing societal challenges and facilitating collaborative problem-solving through universities and industry partnerships (SIH26043).",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Phase 1 CORS: Explicit origins for the local frontend development environment.
# Avoids insecure wildcard origins while enabling Vite / Next.js local clients.
ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://samadhansetusih.vercel.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Centralized error handling
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": exc.detail,
            },
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    # Log internal error without exposing credentials or internal traces to client
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected server error occurred.",
            },
        },
    )


# Register modular routers
app.include_router(health_router)
app.include_router(challenges_router)
app.include_router(auth_router)
app.include_router(projects_router)
app.include_router(milestones_router)
app.include_router(government_router)