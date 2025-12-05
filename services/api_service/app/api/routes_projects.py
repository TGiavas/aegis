"""
Project management routes.

All routes require authentication (JWT token).
Users can only see and manage their own projects.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models import Project, User
from app.schemas.project import (
    ProjectCreateRequest,
    ProjectListResponse,
    ProjectResponse,
    ProjectUpdateRequest,
)

router = APIRouter(
    prefix="/projects",
    tags=["Projects"],
)


# =============================================================================
# CREATE PROJECT
# =============================================================================


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new project",
)
async def create_project(
    request: ProjectCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Project:
    """
    Create a new project for the authenticated user.
    
    - Project names must be unique
    - The authenticated user becomes the owner
    """
    # Check if project name already exists
    query = select(Project).where(Project.name == request.name)
    result = await db.execute(query)
    existing = result.scalar_one_or_none()
    
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Project with name '{request.name}' already exists",
        )
    
    # Create new project
    project = Project(
        name=request.name,
        description=request.description,
        owner_id=current_user.id,
    )
    
    db.add(project)
    await db.commit()
    await db.refresh(project)
    
    return project


# =============================================================================
# LIST PROJECTS
# =============================================================================


@router.get(
    "",
    response_model=ProjectListResponse,
    summary="List user's projects",
)
async def list_projects(
    page: int = Query(default=1, ge=1, description="Page number"),
    size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectListResponse:
    """
    List all projects owned by the authenticated user.
    
    Supports pagination with `page` and `size` parameters.
    """
    # Calculate offset
    offset = (page - 1) * size
    
    # Get total count
    count_query = (
        select(func.count())
        .select_from(Project)
        .where(Project.owner_id == current_user.id)
    )
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()
    
    # Get paginated projects
    query = (
        select(Project)
        .where(Project.owner_id == current_user.id)
        .order_by(Project.created_at.desc())
        .offset(offset)
        .limit(size)
    )
    result = await db.execute(query)
    projects = result.scalars().all()
    
    return ProjectListResponse(
        items=projects,
        total=total,
        page=page,
        size=size,
    )


# =============================================================================
# GET PROJECT
# =============================================================================


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Get project by ID",
)
async def get_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Project:
    """
    Get a specific project by ID.
    
    Users can only access their own projects.
    """
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
# UPDATE PROJECT
# =============================================================================


@router.patch(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Update project",
)
async def update_project(
    project_id: int,
    request: ProjectUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Project:
    """
    Update a project's name or description.
    
    - Only the owner can update
    - Only provided fields are updated (partial update)
    """
    # Fetch existing project
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
    
    # Check name uniqueness if changing name
    if request.name is not None and request.name != project.name:
        name_query = select(Project).where(Project.name == request.name)
        name_result = await db.execute(name_query)
        if name_result.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Project with name '{request.name}' already exists",
            )
        project.name = request.name
    
    # Update description if provided
    if request.description is not None:
        project.description = request.description
    
    await db.commit()
    await db.refresh(project)
    
    return project


# =============================================================================
# DELETE PROJECT
# =============================================================================


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete project",
)
async def delete_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Delete a project.
    
    - Only the owner can delete
    - This also deletes all associated api_keys, events, and alerts (cascade)
    """
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
    
    await db.delete(project)
    await db.commit()

