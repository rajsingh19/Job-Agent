from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.router import api_router
from app.config.settings import get_settings
from app.database.session import close_db, init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure storage folders exist and initialize db schema
    settings = get_settings()
    settings.ensure_directories_exist()
    await init_db()
    yield
    # Shutdown: close DB connection pools
    await close_db()


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Production-oriented Human-in-the-Loop Job Application Agent Backend",
        debug=settings.debug,
        lifespan=lifespan,
    )

    # CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Production will configure specific frontend domain
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include V1 API routers
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    @app.get("/")
    async def root():
        return {
            "name": settings.app_name,
            "version": "0.1.0",
            "status": "online",
            "docs_url": "/docs",
        }

    return app


app = create_app()
