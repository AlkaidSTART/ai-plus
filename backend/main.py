"""InsightX FastAPI application entrypoint."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.errors import register_exception_handlers
from api.router import api_router
from core.config import get_settings
from core.redis import close_redis
from db.session import dispose_engine, get_engine
from runtime.bootstrap import build_runtime

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    engine = get_engine()
    from db.init_db import init_db

    await init_db(engine)
    yield
    await dispose_engine()
    await close_redis()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="InsightX API",
        description="AI market insight and decision system for cross-border e-commerce",
        version=settings.APP_VERSION,
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # The /api/v1 prefix is applied exactly once, here.
    app.include_router(api_router, prefix="/api/v1")
    register_exception_handlers(app)
    app.state.runtime = build_runtime(settings)
    return app


app = create_app()
