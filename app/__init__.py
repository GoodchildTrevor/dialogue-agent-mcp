
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

@asynccontextmanager
async def lifespan(app: Any):
    global _ollama
    await init_db()
    _ollama = OllamaClient(settings)
    log.info("dialogue-agent-mcp started")
    yield
    if _ollama:
        await _ollama.aclose()

mcp = FastMCP(
    name="dialogue-agent-mcp",
    instructions="Tools from the dialogue-agent: search history, search documents, "
                 "browse the web, view/convert files, and generate images.",
    lifespan=lifespan,
)