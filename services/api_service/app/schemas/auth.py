"""
Pydantic schemas for authentication endpoints.

Schemas define the structure of:
- Request bodies (what clients send)
- Response bodies (what we send back)

Pydantic automatically:
- Validates data types
- Returns 422 errors for invalid data
- Generates OpenAPI documentation
"""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


# =============================================================================
# REQUEST SCHEMAS
# =============================================================================


class UserRegisterRequest(BaseModel):
    """
    Request body for POST /auth/register
    
    Example:
        {
            "email": "user@example.com",
            "password": "securepassword123"
        }
    """
    
    # EmailStr validates that the string is a valid email format
    email: EmailStr = Field(
        ...,  # ... means required
        description="User's email address",
        examples=["user@example.com"],
    )
    
    # Password with minimum length validation
    password: str = Field(
        ...,
        min_length=8,
        description="Password (minimum 8 characters)",
        examples=["securepassword123"],
    )


class UserLoginRequest(BaseModel):
    """
    Request body for POST /auth/login
    
    Example:
        {
            "email": "user@example.com",
            "password": "securepassword123"
        }
    """
    
    email: EmailStr = Field(
        ...,
        description="User's email address",
        examples=["user@example.com"],
    )
    
    password: str = Field(
        ...,
        description="User's password",
        examples=["securepassword123"],
    )


# =============================================================================
# RESPONSE SCHEMAS
# =============================================================================


class UserResponse(BaseModel):
    """
    User information returned after registration or when querying user.
    
    Note: We NEVER return the password_hash!
    
    Example:
        {
            "id": 1,
            "email": "user@example.com",
            "role": "USER",
            "created_at": "2025-01-01T12:00:00Z"
        }
    """
    
    id: int
    email: str
    role: str
    created_at: datetime
    
    # This tells Pydantic to read attributes from ORM objects
    # Without this, it only works with dicts
    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    """
    Response body for POST /auth/login
    
    Follows OAuth2 convention for token responses.
    
    Example:
        {
            "access_token": "eyJhbGciOiJIUzI1NiIs...",
            "token_type": "bearer"
        }
    """
    
    access_token: str = Field(
        ...,
        description="JWT access token",
    )
    
    token_type: str = Field(
        default="bearer",
        description="Token type (always 'bearer')",
    )

