import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any

import httpx
from fastmcp import FastMCP

from app.core.config import get_settings

settings = get_settings()
logging.basicConfig(level=settings.LOG_LEVEL)
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: Any):
    from storage.paths import ensure_export_dir
    from app.core.templates import TemplateRegistry

    ensure_export_dir(settings.FILE_EXPORT_DIR)
    TemplateRegistry.init(settings.DOCS_TEMPLATE_PATH)
    
    app.state.http = httpx.AsyncClient(
        timeout=settings.TOOL_REQUEST_TIMEOUT_SECONDS,
        headers={"User-Agent": "mcp-client/1.0"},
    )

    log.info("file-converter-mcp started (v%s)", settings.VERSION)
    yield

    await app.state.http.aclose()
    log.info("file-converter-mcp stopped")


mcp = FastMCP(
    name="dialogue-agent-mcp",
    instructions="Tools from the dialogue-agent: search history, search documents, "
                 "browse the web, view/convert files, and generate images.",
    lifespan=lifespan,
)
