"""
Event viewing routes.

Events are created by the ingestion_service. This API provides
read-only access for users to view their project's events.

Includes SSE endpoint for real-time event streaming.
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import AsyncGenerator, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.db import get_db, AsyncSessionLocal
from app.core.security import get_token_subject
from app.models import Event, Project, User
from app.schemas.event import EventListResponse, EventResponse

router = APIRouter(
    prefix="/projects/{project_id}/events",
    tags=["Events"],
)


# =============================================================================
# VERIFY PROJECT OWNERSHIP
# =============================================================================


async def get_user_project(
    project_id: int,
    current_user: User,
    db: AsyncSession,
) -> Project:
    """Verify the user owns the project."""
    query = select(Project).where(
        Project.id == project_id,
        Project.owner_id == current_user.id,
    )
    result = await db.execute(query)
    project = result.scalar_one_or_none()
    
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    
    return project


async def verify_project_access_by_token(
    project_id: int,
    token: str,
) -> bool:
    """Verify user has access to project using token (for SSE)."""
    user_id = get_token_subject(token)
    if user_id is None:
        return False
    
    async with AsyncSessionLocal() as db:
        query = select(Project).where(
            Project.id == project_id,
            Project.owner_id == int(user_id),
        )
        result = await db.execute(query)
        project = result.scalar_one_or_none()
        return project is not None


# =============================================================================
# LIST EVENTS
# =============================================================================


@router.get(
    "",
    response_model=EventListResponse,
    summary="List events for a project",
)
async def list_events(
    project_id: int,
    # Pagination
    page: int = Query(default=1, ge=1),
    size: int = Query(default=50, ge=1, le=100),
    # Filters
    severity: Optional[str] = Query(
        default=None,
        description="Filter by severity (INFO, WARN, ERROR, CRITICAL)",
    ),
    event_type: Optional[str] = Query(
        default=None,
        description="Filter by type (METRIC, LOG, TRACE)",
    ),
    source: Optional[str] = Query(
        default=None,
        description="Filter by source (partial match)",
    ),
    created_after: Optional[datetime] = Query(
        default=None,
        description="Filter events created after this time",
    ),
    created_before: Optional[datetime] = Query(
        default=None,
        description="Filter events created before this time",
    ),
    # Auth
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EventListResponse:
    """
    List events for a project with optional filtering.
    
    Events are returned in reverse chronological order (newest first).
    """
    # Verify project ownership
    await get_user_project(project_id, current_user, db)
    
    # Build base query
    base_conditions = [Event.project_id == project_id]
    
    # Apply filters
    if severity:
        base_conditions.append(Event.severity == severity.upper())
    if event_type:
        base_conditions.append(Event.event_type == event_type.upper())
    if source:
        base_conditions.append(Event.source.ilike(f"%{source}%"))
    if created_after:
        base_conditions.append(Event.created_at >= created_after)
    if created_before:
        base_conditions.append(Event.created_at <= created_before)
    
    # Get total count
    count_query = (
        select(func.count())
        .select_from(Event)
        .where(*base_conditions)
    )
    count_result = await db.execute(count_query)
    total = count_result.scalar_one()
    
    # Get paginated events
    offset = (page - 1) * size
    query = (
        select(Event)
        .where(*base_conditions)
        .order_by(Event.created_at.desc())
        .offset(offset)
        .limit(size)
    )
    result = await db.execute(query)
    events = result.scalars().all()
    
    return EventListResponse(
        items=events,
        total=total,
        page=page,
        size=size,
    )


# =============================================================================
# SSE STREAMING ENDPOINT
# =============================================================================
# NOTE: This must come BEFORE /{event_id} route, otherwise FastAPI
# will interpret "stream" as an event_id parameter.


async def event_stream(
    project_id: int,
    last_event_id: Optional[int] = None,
) -> AsyncGenerator[str, None]:
    """
    Generate SSE events for new events in the project.
    
    Polls the database every second for new events.
    """
    current_last_id = last_event_id
    
    while True:
        try:
            async with AsyncSessionLocal() as db:
                # Build query for new events
                conditions = [Event.project_id == project_id]
                if current_last_id is not None:
                    conditions.append(Event.id > current_last_id)
                
                query = (
                    select(Event)
                    .where(*conditions)
                    .order_by(Event.id.asc())
                    .limit(50)  # Batch size
                )
                result = await db.execute(query)
                new_events = result.scalars().all()
                
                for event in new_events:
                    # Format as SSE
                    event_data = {
                        "id": event.id,
                        "project_id": event.project_id,
                        "source": event.source,
                        "event_type": event.event_type,
                        "severity": event.severity,
                        "latency_ms": event.latency_ms,
                        "payload": event.payload,
                        "created_at": event.created_at.isoformat() if event.created_at else None,
                    }
                    yield f"data: {json.dumps(event_data)}\n\n"
                    current_last_id = event.id
                
                # Send heartbeat to keep connection alive
                yield ": heartbeat\n\n"
            
            # Poll interval
            await asyncio.sleep(1)
            
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"SSE error: {e}")
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
            await asyncio.sleep(5)  # Wait before retry


@router.get(
    "/stream",
    summary="Stream events in real-time via SSE",
    response_class=StreamingResponse,
)
async def stream_events(
    project_id: int,
    token: str = Query(..., description="JWT token for authentication"),
    last_event_id: Optional[int] = Query(
        default=None,
        description="Only stream events after this ID",
    ),
):
    """
    Stream new events in real-time using Server-Sent Events (SSE).
    
    Authentication is done via query parameter since EventSource
    doesn't support custom headers.
    
    Usage (JavaScript):
    ```
    const eventSource = new EventSource(
      `/api/v1/projects/${projectId}/events/stream?token=${token}`
    );
    eventSource.onmessage = (e) => {
      const event = JSON.parse(e.data);
      console.log('New event:', event);
    };
    ```
    """
    # Verify token and project access
    has_access = await verify_project_access_by_token(project_id, token)
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token or no access to project",
        )
    
    return StreamingResponse(
        event_stream(project_id, last_event_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


# =============================================================================
# GET SINGLE EVENT
# =============================================================================


@router.get(
    "/{event_id}",
    response_model=EventResponse,
    summary="Get event by ID",
)
async def get_event(
    project_id: int,
    event_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Event:
    """Get a specific event by ID."""
    # Verify project ownership
    await get_user_project(project_id, current_user, db)
    
    # Get the event
    query = select(Event).where(
        Event.id == event_id,
        Event.project_id == project_id,
    )
    result = await db.execute(query)
    event = result.scalar_one_or_none()
    
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )
    
    return event
