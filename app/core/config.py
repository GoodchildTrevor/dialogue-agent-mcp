from pydantic_settings import BaseSettings, SettingsConfigDict

_settings_cache = None

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    LOG_LEVEL: str = "INFO"

    MCP_AUTH_TOKEN: str  # Required - no default, fails fast with a clear error

    DOCUMENT_SEARCHER_URL: str = "http://document_searcher:8091"
    DOCUMENT_SEARCHER_API_KEY: str = ""
    DOCUMENT_SEARCHER_DEFAULT_COLLECTION: str = "documents"
    FILE_VIEWER_URL: str = "http://file_viewer:8092"
    WEB_SEARCHER_URL: str = "http://web_searcher:8093"
    IMAGE_BACKEND_URL: str = "http://image_generator:8094"
    
    IMAGE_VALID_SIZES: list[str] = ["1024x1024"]
    TOOL_REQUEST_TIMEOUT_SECONDS: float = 45.0

    MAX_RETRIES: int = 3
    INITIAL_BACKOFF: float = 0.5

def get_settings() -> Settings:
    global _settings_cache
    if _settings_cache is None:
        _settings_cache = Settings()
    return _settings_cache

def override_settings(settings: Settings) -> None:
    global _settings_cache
    _settings_cache = settings

def reset_settings() -> None:
    global _settings_cache
    _settings_cache = None
    
