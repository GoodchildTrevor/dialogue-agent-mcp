from typing import Any

import httpx
from sqlalchemy import select

from app import _http, _ollama, log, mcp, settings
from app.db.session import async_session_maker
from app.db.models import Message
from app.utils.external import call_external
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
    """Search corporate documents via qdrant-searcher hybrid search endpoint."""
    query = _validate_query(query)
    if filters is not None and not isinstance(filters, dict):
        raise TypeError("filters must be a dictionary")
    limit = _validate_limit(limit, default=10)

    collection_name = (filters or {}).get("collection", settings.DOCUMENT_SEARCHER_DEFAULT_COLLECTION)
    method = (filters or {}).get("method", "hybrid")
    if method not in ("hybrid", "dense"):
        method = "hybrid"

    base_url = settings.DOCUMENT_SEARCHER_URL.rstrip("/")
    search_url = f"{base_url}/vector_search"

    payload = {
        "text": query,
        "method": method,
        "collection_name": collection_name,
        "top_k": limit,
    }

    headers = {
        "Authorization": f"Bearer {settings.DOCUMENT_SEARCHER_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        response = await _http.post(
            search_url,
            json=payload,
            headers=headers,
            timeout=settings.TOOL_REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
    except (httpx.TimeoutException, httpx.ConnectError, httpx.RequestError) as e:
        log.warning(f"qdrant-searcher unreachable at {search_url}: {e}")
        return {"query": query, "results": [], "error": "Document search service is currently unavailable"}
    except httpx.HTTPStatusError as e:
        log.error(f"qdrant-searcher returned HTTP {e.response.status_code} for query '{query}'")
        return {"query": query, "results": [], "error": f"Document search returned status {e.response.status_code}"}
    except ValueError as e:
        log.error(f"qdrant-searcher returned invalid JSON: {e}")
        return {"query": query, "results": [], "error": "Document search returned invalid response"}

    raw_docs: list[dict] = data.get("documents", [])

    results = [
        {
            "id": doc.get("id", ""),
            "content": doc.get("payload", {}).get("text", ""),
            "score": doc.get("score", 0.0),
            "metadata": {
                k: v for k, v in doc.get("payload", {}).items() if k != "text"
            } | {"source": doc.get("source", "")},
        }
        for doc in raw_docs
        if doc
    ]

    return {"query": query, "results": results}


@mcp.tool()
async def web_searcher(
    query: str,
    limit: int | None = None,
) -> dict[str, Any]:
    """Search the public web using a self-hosted SearXNG instance."""
    query = _validate_query(query)
    limit = _validate_limit(limit, default=10)

    params = {
        "q": query,
        "format": "json",
        "pageno": 1,
    }

    base_url = settings.WEB_SEARCHER_URL.rstrip("/")
    search_url = f"{base_url}/search"

    try:
        response = await _http.get(
            search_url,
            params=params,
            timeout=settings.TOOL_REQUEST_TIMEOUT_SECONDS,
            headers={"Accept": "application/json"},
        )
        response.raise_for_status()
        data = response.json()
    except (httpx.TimeoutException, httpx.ConnectError, httpx.RequestError) as e:
        log.warning(f"SearXNG unreachable at {search_url}: {e}")
        return {"query": query, "results": [], "error": "Web search service is currently unavailable"}
    except httpx.HTTPStatusError as e:
        log.error(f"SearXNG returned HTTP {e.response.status_code} for query '{query}'")
        return {"query": query, "results": [], "error": f"Web search returned status {e.response.status_code}"}
    except ValueError as e:
        log.error(f"SearXNG returned invalid JSON: {e}")
        return {"query": query, "results": [], "error": "Web search returned invalid response"}

    raw_results: list[dict] = data.get("results", [])

    results = [
        {
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "snippet": r.get("content", ""),
        }
        for r in raw_results[:limit]
        if r.get("url")
    ]

    return {"query": query, "results": results}
