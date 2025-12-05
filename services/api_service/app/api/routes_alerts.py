"""
Alert viewing and management routes.

Alerts are created by the analytics_service. This API provides:
- Read access to view alerts
- Ability to resolve alerts
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models import Alert, Project, User
from app.schemas.alert import AlertListResponse, AlertResponse

router = APIRouter(
    prefix="/projects/{project_id}/alerts",
    tags=["Alerts"],
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
# LIST ALERTS
# =============================================================================


@router.get(
    "",
    response_model=AlertListResponse,
    summary="List alerts for a project",
)
async def list_alerts(
    project_id: int,
    # Pagination
    page: int = Query(default=1, ge=1),
    size: int = Query(default=50, ge=1, le=100),
    # Filters
    level: Optional[str] = Query(
        default=None,
        description="Filter by level (LOW, MEDIUM, HIGH, CRITICAL)",
    ),
    rule_name: Optional[str] = Query(
        default=None,
        description="Filter by rule name",
    ),
    resolved: Optional[bool] = Query(
        default=None,
        description="Filter by resolved status (true/false)",
    ),
    # Auth
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AlertListResponse:
    """
    List alerts for a project with optional filtering.
    
    Alerts are returned in reverse chronological order (newest first).
    """
    # Verify project ownership
    await get_user_project(project_id, current_user, db)
    
    # Build base query
    base_conditions = [Alert.project_id == project_id]
    
    # Apply filters
    if level:
        base_conditions.append(Alert.level == level.upper())
    if rule_name:
        base_conditions.append(Alert.rule_name == rule_name)
    if resolved is not None:
        if resolved:
            base_conditions.append(Alert.resolved_at.isnot(None))
        else:
            base_conditions.append(Alert.resolved_at.is_(None))
    
    # Get total count
    count_query = (
        select(func.count())
        .select_from(Alert)
        .where(*base_conditions)
    )
    count_result = await db.execute(count_query)
    total = count_result.scalar_one()
    
    # Get paginated alerts
    offset = (page - 1) * size
    query = (
        select(Alert)
        .where(*base_conditions)
        .order_by(Alert.created_at.desc())
        .offset(offset)
        .limit(size)
    )
    result = await db.execute(query)
    alerts = result.scalars().all()
    
    return AlertListResponse(
        items=alerts,
        total=total,
        page=page,
        size=size,
    )


# =============================================================================
# GET SINGLE ALERT
# =============================================================================


@router.get(
    "/{alert_id}",
    response_model=AlertResponse,
    summary="Get alert by ID",
)
async def get_alert(
    project_id: int,
    alert_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Alert:
    """Get a specific alert by ID."""
    # Verify project ownership
    await get_user_project(project_id, current_user, db)
    
    # Get the alert
    query = select(Alert).where(
        Alert.id == alert_id,
        Alert.project_id == project_id,
    )
    result = await db.execute(query)
    alert = result.scalar_one_or_none()
    
    if alert is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found",
        )
    
    return alert


# =============================================================================
# RESOLVE ALERT
# =============================================================================


@router.post(
    "/{alert_id}/resolve",
    response_model=AlertResponse,
    summary="Resolve an alert",
)
async def resolve_alert(
    project_id: int,
    alert_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Alert:
    """
    Mark an alert as resolved.
    
    Sets the `resolved_at` timestamp to the current time.
    """
    # Verify project ownership
    await get_user_project(project_id, current_user, db)
    
    # Get the alert
    query = select(Alert).where(
        Alert.id == alert_id,
        Alert.project_id == project_id,
    )
    result = await db.execute(query)
    alert = result.scalar_one_or_none()
    
    if alert is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found",
        )
    
    if alert.resolved_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Alert is already resolved",
        )
    
    # Resolve the alert
    alert.resolved_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(alert)
    
    return alert

