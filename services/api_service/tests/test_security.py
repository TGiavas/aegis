"""
Tests for the security module.

These tests verify:
1. Password hashing works correctly
2. JWT tokens are created and verified properly
3. Invalid/expired tokens are rejected
"""

import time
from datetime import timedelta

import pytest

from app.core.security import (
    create_access_token,
    get_token_subject,
    hash_password,
    verify_password,
    verify_token,
)


# =============================================================================
# PASSWORD HASHING TESTS
# =============================================================================


class TestPasswordHashing:
    """Test password hashing and verification."""

    def test_hash_password_returns_hash(self):
        """hash_password should return a bcrypt hash string."""
        password = "mysecretpassword"
        hashed = hash_password(password)
        
        # Bcrypt hashes start with $2b$ (version identifier)
        assert hashed.startswith("$2b$"), "Should be a bcrypt hash"
        
        # Hash should be different from original password
        assert hashed != password, "Hash should not equal plain password"

    def test_hash_password_different_each_time(self):
        """Same password should produce different hashes (due to salt)."""
        password = "mysecretpassword"
        
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        
        # Each hash includes a random salt, so they should differ
        assert hash1 != hash2, "Hashes should be different due to random salt"

    def test_verify_password_correct(self):
        """verify_password should return True for correct password."""
        password = "mysecretpassword"
        hashed = hash_password(password)
        
        result = verify_password(password, hashed)
        
        assert result is True, "Correct password should verify"

    def test_verify_password_incorrect(self):
        """verify_password should return False for wrong password."""
        password = "mysecretpassword"
        wrong_password = "wrongpassword"
        hashed = hash_password(password)
        
        result = verify_password(wrong_password, hashed)
        
        assert result is False, "Wrong password should not verify"

    def test_verify_password_empty_password(self):
        """verify_password should handle empty password."""
        password = "mysecretpassword"
        hashed = hash_password(password)
        
        result = verify_password("", hashed)
        
        assert result is False, "Empty password should not verify"


# =============================================================================
# JWT TOKEN TESTS
# =============================================================================


class TestJWTTokens:
    """Test JWT token creation and verification."""

    def test_create_access_token_returns_string(self):
        """create_access_token should return a JWT string."""
        token = create_access_token(data={"sub": "123"})
        
        # JWT has 3 parts separated by dots
        parts = token.split(".")
        assert len(parts) == 3, "JWT should have 3 parts (header.payload.signature)"

    def test_verify_token_valid(self):
        """verify_token should decode a valid token."""
        original_data = {"sub": "user123", "role": "admin"}
        token = create_access_token(data=original_data)
        
        payload = verify_token(token)
        
        assert payload is not None, "Valid token should decode"
        assert payload["sub"] == "user123", "Subject should match"
        assert payload["role"] == "admin", "Custom claims should be preserved"

    def test_verify_token_invalid_signature(self):
        """verify_token should reject tokens with invalid signature."""
        token = create_access_token(data={"sub": "123"})
        
        # Tamper with the token (change last character)
        tampered_token = token[:-1] + ("X" if token[-1] != "X" else "Y")
        
        payload = verify_token(tampered_token)
        
        assert payload is None, "Tampered token should be rejected"

    def test_verify_token_malformed(self):
        """verify_token should reject malformed tokens."""
        malformed_tokens = [
            "not.a.valid.jwt",
            "completely_invalid",
            "",
            "a.b",  # Only 2 parts
        ]
        
        for bad_token in malformed_tokens:
            payload = verify_token(bad_token)
            assert payload is None, f"Malformed token '{bad_token}' should be rejected"

    def test_token_contains_expiration(self):
        """Token payload should contain expiration claim."""
        token = create_access_token(data={"sub": "123"})
        payload = verify_token(token)
        
        assert "exp" in payload, "Token should have expiration claim"

    def test_token_custom_expiration(self):
        """Should be able to set custom expiration time."""
        # Create token that expires in 1 hour
        token = create_access_token(
            data={"sub": "123"},
            expires_delta=timedelta(hours=1),
        )
        
        payload = verify_token(token)
        
        assert payload is not None, "Token with custom expiration should be valid"

    def test_get_token_subject_valid(self):
        """get_token_subject should extract the subject claim."""
        user_id = "user_12345"
        token = create_access_token(data={"sub": user_id})
        
        subject = get_token_subject(token)
        
        assert subject == user_id, "Should extract correct subject"

    def test_get_token_subject_invalid_token(self):
        """get_token_subject should return None for invalid token."""
        subject = get_token_subject("invalid.token.here")
        
        assert subject is None, "Invalid token should return None"

    def test_get_token_subject_no_sub_claim(self):
        """get_token_subject should return None if no 'sub' claim."""
        # Create token without 'sub' claim
        token = create_access_token(data={"user_id": "123"})  # Wrong key
        
        subject = get_token_subject(token)
        
        assert subject is None, "Missing 'sub' claim should return None"


# =============================================================================
# INTEGRATION TESTS
# =============================================================================


class TestSecurityIntegration:
    """Integration tests combining multiple security functions."""

    def test_full_auth_flow(self):
        """Simulate a complete authentication flow."""
        # 1. User registers - password gets hashed
        plain_password = "user_secure_password_123"
        stored_hash = hash_password(plain_password)
        
        # 2. User logs in - password gets verified
        is_valid = verify_password(plain_password, stored_hash)
        assert is_valid is True
        
        # 3. Server creates JWT for the user
        user_id = "user_42"
        token = create_access_token(data={"sub": user_id})
        
        # 4. User makes authenticated request - token gets verified
        extracted_user_id = get_token_subject(token)
        assert extracted_user_id == user_id
        
    def test_wrong_password_flow(self):
        """User with wrong password should not get a token."""
        # Setup: hash the real password
        real_password = "correct_password"
        stored_hash = hash_password(real_password)
        
        # User tries wrong password
        attempted_password = "wrong_password"
        is_valid = verify_password(attempted_password, stored_hash)
        
        # Should fail - no token should be created
        assert is_valid is False, "Wrong password should not authenticate"

