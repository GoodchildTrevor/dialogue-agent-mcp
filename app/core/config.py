from __future__ import annotations

import json
import logging
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

_settings_cache = None

_COLLECTIONS_PATH = Path("/app/collections.json")
_COLLECTIONS_FALLBACK = Path("collections.json")


def _load_collections() -> dict[str, str]:
    """Load collection definitions from collections.json.

    Looks first at /app/collections.json (container path), then at
    ./collections.json (local dev path). Falls back to a single default
    collection if the file is absent or malformed.
    """
    for path in (_COLLECTIONS_PATH, _COLLECTIONS_FALLBACK):
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, dict) and data:
                    logger.info("Loaded %d collections from %s", len(data), path)
                    return {str(k): str(v) for k, v in data.items()}
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to parse %s: %s", path, exc)
    logger.info("collections.json not found, using default collection")
    return {}


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

    IMAGE_VALID_SIZES: list[str] = ["1K", "2K", "4K", "512"]
    IMAGE_MODEL: str = "dall-e-3"
    IMAGE_MIME_TYPE: str = "image/png"
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


# Loaded once at import time so the docstring hint is available immediately.
DOCUMENT_COLLECTIONS: dict[str, str] = _load_collections()
