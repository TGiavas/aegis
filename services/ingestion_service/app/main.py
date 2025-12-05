"""
Ingestion Service - receives events from external sources.

Authentication: API keys (Bearer token)
- External services send events with their API key
- We validate the key and associate events with the correct project
"""

import hashlib
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_db, ApiKey, Event
from app.rabbitmq import connect, disconnect, publish_event
from app.schemas import EventIngestRequest, EventIngestResponse


# =============================================================================
# LIFESPAN
# =============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown."""
    # Startup
    print("🚀 Starting Ingestion Service...")
    await connect()  # Connect to RabbitMQ
    
    yield
    
    # Shutdown
    await disconnect()
    print("👋 Ingestion Service stopped")


# =============================================================================
# APP
# =============================================================================


app = FastAPI(
    title="Aegis Ingestion Service",
    description="Event ingestion endpoint for external services",
    version="0.1.0",
    lifespan=lifespan,
)


# =============================================================================
# SECURITY
# =============================================================================

security = HTTPBearer()


def hash_api_key(key: str) -> str:
    """Hash an API key for comparison."""
    return hashlib.sha256(key.encode()).hexdigest()


async def get_project_id_from_api_key(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> int:
    """
    Validate API key and return the associated project ID.
    
    This is different from JWT auth in api_service:
    - API keys are used by external services to send events
    - We hash the provided key and compare with stored hash
    """
    api_key = credentials.credentials
    key_hash = hash_api_key(api_key)
    
    # Look up the API key by its hash
    query = select(ApiKey).where(ApiKey.key_hash == key_hash)
    result = await db.execute(query)
    api_key_record = result.scalar_one_or_none()
    
    if api_key_record is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not api_key_record.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return api_key_record.project_id


# =============================================================================
# ENDPOINTS
# =============================================================================


@app.get("/health", tags=["Health"])
@app.get("/api/v1/health", tags=["Health"], include_in_schema=False)
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "ingestion_service"}


@app.post(
    "/api/v1/events",
    response_model=EventIngestResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Events"],
    summary="Ingest an event",
)
async def ingest_event(
    request: EventIngestRequest,
    project_id: int = Depends(get_project_id_from_api_key),
    db: AsyncSession = Depends(get_db),
) -> EventIngestResponse:
    """
    Ingest an event from an external source.
    
    Authentication: Use your project's API key as Bearer token.
    
    Example:
    ```
    curl -X POST http://localhost:8001/api/v1/events \
      -H "Authorization: Bearer aegis_ab12cd34ef56..." \
      -H "Content-Type: application/json" \
      -d '{"source": "web-server-01", "event_type": "METRIC", "severity": "INFO"}'
    ```
    """
    # Create event in database
    event = Event(
        project_id=project_id,
        source=request.source,
        event_type=request.event_type.upper(),
        severity=request.severity.upper(),
        latency_ms=request.latency_ms,
        payload=request.payload,
    )
    
    db.add(event)
    await db.commit()
    await db.refresh(event)
    
    # Publish to RabbitMQ for analytics processing
    await publish_event({
        "id": event.id,
        "project_id": event.project_id,
        "source": event.source,
        "event_type": event.event_type,
        "severity": event.severity,
        "latency_ms": event.latency_ms,
        "payload": event.payload,
        "created_at": event.created_at.isoformat(),
    })
    
    return EventIngestResponse(
        id=event.id,
        project_id=event.project_id,
        source=event.source,
        event_type=event.event_type,
        severity=event.severity,
        latency_ms=event.latency_ms,
        created_at=event.created_at,
        message="Event ingested successfully",
    )

