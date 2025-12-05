"""
Configuration for analytics service.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+psycopg://aegis:aegis@localhost:5432/aegis"
    
    # RabbitMQ
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    events_queue: str = "events"
    
    # Alert thresholds
    error_rate_threshold: float = 0.1  # 10% error rate triggers alert
    high_latency_threshold_ms: int = 5000  # 5 seconds
    window_size_seconds: int = 300  # 5 minute window for rate calculations
    
    # Service settings
    debug: bool = False
    log_level: str = "INFO"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
    )


settings = Settings()

