"""Configuration management using Pydantic Settings."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    database_url: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/cortex_orchestrator",
        description="PostgreSQL connection URL for orchestrator database",
    )

    # API Server
    api_host: str = Field(default="0.0.0.0", description="API server host (listen on all interfaces)")
    api_port: int = Field(default=8004, description="API server port (upstream nginx handles SSL)")
    api_reload: bool = Field(default=False, description="Enable auto-reload in development")
    
    # SSL/TLS Configuration (optional - use only if running without nginx)
    ssl_cert_file: str | None = Field(
        default=None,
        description="Path to SSL certificate file (not needed when using nginx)",
    )
    ssl_key_file: str | None = Field(
        default=None,
        description="Path to SSL private key file (not needed when using nginx)",
    )

    # Docker Swarm
    docker_host: str = Field(
        default="unix:///var/run/docker.sock",
        description="Docker daemon socket",
    )
    docker_network: str = Field(
        default="insurance-network",
        description="Docker network for all services",
    )

    # Instance Defaults (Phase 1 - all instances use same config)
    instance_image: str = Field(
        default="bre-payments:latest",
        description="Docker image for product instances",
    )
    instance_database_url: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/bre_payments",
        description="Database URL for product instances",
    )
    instance_platform_api_url: str = Field(
        default="https://api.platform.integrations.habit.io",
        description="Habit Platform API URL",
    )
    instance_platform_api_key: str = Field(
        default="",
        description="Habit Platform API key",
    )
    instance_mqtt_broker: str = Field(
        default="mqtt://localhost:1883",
        description="MQTT broker URL",
    )
    instance_redis_url: str = Field(
        default="redis://localhost:6379",
        description="Redis URL",
    )

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    
    # Build Configuration
    build_cache_dir: str = Field(
        default="./build-cache",
        description="Directory for storing temporary build files and caches",
    )
    
    # GitHub Integration
    github_token: str | None = Field(
        default=None,
        description="GitHub personal access token for private repo access",
    )


# Global settings instance
settings = Settings()
