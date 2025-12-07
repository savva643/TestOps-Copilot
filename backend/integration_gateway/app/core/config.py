"""Application configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    """Application settings."""

    SERVICE_NAME: str = "integration-gateway"
    DEBUG: bool = False

    # External service URLs
    CORE_AGENT_URL: str = "http://localhost:8001"
    SPEC_PARSER_URL: str = "http://localhost:8002"
    CODE_GENERATOR_URL: str = "http://localhost:8003"
    TEST_OPTIMIZER_URL: str = "http://localhost:8004"

    # Security
    API_KEY: str = "default-api-key-change-in-production"

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)


settings = Settings()

