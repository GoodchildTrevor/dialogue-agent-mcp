from typing import Any

from sqlalchemy import select

from app import _ollama, log, mcp, settings
from app.db.session import async_session_maker
from app.db.models import Message
from app.utils.external import _call_external 
from app.utils.validations import (
    _validate_query,
    _validate_user_id,
    _validate_limit,
)


@mcp.tool()
async def search_history(
    query: str,
    user_id: str,
    limit: int = 5,
) -> dict[str, Any]:
    """Semantic search over the user's previous messages stored in PostgreSQL/PGvector."""
    # Input validation
    query = _validate_query(query)
    user_id = _validate_user_id(user_id)
    limit = _validate_limit(limit, default=5, max_val=10)

    if _ollama is None:
        raise RuntimeError("OllamaClient is not initialised")

    try:
        embedding = await _ollama.embeddings(model=settings.EMBEDDING_MODEL, prompt=query)
    except Exception as e:
        log.error(f"Failed to generate embeddings for query: {e}")
        raise RuntimeError("Failed to generate embeddings") from e

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

@mcp.tool()
async def document_searcher(
    query: str,
    filters: dict[str, Any] | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    """Search corporate documents via an external retrieval API."""
    # Input validation
    query = _validate_query(query)
    if filters is not None and not isinstance(filters, dict):
        raise TypeError("filters must be a dictionary")
    limit = _validate_limit(limit, default=None)

    args: dict[str, Any] = {"query": query}
    if filters is not None:
        args["filters"] = filters
    if limit is not None:
        args["limit"] = limit
    return await _call_external(settings.DOCUMENT_SEARCHER_URL, args)


@mcp.tool()
async def web_searcher(
    query: str,
    limit: int | None = None,
) -> dict[str, Any]:
    """Search the public web using an external search service."""
    # Input validation
    query = _validate_query(query)
    limit = _validate_limit(limit, default=None)

    args: dict[str, Any] = {"query": query}
    if limit is not None:
        args["limit"] = limit
    return await _call_external(settings.WEB_SEARCHER_URL, args)