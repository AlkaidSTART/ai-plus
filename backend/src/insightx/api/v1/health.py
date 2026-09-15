"""Health check endpoint."""

from fastapi import APIRouter

from insightx import __version__

router = APIRouter()


@router.get("/health")
def health() -> dict[str, object]:
    """Report application and dependency status without fabricating probes."""
    db_available = False
    redis_available = False
    status = "ok" if db_available and redis_available else "degraded"
    return {
        "code": 0,
        "message": "ok",
        "data": {
            "status": status,
            "version": __version__,
            "db": db_available,
            "redis": redis_available,
        },
    }
