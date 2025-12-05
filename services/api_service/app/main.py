"""
FastAPI application entry point.

This is where:
- The FastAPI app is created
- Routes are registered
- Middleware is configured
- Startup/shutdown events are handled
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes_auth import router as auth_router
from app.api.routes_projects import router as projects_router
from app.api.routes_api_keys import router as api_keys_router
from app.api.routes_events import router as events_router
from app.api.routes_alerts import router as alerts_router


# =============================================================================
# LIFESPAN MANAGEMENT
# =============================================================================
# The lifespan context manager handles startup and shutdown events.
# This is the modern way (replaces @app.on_event decorators).


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handle application startup and shutdown.
    
    Startup: runs before the app starts accepting requests
    Shutdown: runs after the app stops accepting requests
    """
    # --- STARTUP ---
    print("🚀 Starting Aegis API Service...")
    
    # You could initialize connections here, e.g.:
    # - Database connection pool
    # - Redis client
    # - External service clients
    
    yield  # App runs while we're "inside" the yield
    
    # --- SHUTDOWN ---
    print("👋 Shutting down Aegis API Service...")
    
    # Clean up resources here, e.g.:
    # - Close database connections
    # - Flush caches


# =============================================================================
# CREATE APPLICATION
# =============================================================================


app = FastAPI(
    title="Aegis API",
    description="Real-Time Event Monitoring & Alerting Platform",
    version="0.1.0",
    lifespan=lifespan,
    # API docs URLs
    docs_url="/docs",       # Swagger UI
    redoc_url="/redoc",     # ReDoc alternative
    openapi_url="/openapi.json",
)


# =============================================================================
# REGISTER ROUTERS
# =============================================================================
# Each router handles a group of related endpoints.
# The prefix adds a path segment to all routes in that router.

app.include_router(
    auth_router,
    prefix="/api/v1",  # Full path: /api/v1/auth/register, etc.
)

app.include_router(
    projects_router,
    prefix="/api/v1",  # Full path: /api/v1/projects, etc.
)

app.include_router(
    api_keys_router,
    prefix="/api/v1",  # Full path: /api/v1/projects/{id}/api-keys, etc.
)

app.include_router(
    events_router,
    prefix="/api/v1",  # Full path: /api/v1/projects/{id}/events, etc.
)

app.include_router(
    alerts_router,
    prefix="/api/v1",  # Full path: /api/v1/projects/{id}/alerts, etc.
)


# =============================================================================
# HEALTH CHECK
# =============================================================================
# Simple endpoint to verify the service is running.
# Used by Docker healthchecks and load balancers.


@app.get(
    "/api/v1/health",
    tags=["Health"],
    summary="Health check",
)
async def health_check():
    """
    Check if the API service is running.
    
    Returns:
        Simple status object
    """
    return {
        "status": "healthy",
        "service": "api_service",
    }

