import logging
from contextlib import asynccontextmanager
from typing import Any

import httpx
from fastmcp import FastMCP

from app.core.config import get_settings
from app.context import current_app

settings = get_settings()
logging.basicConfig(level=settings.LOG_LEVEL)
log = logging.getLogger(__name__)

http_client: httpx.AsyncClient | None = None


def get_http_client() -> httpx.AsyncClient:
    if http_client is None:
        raise RuntimeError("http_client is not initialised (lifespan not started)")
    return http_client


@asynccontextmanager
async def lifespan(app: Any):
    global http_client
    token = current_app.set(app)

    http_client = httpx.AsyncClient(
        timeout=settings.TOOL_REQUEST_TIMEOUT_SECONDS,
        headers={"User-Agent": "mcp-client/1.0"},
    )

    log.info("dialogue-agent-mcp started")

    try:
        yield
    finally:
        if http_client is not None:
            await http_client.aclose()
        http_client = None
        current_app.reset(token)
        log.info("dialogue-agent-mcp stopped")
        