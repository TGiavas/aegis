"""
Alert rule management routes.

Provides CRUD operations for alert rules:
- Global rules: Apply to all projects (admin only)
- Project rules: Override global rules for a specific project
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_admin
from app.core.db import get_db
from app.models import AlertRule, Project, User
from app.schemas.alert_rule import (
    AlertRuleCreate,
    AlertRuleUpdate,
    AlertRuleResponse,
    AlertRuleListResponse,
)


# =============================================================================
# GLOBAL RULES ROUTER
# =============================================================================

global_router = APIRouter(
    prefix="/alert-rules",
    tags=["Alert Rules"],
)


# =============================================================================
# PROJECT RULES ROUTER  
# =============================================================================

project_router = APIRouter(
    prefix="/projects/{project_id}/alert-rules",
    tags=["Alert Rules"],
)


# =============================================================================
# HELPER FUNCTIONS
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


async def get_rule_by_id(
    rule_id: int,
    db: AsyncSession,
) -> AlertRule:
    """Get an alert rule by ID."""
    query = select(AlertRule).where(AlertRule.id == rule_id)
    result = await db.execute(query)
    rule = result.scalar_one_or_none()
    
    if rule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert rule not found",
        )
    
    return rule


# =============================================================================
# GLOBAL RULES ENDPOINTS
# =============================================================================


@global_router.get(
    "",
    response_model=AlertRuleListResponse,
    summary="List all global alert rules",
)
async def list_global_rules(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AlertRuleListResponse:
    """
    List all global alert rules (rules with no project_id).
    
    These rules apply to all projects unless overridden.
    """
    query = (
        select(AlertRule)
        .where(AlertRule.project_id.is_(None))
        .order_by(AlertRule.name)
    )
    result = await db.execute(query)
    rules = result.scalars().all()
    
    return AlertRuleListResponse(
        items=list(rules),
        total=len(rules),
    )


@global_router.post(
    "",
    response_model=AlertRuleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a global alert rule",
)
async def create_global_rule(
    rule_data: AlertRuleCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> AlertRule:
    """
    Create a new global alert rule (admin only).
    
    Global rules apply to all projects unless a project has an override
    with the same rule name.
    """
    # Check if global rule with same name exists
    existing = await db.execute(
        select(AlertRule).where(
            AlertRule.name == rule_data.name,
            AlertRule.project_id.is_(None),
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Global rule '{rule_data.name}' already exists",
        )
    
    rule = AlertRule(
        name=rule_data.name,
        project_id=None,
        field=rule_data.field,
        operator=rule_data.operator,
        value=rule_data.value,
        alert_level=rule_data.alert_level,
        message_template=rule_data.message_template,
        enabled=rule_data.enabled,
    )
    
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    
    return rule


@global_router.get(
    "/{rule_id}",
    response_model=AlertRuleResponse,
    summary="Get a global alert rule by ID",
)
async def get_global_rule(
    rule_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AlertRule:
    """Get a specific global alert rule."""
    rule = await get_rule_by_id(rule_id, db)
    
    if rule.project_id is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert rule not found (this is a project-specific rule)",
        )
    
    return rule


@global_router.put(
    "/{rule_id}",
    response_model=AlertRuleResponse,
    summary="Update a global alert rule",
)
async def update_global_rule(
    rule_id: int,
    rule_data: AlertRuleUpdate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> AlertRule:
    """
    Update a global alert rule (admin only).
    
    Only provided fields will be updated.
    """
    rule = await get_rule_by_id(rule_id, db)
    
    if rule.project_id is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert rule not found (this is a project-specific rule)",
        )
    
    # Update only provided fields
    update_data = rule_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(rule, field, value)
    
    await db.commit()
    await db.refresh(rule)
    
    return rule


@global_router.delete(
    "/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a global alert rule",
)
async def delete_global_rule(
    rule_id: int,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Delete a global alert rule (admin only).
    
    Warning: This will also affect all projects that relied on this global rule.
    """
    rule = await get_rule_by_id(rule_id, db)
    
    if rule.project_id is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert rule not found (this is a project-specific rule)",
        )
    
    await db.delete(rule)
    await db.commit()


