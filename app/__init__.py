import asyncio
import logging 
from contextlib import asynccontextmanager
from typing import Any

import httpx
from fastmcp import FastMCP

from app.core.config import get_settings
from app.core.ollama import OllamaClient
from app.db.session import init_db

settings = get_settings()
logging.basicConfig(level=settings.LOG_LEVEL)
log = logging.getLogger(__name__)

# Shared HTTP client for external tool adapters
_http = httpx.AsyncClient(timeout=settings.TOOL_REQUEST_TIMEOUT_SECONDS)
_ollama: OllamaClient | None = None
_initialization_lock = None  # Will be set to asyncio.Lock() after import

async def get_ollama() -> OllamaClient:
    global _ollama, _initialization_lock
    if _ollama is not None:
        return _ollama
    if _initialization_lock is None:
        raise RuntimeError("OllamaClient initialization lock not set. Application startup incomplete.")
    async with _initialization_lock:
        if _ollama is not None:
            return _ollama
        raise RuntimeError("OllamaClient is not initialized. Ensure the application startup has completed.")

@asynccontextmanager
async def lifespan(app: Any):
    global _ollama, _initialization_lock
    _ollama = OllamaClient(settings)
    _initialization_lock = asyncio.Lock()
    log.info("dialogue-agent-mcp started")
    yield
    if _ollama:
        await _ollama.aclose()
    if _http:
        await _http.aclose()

mcp = FastMCP(
    name="dialogue-agent-mcp",
    instructions="Tools from the dialogue-agent: search history, search documents, "
                 "browse the web, view/convert files, and generate images.",
    lifespan=lifespan,
)