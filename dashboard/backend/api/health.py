"""Health check API endpoint for the LLM Serve Dashboard.

Provides health status information including database connectivity and version.
This endpoint does not require authentication and is intended for monitoring
and load balancer health checks.
"""

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from dashboard.backend.config import get_settings
from dashboard.backend.db.session import get_db
from dashboard.backend.models.schemas import HealthResponse

# Initialize structured logger
logger = structlog.get_logger(__name__)

# Create router with health tag
router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check(
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> HealthResponse:
    """Check the health status of the API and its dependencies.

    This endpoint verifies:
    - API is running and responding
    - Database connectivity via a simple SELECT 1 query
    - Returns the current application version

    Returns 200 OK when healthy, 503 Service Unavailable when unhealthy.
    Does not require authentication.

    Args:
        response: FastAPI response object for setting status codes
        db: Database session dependency

    Returns:
        HealthResponse with status, database connectivity, and version

    Raises:
        No exceptions - catches all errors and returns unhealthy status
    """
    settings = get_settings()
    database_connected = False
    health_status = "unhealthy"

    try:
        # Test database connectivity with simple query
        result = await db.execute(text("SELECT 1"))
        result.scalar()
        database_connected = True
        health_status = "healthy"

        logger.info(
            "health_check_success",
            database_connected=database_connected,
            version=settings.app_version,
        )

    except Exception as e:
        # Log the failure but return a graceful response
        logger.error(
            "health_check_failed",
            error=str(e),
            error_type=type(e).__name__,
            database_connected=database_connected,
        )

        # Set HTTP 503 Service Unavailable status
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return HealthResponse(
        status=health_status,
        database_connected=database_connected,
        version=settings.app_version,
    )
