from typing import Any

from app import mcp, settings, get_http_client
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


@mcp.tool()
async def document_searcher(
    query: str,
    file_id: str | None = None,
    filters: dict[str, Any] | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    """Search corporate documents via qdrant-searcher hybrid search endpoint.
    :param query: The query to search for.
    :param file_id: Optional file UUID to restrict search to a specific uploaded file.
    :param filters: The filters to apply to the search.
    :param limit: The number of results to return.
    :return: The search results.
    """
    query = _validate_query(query)
    if filters is not None and not isinstance(filters, dict):
        raise TypeError("filters must be a dictionary")
    limit = _validate_limit(limit, default=10)

    collection = (filters or {}).get("collection", settings.DOCUMENT_SEARCHER_DEFAULT_COLLECTION)
    method = (filters or {}).get("method", "hybrid")
    if method not in ("hybrid", "dense"):
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
    return {"query": query, "results": results}


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
