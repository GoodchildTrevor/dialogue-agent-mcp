from typing import Any

from app import mcp, settings, get_http_client
from app.core.config import DOCUMENT_COLLECTIONS
from app.core.http_client import BaseAPIClient
from app.utils.validations import _validate_query, _validate_limit


class _DocumentSearcherClient(BaseAPIClient):
    """API client for the qdrant-searcher hybrid search service."""

    def __init__(self) -> None:
        super().__init__(
            base_url=settings.DOCUMENT_SEARCHER_URL,
            auth_token=settings.DOCUMENT_SEARCHER_API_KEY,
        )

    async def search(
        self,
        query: str,
        collection: str,
        method: str,
        limit: int,
        file_id: str | None = None,
    ) -> dict[str, Any] | None:
        """Run a vector search against the qdrant-searcher endpoint.

        :param query: Search query text.
        :param collection: Qdrant collection name to search.
        :param method: Search method — ``"hybrid"`` or ``"dense"``.
        :param limit: Maximum number of results to return.
        :param file_id: Optional file UUID to restrict results to a single file.
        :return: Raw response dict from the service, or None on error.
        """
        payload: dict[str, Any] = {
            "text": query,
            "method": method,
            "collection_name": collection,
            "top_k": limit,
        }
        if file_id:
            payload["filters"] = {"file_id": file_id}
        return await self._post(
            get_http_client(),
            "/vector_search",
            json=payload,
            extra_headers={"Content-Type": "application/json"},
            timeout=settings.TOOL_REQUEST_TIMEOUT_SECONDS,
        )


class _WebSearcherClient(BaseAPIClient):
    """API client for the self-hosted SearXNG search instance."""

    def __init__(self) -> None:
        super().__init__(base_url=settings.WEB_SEARCHER_URL)

    async def search(
        self,
        query: str,
        limit: int,
    ) -> dict[str, Any] | None:
        """Fetch web search results from SearXNG.

        :param query: Search query text.
        :param limit: Maximum number of results to return.
        :return: Raw response dict from SearXNG, or None on error.
        """
        return await self._get(
            get_http_client(),
            "/search",
            params={"q": query, "format": "json", "pageno": 1},
            extra_headers={"Accept": "application/json"},
            timeout=settings.TOOL_REQUEST_TIMEOUT_SECONDS,
        )


_doc_client = _DocumentSearcherClient()
_web_client = _WebSearcherClient()


def _collections_hint() -> str:
    """Build a human-readable collection list for the tool docstring."""
    if not DOCUMENT_COLLECTIONS:
        return f'"{settings.DOCUMENT_SEARCHER_DEFAULT_COLLECTION}" (default)'
    return "; ".join(f'"{k}" — {v}' for k, v in DOCUMENT_COLLECTIONS.items())


def _resolve_collection(collection: str | None) -> str:
    """Validate and return the collection name.

    If DOCUMENT_COLLECTIONS is configured, the requested collection must be
    one of the known keys. Falls back to the default collection when None.
    """
    if collection is None:
        return settings.DOCUMENT_SEARCHER_DEFAULT_COLLECTION
    if DOCUMENT_COLLECTIONS and collection not in DOCUMENT_COLLECTIONS:
        known = list(DOCUMENT_COLLECTIONS.keys())
        raise ValueError(f"Unknown collection {collection!r}. Available: {known}")
    return collection


_DOC_SEARCH_DOC = f"""Search corporate documents via qdrant-searcher hybrid search endpoint.

Available collections: {_collections_hint()}
Choose the most relevant collection based on the query topic.

:param query: The query to search for.
:param collection: Collection name to search. Must be one of the available collections listed above.
    Omit to use the default collection.
:param file_id: Optional file UUID to restrict search to a specific uploaded file.
:param limit: The number of results to return.
:return: The search results.
"""


@mcp.tool()
async def document_searcher(
    query: str,
    collection: str | None = None,
    file_id: str | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    query = _validate_query(query)
    limit = _validate_limit(limit, default=10)
    collection = _resolve_collection(collection)
    method = "hybrid"

    data = await _doc_client.search(
        query=query,
        collection=collection,
        method=method,
        limit=limit,
        file_id=file_id,
    )
    if data is None:
        return {"query": query, "results": [], "error": "Document search service is currently unavailable"}

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
    return {"query": query, "collection": collection, "results": results}


document_searcher.__doc__ = _DOC_SEARCH_DOC


@mcp.tool()
async def web_searcher(
    query: str,
    limit: int | None = None,
) -> dict[str, Any]:
    """Search the public web using a self-hosted SearXNG instance.
    :param query: The query to search for.
    :param limit: The number of results to return.
    :return: The search results.
    """
    query = _validate_query(query)
    limit = _validate_limit(limit, default=10)

    data = await _web_client.search(query=query, limit=limit)
    if data is None:
        return {"query": query, "results": [], "error": "Web search service is currently unavailable"}

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
