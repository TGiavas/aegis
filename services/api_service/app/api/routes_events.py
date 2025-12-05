"""
Event viewing routes.

Events are created by the ingestion_service. This API provides
read-only access for users to view their project's events.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.db import get_db
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

