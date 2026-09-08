from fastapi import APIRouter
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.resumes import router as resumes_router
from app.api.v1.endpoints.preferences import router as preferences_router
from app.api.v1.endpoints.profile import router as profile_router
from app.api.v1.endpoints.jobs import router as jobs_router

api_router = APIRouter()
api_router.include_router(health_router, prefix="/system", tags=["System"])
api_router.include_router(resumes_router, prefix="/resumes", tags=["Resumes"])
api_router.include_router(preferences_router, prefix="/preferences", tags=["Preferences"])
api_router.include_router(profile_router, prefix="/profile", tags=["Candidate Profile"])
api_router.include_router(jobs_router, prefix="/jobs", tags=["Job Discovery"])
