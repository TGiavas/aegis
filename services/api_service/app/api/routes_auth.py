"""
Authentication routes: register and login.

These endpoints handle:
- User registration (create new account)
- User login (authenticate and get JWT token)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import create_access_token, hash_password, verify_password

# Import from models package (this ensures all models are loaded for relationships)
from app.models import User

from app.schemas.auth import (
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)

# =============================================================================
# ROUTER SETUP
# =============================================================================
# APIRouter groups related endpoints together.
# The prefix and tags help organize the API documentation.

router = APIRouter(
    prefix="/auth",  # All routes start with /auth
    tags=["Authentication"],  # Groups endpoints in Swagger docs
)


# =============================================================================
# REGISTER ENDPOINT
# =============================================================================


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Create a new user account with email and password.",
)
async def register(
    request: UserRegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Register a new user.
    
    Flow:
    1. Check if email already exists
    2. Hash the password
    3. Create user in database
    4. Return user info (without password)
    
    Args:
        request: Contains email and password
        db: Database session (injected by FastAPI)
        
    Returns:
        The created user
        
    Raises:
        409 Conflict: If email already registered
    """
    # Check if user with this email already exists
    query = select(User).where(User.email == request.email)
    result = await db.execute(query)
    existing_user = result.scalar_one_or_none()
    
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )
    
    # Create new user with hashed password
    user = User(
        email=request.email,
        password_hash=hash_password(request.password),
        role="USER",
    )
    
    # Add to database
    db.add(user)
    await db.commit()
    
    # Refresh to get generated fields (id, created_at)
    await db.refresh(user)
    
    return user


# =============================================================================
# LOGIN ENDPOINT
# =============================================================================


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login and get access token",
    description="Authenticate with email and password to receive a JWT token.",
)
async def login(
    request: UserLoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """
    Authenticate user and return JWT token.
    
    Flow:
    1. Find user by email
    2. Verify password against stored hash
    3. Create JWT token with user ID
    4. Return token
    
    Args:
        request: Contains email and password
        db: Database session
        
    Returns:
        JWT access token
        
    Raises:
        401 Unauthorized: If credentials are invalid
    """
    # Find user by email
    query = select(User).where(User.email == request.email)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    # Check if user exists and password is correct
    # We use the same error message for both cases (security best practice)
    # This prevents attackers from knowing if an email is registered
    if user is None or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create JWT token
    # We store user ID in the "sub" (subject) claim
    # Converting to string because JWT standard recommends string subjects
    access_token = create_access_token(data={"sub": str(user.id)})
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
    )

