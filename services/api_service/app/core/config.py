"""
Application configuration loaded from environment variables.

Uses pydantic-settings to automatically read from environment
and provide type validation.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str = "postgresql+psycopg://aegis:aegis@localhost:5432/aegis"

    # JWT Authentication
    jwt_secret: str = "dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # Application
    debug: bool = False
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        # Load from .env file if present
        env_file=".env",
        # Environment variables are case-insensitive
        case_sensitive=False,
    )


# Create a singleton instance
settings = Settings()

