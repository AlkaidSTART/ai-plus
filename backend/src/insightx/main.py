"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from insightx import __version__
from insightx.api.router import api_router
from insightx.config import get_settings
from insightx.database import build_database
from insightx.errors import install_exception_handlers


def create_app() -> FastAPI:
    """Create and configure the InsightX API application."""
    app = FastAPI(title="InsightX API", version=__version__)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    settings = get_settings()
    engine, session_factory = build_database(settings)
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = session_factory

    install_exception_handlers(app)
    app.include_router(api_router, prefix="/api/v1")
    return app


app = create_app()
