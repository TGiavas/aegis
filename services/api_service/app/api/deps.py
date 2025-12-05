"""
FastAPI dependencies for route handlers.

Dependencies are reusable pieces of logic that can be injected into routes.
The most common use case is authentication — checking the JWT token and
returning the current user.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import get_token_subject
from app.models import User


# =============================================================================
# HTTP BEARER SCHEME
# =============================================================================
# This tells FastAPI to expect an "Authorization: Bearer <token>" header.
# It also adds the lock icon in Swagger UI for protected endpoints.

security = HTTPBearer()


# =============================================================================
# GET CURRENT USER
# =============================================================================


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Extract and validate JWT token, return the authenticated user.
    
    This is used as a dependency in protected routes:
    
        @router.get("/protected")
        async def protected_route(user: User = Depends(get_current_user)):
            return {"message": f"Hello {user.email}"}
    
    Flow:
    1. Extract token from Authorization header
    2. Decode and validate JWT
    3. Get user ID from token subject
    4. Fetch user from database
    5. Return user or raise 401
    
    Raises:
        401 Unauthorized: If token is invalid or user not found
    """
    # Extract the token string
    token = credentials.credentials
    
    # Get user ID from token
    user_id = get_token_subject(token)
    
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Fetch user from database
    query = select(User).where(User.id == int(user_id))
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


# =============================================================================
# ROLE-BASED ACCESS
# =============================================================================


async def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Dependency that requires the current user to be an admin.
    
    Usage:
        @router.delete("/users/{user_id}")
        async def delete_user(user: User = Depends(require_admin)):
            # Only admins can reach here
            ...
    
    Raises:
        403 Forbidden: If user is not an admin
    """
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user