# =============================================================================
# PROJECT RULES ENDPOINTS
# =============================================================================


@project_router.get(
    "",
    response_model=AlertRuleListResponse,
    summary="List effective alert rules for a project",
)
async def list_project_rules(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AlertRuleListResponse:
    """
    List effective alert rules for a project.
    
    Returns global rules + project-specific overrides.
    Project rules override global rules with the same name.
    """
    # Verify project ownership
    await get_user_project(project_id, current_user, db)
    
    # Get all global rules and project-specific rules
    query = (
        select(AlertRule)
        .where(
            or_(
                AlertRule.project_id.is_(None),
                AlertRule.project_id == project_id,
            )
        )
        .order_by(AlertRule.name)
    )
    result = await db.execute(query)
    all_rules = result.scalars().all()
    
    # Dedupe: project rules override global rules with same name
    rules_by_name: dict[str, AlertRule] = {}
    for rule in all_rules:
        if rule.name not in rules_by_name:
            rules_by_name[rule.name] = rule
        elif rule.project_id is not None:
            # Project rule overrides global rule
            rules_by_name[rule.name] = rule
    
    effective_rules = list(rules_by_name.values())
    
    return AlertRuleListResponse(
        items=effective_rules,
        total=len(effective_rules),
    )


@project_router.post(
    "",
    response_model=AlertRuleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a project-specific alert rule",
)
async def create_project_rule(
    project_id: int,
    rule_data: AlertRuleCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AlertRule:
    """
    Create a project-specific alert rule.
    
    If a global rule with the same name exists, this rule will override
    the global rule for this project only.
    """
    # Verify project ownership
    await get_user_project(project_id, current_user, db)
    
    # Check if project rule with same name exists
    existing = await db.execute(
        select(AlertRule).where(
            AlertRule.name == rule_data.name,
            AlertRule.project_id == project_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Project rule '{rule_data.name}' already exists for this project",
        )
    
    rule = AlertRule(
        name=rule_data.name,
        project_id=project_id,
        field=rule_data.field,
        operator=rule_data.operator,
        value=rule_data.value,
        alert_level=rule_data.alert_level,
        message_template=rule_data.message_template,
        enabled=rule_data.enabled,
    )
    
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    
    return rule


@project_router.get(
    "/{rule_id}",
    response_model=AlertRuleResponse,
    summary="Get a project-specific alert rule by ID",
)
async def get_project_rule(
    project_id: int,
    rule_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AlertRule:
    """Get a specific project alert rule."""
    # Verify project ownership
    await get_user_project(project_id, current_user, db)
    
    rule = await get_rule_by_id(rule_id, db)
    
    if rule.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert rule not found for this project",
        )
    
    return rule


@project_router.put(
    "/{rule_id}",
    response_model=AlertRuleResponse,
    summary="Update a project-specific alert rule",
)
async def update_project_rule(
    project_id: int,
    rule_id: int,
    rule_data: AlertRuleUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AlertRule:
    """
    Update a project-specific alert rule.
    
    Only provided fields will be updated.
    """
    # Verify project ownership
    await get_user_project(project_id, current_user, db)
    
    rule = await get_rule_by_id(rule_id, db)
    
    if rule.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert rule not found for this project",
        )
    
    # Update only provided fields
    update_data = rule_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(rule, field, value)
    
    await db.commit()
    await db.refresh(rule)
    
    return rule


@project_router.delete(
    "/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a project-specific alert rule",
)
async def delete_project_rule(
    project_id: int,
    rule_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Delete a project-specific alert rule.
    
    After deletion, the global rule (if any) will apply again.
    """
    # Verify project ownership
    await get_user_project(project_id, current_user, db)
    
    rule = await get_rule_by_id(rule_id, db)
    
    if rule.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert rule not found for this project",
        )
    
    await db.delete(rule)
    await db.commit()

