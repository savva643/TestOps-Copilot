"""Application configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    """Application settings."""

    SERVICE_NAME: str = "gitlab-integration-service"
    DEBUG: bool = False

    # External service URLs
    CORE_AGENT_URL: str = "http://localhost:8001"
    SPEC_PARSER_URL: str = "http://localhost:8002"
    CODE_GENERATOR_URL: str = "http://localhost:8003"

    # GitLab defaults
    GITLAB_BASE_URL: str = "https://gitlab.com/api/v4"
    GITLAB_DEFAULT_BRANCH: str = "main"
    GITLAB_TESTS_PATH: str = "tests/generated/"
    GITLAB_COMMIT_PREFIX: str = "testops: "

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)


settings = Settings()




