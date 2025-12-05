"""
API Key management routes.

API keys are used to authenticate event submissions from external services.
Keys are scoped to a project and can be revoked.

Security:
- Full key is returned ONLY at creation time
- We store only the hash (like passwords)
- List view shows only the prefix
"""

import hashlib
import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models import ApiKey, Project, User
from app.schemas.api_key import (
    ApiKeyCreateRequest,
    ApiKeyCreateResponse,
    ApiKeyListResponse,
    ApiKeyResponse,
)

router = APIRouter(
    prefix="/projects/{project_id}/api-keys",
    tags=["API Keys"],
)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def generate_api_key() -> str:
    """
    Generate a secure random API key.
    
    Format: aegis_<32 random hex characters>
    Example: aegis_ab12cd34ef56gh78ij90kl12mn34op56
    
    The prefix helps identify Aegis keys in logs/configs.
    """
    random_part = secrets.token_hex(16)  # 32 hex chars
    return f"aegis_{random_part}"


def hash_api_key(key: str) -> str:
    """
    Hash an API key for storage.
    
    We use SHA-256 which is fast and sufficient for API keys
    (unlike passwords, API keys have high entropy already).
    """
    return hashlib.sha256(key.encode()).hexdigest()


def get_key_prefix(key: str) -> str:
    """
    Extract the prefix from an API key for display.
    
    Example: aegis_ab12cd34... -> aegis_ab
    """
    return key[:8]  # "aegis_" + first 2 chars of random part


# =============================================================================
# VERIFY PROJECT OWNERSHIP
# =============================================================================


async def get_user_project(
    project_id: int,
    current_user: User,
    db: AsyncSession,
) -> Project:
    """
    Verify the user owns the project and return it.
    
    Raises 404 if project doesn't exist or user doesn't own it.
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
# CREATE API KEY
# =============================================================================


@router.post(
    "",
    response_model=ApiKeyCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new API key",
)
async def create_api_key(
    project_id: int,
    request: ApiKeyCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiKeyCreateResponse:
    """
    Create a new API key for a project.
    
    IMPORTANT: The full key is returned only once! Save it securely.
    
    The key can be used to authenticate event submissions:
    ```
    POST /api/v1/events
    Authorization: Bearer aegis_ab12cd34...
    ```
    """
    # Verify project ownership
    await get_user_project(project_id, current_user, db)
    
    # Generate the key
    full_key = generate_api_key()
    key_hash = hash_api_key(full_key)
    key_prefix = get_key_prefix(full_key)
    
    # Create database record
    api_key = ApiKey(
        project_id=project_id,
        key_hash=key_hash,
        key_prefix=key_prefix,
        name=request.name,
    )
    
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)
    
    # Return with full key (only time it's shown!)
    return ApiKeyCreateResponse(
        id=api_key.id,
        project_id=api_key.project_id,
        name=api_key.name,
        key=full_key,  # Full key - save this!
        key_prefix=key_prefix,
        created_at=api_key.created_at,
    )


# =============================================================================
# LIST API KEYS
# =============================================================================


@router.get(
    "",
    response_model=ApiKeyListResponse,
    summary="List API keys for a project",
)
async def list_api_keys(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiKeyListResponse:
    """
    List all API keys for a project.
    
    Note: Only the key prefix is shown, not the full key.
    """
    # Verify project ownership
    await get_user_project(project_id, current_user, db)
    
    # Get all keys for the project
    query = (
        select(ApiKey)
        .where(ApiKey.project_id == project_id)
        .order_by(ApiKey.created_at.desc())
    )
    result = await db.execute(query)
    api_keys = result.scalars().all()
    
    # Get count
    count_query = (
        select(func.count())
        .select_from(ApiKey)
        .where(ApiKey.project_id == project_id)
    )
    count_result = await db.execute(count_query)
    total = count_result.scalar_one()
    
    return ApiKeyListResponse(
        items=api_keys,
        total=total,
    )


# =============================================================================
# REVOKE API KEY
# =============================================================================


@router.delete(
    "/{key_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke an API key",
)
async def revoke_api_key(
    project_id: int,
    key_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Revoke an API key.
    
    This is a soft-delete: the key remains in the database but is marked
    as revoked and can no longer be used for authentication.
    """
    # Verify project ownership
    await get_user_project(project_id, current_user, db)
    
    # Find the API key
    query = select(ApiKey).where(
        ApiKey.id == key_id,
        ApiKey.project_id == project_id,
    )
    result = await db.execute(query)
    api_key = result.scalar_one_or_none()
    
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )
    
    if api_key.revoked_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="API key is already revoked",
        )
    
    # Soft delete - set revoked timestamp
    from datetime import datetime, timezone
    api_key.revoked_at = datetime.now(timezone.utc)
    
    await db.commit()

