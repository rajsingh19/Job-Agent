from fastapi import APIRouter
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.resumes import router as resumes_router
from app.api.v1.endpoints.preferences import router as preferences_router
from app.api.v1.endpoints.profile import router as profile_router
from app.api.v1.endpoints.jobs import router as jobs_router
from app.api.v1.endpoints.connectors import router as connectors_router
from app.api.v1.endpoints.applications import router as applications_router
from app.api.v1.endpoints.browser import router as browser_router
from app.api.v1.endpoints.submission import router as submission_router
from app.api.v1.endpoints.portals import router as portals_router

api_router = APIRouter()
api_router.include_router(health_router, prefix="/system", tags=["System"])
api_router.include_router(resumes_router, prefix="/resumes", tags=["Resumes"])
api_router.include_router(preferences_router, prefix="/preferences", tags=["Preferences"])
api_router.include_router(profile_router, prefix="/profile", tags=["Candidate Profile"])
api_router.include_router(jobs_router, prefix="/jobs", tags=["Job Discovery"])
api_router.include_router(connectors_router, prefix="/connectors", tags=["Connectors"])
api_router.include_router(applications_router, prefix="/applications", tags=["Applications"])
api_router.include_router(submission_router, prefix="/applications", tags=["Application Submission"])
api_router.include_router(portals_router, prefix="", tags=["Portal Compatibility"])
api_router.include_router(browser_router, prefix="/browser", tags=["Browser Automation"])

