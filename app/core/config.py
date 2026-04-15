from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    LOG_LEVEL: str = "INFO"

    OLLAMA_BASE_URL: str = "http://host.docker.internal:11434"
    EMBEDDING_MODEL: str = "nomic-embed-text"

    POSTGRES_URL: str = "postgresql+asyncpg://dialogue_bot:dialogue_bot@postgres:5432/dialogue_bot"

    DOCUMENT_SEARCHER_URL: str = "http://document_searcher:8091"
    FILE_VIEWER_URL: str = "http://file_viewer:8092"
    WEB_SEARCHER_URL: str = "http://web_searcher:8093"
    IMAGE_GENERATOR_URL: str = "http://image_generator:8094"
    FILE_CONVERTER_URL: str = "http://file_converter:8095"

    TOOL_REQUEST_TIMEOUT_SECONDS: float = 45.0
    HISTORY_SEARCH_LIMIT: int = 5

    MAX_RETRIES: int = 3
    INITIAL_BACKOFF: float = 0.5


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
