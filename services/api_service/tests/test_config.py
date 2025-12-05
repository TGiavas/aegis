"""
Tests for application configuration.

These tests verify that:
1. Default values are set correctly
2. Environment variables override defaults
"""

import os


class TestSettings:
    """Test the Settings configuration class."""

    def test_default_values(self, monkeypatch):
        """Settings should have sensible defaults when no env vars are set."""
        # Clear environment variables that would override defaults
        # monkeypatch.delenv removes the variable for this test only
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.delenv("JWT_SECRET", raising=False)
        monkeypatch.delenv("JWT_ALGORITHM", raising=False)
        monkeypatch.delenv("ACCESS_TOKEN_EXPIRE_MINUTES", raising=False)
        monkeypatch.delenv("DEBUG", raising=False)
        monkeypatch.delenv("LOG_LEVEL", raising=False)

        # Import inside test to get fresh instance
        from app.core.config import Settings

        # Create a new settings instance
        settings = Settings(
            _env_file=None,  # Don't read .env file
        )

        # Check defaults are what we expect
        assert settings.jwt_algorithm == "HS256"
        assert settings.access_token_expire_minutes == 60
        assert settings.debug is False
        assert settings.log_level == "INFO"

    def test_database_url_format(self):
        """Database URL should use the correct driver."""
        from app.core.config import Settings

        settings = Settings(_env_file=None)

        # Should use psycopg (not psycopg2)
        assert "psycopg" in settings.database_url
        # Should be PostgreSQL
        assert settings.database_url.startswith("postgresql")

    def test_env_override(self, monkeypatch):
        """Environment variables should override default values."""
        # monkeypatch is a pytest fixture that lets us safely modify env vars
        # Changes are automatically reverted after the test

        # Set an environment variable
        monkeypatch.setenv("JWT_SECRET", "my-test-secret")
        monkeypatch.setenv("DEBUG", "true")

        # Import and create settings AFTER setting env vars
        from app.core.config import Settings

        settings = Settings(_env_file=None)

        # Verify the override worked
        assert settings.jwt_secret == "my-test-secret"
        assert settings.debug is True

