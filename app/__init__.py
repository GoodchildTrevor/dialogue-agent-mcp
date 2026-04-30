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


@asynccontextmanager
async def lifespan(app: Any):
    token = current_app.set(app)

    app.state.http = httpx.AsyncClient(
        timeout=settings.TOOL_REQUEST_TIMEOUT_SECONDS,
        headers={"User-Agent": "mcp-client/1.0"},
    )

    log.info("dialogue-agent-mcp started (v%s)", settings.VERSION)

    try:
        yield
    finally:
        await app.state.http.aclose()
        current_app.reset(token)
        log.info("dialogue-agent-mcp stopped")


mcp = FastMCP(
    name="dialogue-agent-mcp",
    instructions=(
        "Tools from the dialogue-agent: search history, search documents, "
        "browse the web, view/convert files, and generate images."
    ),
    lifespan=lifespan,
)
