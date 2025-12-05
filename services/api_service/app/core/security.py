"""
Security utilities for authentication.

This module provides:
1. Password hashing (bcrypt) - secure password storage
2. JWT token creation/verification - stateless authentication

Security principles:
- Never store plain text passwords
- Use industry-standard algorithms (bcrypt, HS256)
- Tokens expire after a configurable time
"""

from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings


# =============================================================================
# PASSWORD HASHING
# =============================================================================
# We use bcrypt directly (not passlib) for better compatibility.
# bcrypt is slow by design - this makes brute-force attacks impractical.
#
# How bcrypt works:
# 1. Generate a random "salt" (prevents rainbow table attacks)
# 2. Hash password + salt together
# 3. Store the result (includes the salt)


def hash_password(plain_password: str) -> str:
    """
    Hash a plain text password using bcrypt.
    
    Args:
        plain_password: The user's plain text password
        
    Returns:
        The bcrypt hash (store this in the database)
        
    Example:
        >>> hash_password("mypassword123")
        '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.SBnVMGSJQH3G5m'
    """
    # Convert string to bytes (bcrypt requires bytes)
    password_bytes = plain_password.encode("utf-8")
    
    # Generate salt and hash in one step
    # bcrypt.gensalt() creates a random salt with default cost factor of 12
    hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
    
    # Convert bytes back to string for storage
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain text password against a stored hash.
    
    Args:
        plain_password: The password the user just typed
        hashed_password: The hash stored in the database
        
    Returns:
        True if password matches, False otherwise
        
    Example:
        >>> stored_hash = hash_password("mypassword123")
        >>> verify_password("mypassword123", stored_hash)
        True
        >>> verify_password("wrongpassword", stored_hash)
        False
    """
    # Convert strings to bytes
    password_bytes = plain_password.encode("utf-8")
    hash_bytes = hashed_password.encode("utf-8")
    
    # bcrypt.checkpw compares password against hash
    # It extracts the salt from the hash automatically
    return bcrypt.checkpw(password_bytes, hash_bytes)


# =============================================================================
# JWT TOKEN HANDLING
# =============================================================================
# JWT (JSON Web Token) is a way to securely transmit information.
# Structure: header.payload.signature (base64 encoded, dot-separated)
#
# Flow:
# 1. User logs in with email/password
# 2. Server verifies credentials
# 3. Server creates JWT with user info and expiration
# 4. User includes JWT in future requests (Authorization header)
# 5. Server verifies JWT signature to authenticate


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Payload to encode in the token (typically {"sub": user_id})
        expires_delta: How long until token expires (default from settings)
        
    Returns:
        Encoded JWT string
        
    The token contains:
    - Your data (e.g., user ID)
    - Expiration time ("exp" claim)
    - Signed with our secret key (tamper-proof)
    """
    # Copy data so we don't modify the original
    to_encode = data.copy()
    
    # Set expiration time
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.access_token_expire_minutes
        )
    
    # Add expiration to payload
    # "exp" is a standard JWT claim that libraries check automatically
    to_encode.update({"exp": expire})
    
    # Create the token
    # jwt.encode(payload, secret_key, algorithm)
    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    
    return encoded_jwt


def verify_token(token: str) -> dict[str, Any] | None:
    """
    Verify and decode a JWT token.
    
    Args:
        token: The JWT string from the Authorization header
        
    Returns:
        The decoded payload if valid, None if invalid/expired
        
    This function:
    1. Checks the signature (was it signed with our secret?)
    2. Checks expiration (is it still valid?)
    3. Returns the payload if everything checks out
    """
    try:
        # Decode and verify the token
        # This raises JWTError if:
        # - Signature doesn't match (tampered)
        # - Token is expired
        # - Token is malformed
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except JWTError:
        # Token is invalid - don't reveal why (security best practice)
        return None


def get_token_subject(token: str) -> str | None:
    """
    Extract the subject (usually user ID) from a token.
    
    Args:
        token: The JWT string
        
    Returns:
        The "sub" claim value, or None if token is invalid
        
    Convention: We store the user ID in the "sub" (subject) claim.
    """
    payload = verify_token(token)
    if payload is None:
        return None
    
    # "sub" is a standard JWT claim for the subject (who the token is about)
    return payload.get("sub")

