"""MCP server for dialogue-agent tools.

Exposes all tools from the original dialogue-agent as MCP tools
over HTTP/SSE transport (fastmcp). Each tool mirrors the original
ToolSpec signature so the agent can swap ExternalToolAdapter calls
for MCP calls without changing argument schemas.

Transport: Streamable HTTP (default fastmcp transport).
Endpoint:  POST /mcp  (SSE fallback: GET /mcp)
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

import httpx
from fastmcp import FastMCP
from sqlalchemy import select

from app.core.config import get_settings
from app.core.ollama import OllamaClient
from app.db.models import Message
from app.db.session import async_session_maker, init_db

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

settings = get_settings()
logging.basicConfig(level=settings.LOG_LEVEL)
log = logging.getLogger(__name__)

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

# Shared HTTP client for external tool adapters
_http = httpx.AsyncClient(timeout=settings.TOOL_REQUEST_TIMEOUT_SECONDS)


async def _call_external(base_url: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """POST arguments to an ExternalToolAdapter's /invoke endpoint."""
    response = await _http.post(
        base_url.rstrip("/") + "/invoke",
        json={"arguments": arguments},
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("External tool returned a non-object payload")
    return payload


# ---------------------------------------------------------------------------
# Tool: search_history
# Semantic search over the current user's previous messages (PGvector).
# user_id is passed explicitly because MCP tools have no ToolContext.
# ---------------------------------------------------------------------------

@mcp.tool()
async def search_history(
    query: str,
    user_id: str,
    limit: int = 5,
) -> dict[str, Any]:
    """Semantic search over the user's previous messages stored in PostgreSQL/PGvector."""
    if _ollama is None:
        raise RuntimeError("OllamaClient is not initialised")

    limit = max(1, min(limit, 10))
    embedding = await _ollama.embeddings(model=settings.EMBEDDING_MODEL, prompt=query)

    async with async_session_maker() as session:
        distance = Message.embedding.cosine_distance(embedding)
        stmt = (
            select(
                Message.id,
                Message.role,
                Message.content,
                Message.created_at,
                distance.label("distance"),
            )
            .where(Message.user_id == user_id, Message.embedding.is_not(None))
            .order_by(distance)
            .limit(limit)
        )
        rows = (await session.execute(stmt)).all()

    return {
        "query": query,
        "matches": [
            {
                "id": str(row.id),
                "role": row.role,
                "content": row.content,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "distance": float(row.distance),
            }
            for row in rows
        ],
    }


# ---------------------------------------------------------------------------
# Tool: document_searcher
# ---------------------------------------------------------------------------

@mcp.tool()
async def document_searcher(
    query: str,
    filters: dict[str, Any] | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    """Search corporate documents via an external retrieval API."""
    args: dict[str, Any] = {"query": query}
    if filters is not None:
        args["filters"] = filters
    if limit is not None:
        args["limit"] = limit
    return await _call_external(settings.DOCUMENT_SEARCHER_URL, args)


# ---------------------------------------------------------------------------
# Tool: web_searcher
# ---------------------------------------------------------------------------

@mcp.tool()
async def web_searcher(
    query: str,
    limit: int | None = None,
) -> dict[str, Any]:
    """Search the public web using an external search service."""
    args: dict[str, Any] = {"query": query}
    if limit is not None:
        args["limit"] = limit
    return await _call_external(settings.WEB_SEARCHER_URL, args)


# ---------------------------------------------------------------------------
# Tool: file_viewer
# ---------------------------------------------------------------------------

@mcp.tool()
async def file_viewer(
    file_id: str | None = None,
    path: str | None = None,
    page: int | None = None,
) -> dict[str, Any]:
    """Preview or read file contents through an external file service."""
    args: dict[str, Any] = {}
    if file_id is not None:
        args["file_id"] = file_id
    if path is not None:
        args["path"] = path
    if page is not None:
        args["page"] = page
    return await _call_external(settings.FILE_VIEWER_URL, args)


# ---------------------------------------------------------------------------
# Tool: file_converter
# ---------------------------------------------------------------------------

@mcp.tool()
async def file_converter(
    source_path: str,
    target_format: str,
) -> dict[str, Any]:
    """Convert files between supported formats through an external conversion API."""
    return await _call_external(
        settings.FILE_CONVERTER_URL,
        {"source_path": source_path, "target_format": target_format},
    )


# ---------------------------------------------------------------------------
# Tool: image_generator
# ---------------------------------------------------------------------------

@mcp.tool()
async def image_generator(
    prompt: str,
    size: str | None = None,
) -> dict[str, Any]:
    """Generate images through an external image generation API."""
    args: dict[str, Any] = {"prompt": prompt}
    if size is not None:
        args["size"] = size
    return await _call_external(settings.IMAGE_GENERATOR_URL, args)


# ---------------------------------------------------------------------------
# ASGI app (fastmcp HTTP transport)
# ---------------------------------------------------------------------------

mcp_app = mcp.http_app()
