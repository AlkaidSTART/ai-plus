"""SQLAlchemy engine, session, and ORM base configuration."""

from collections.abc import Iterator

from fastapi import Request
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from insightx.config import Settings


class Base(DeclarativeBase):
    """Declarative base for InsightX persistence models."""


SessionFactory = sessionmaker[Session]


def create_database_engine(database_url: str) -> Engine:
    """Create a lazily connected SQLAlchemy engine for PostgreSQL."""

    return create_engine(database_url, pool_pre_ping=True)


def create_session_factory(engine: Engine) -> SessionFactory:
    """Create application sessions without expiring loaded objects."""

    return sessionmaker(bind=engine, expire_on_commit=False)


def build_database(settings: Settings) -> tuple[Engine, SessionFactory]:
    """Build the engine and session factory for an application instance."""

    engine = create_database_engine(settings.database_url)
    return engine, create_session_factory(engine)


def get_session(request: Request) -> Iterator[Session]:
    """Yield one request-scoped database session."""

    factory: SessionFactory = request.app.state.session_factory
    with factory() as session:
        yield session
