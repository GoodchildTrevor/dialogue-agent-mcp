import base64
from typing import Any
from unittest.mock import AsyncMock

import httpx
import pytest

from app import settings
from app.tools import file_handlers, images, searchers


class _DummyResponse:
    def __init__(self, data: dict[str, Any], status_code: int = 200) -> None:
        self._data = data
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("error", request=None, response=self)

    def json(self) -> dict[str, Any]:
        return self._data


class _DummyClient:
    def __init__(self, response: _DummyResponse | Exception) -> None:
        self._response = response

    async def post(self, *args: Any, **kwargs: Any) -> _DummyResponse:
        if isinstance(self._response, Exception):
            raise self._response
        return self._response

    async def get(self, *args: Any, **kwargs: Any) -> _DummyResponse:
        if isinstance(self._response, Exception):
            raise self._response
        return self._response


@pytest.mark.asyncio
async def test_document_searcher_success(monkeypatch) -> None:
    response_payload = {
        "documents": [
            {
                "id": "abc",
                "payload": {"text": "content", "source": "x"},
                "score": 0.9,
            }
        ]
    }
    monkeypatch.setattr(searchers, "get_http_client", lambda: _DummyClient(_DummyResponse(response_payload)))

    result = await searchers.document_searcher("query")

    assert result["query"] == "query"
    assert len(result["results"]) == 1
    assert result["results"][0]["metadata"]["source"] == "x"


@pytest.mark.asyncio
async def test_document_searcher_filters_type_guard() -> None:
    with pytest.raises(TypeError):
        await searchers.document_searcher("query", filters="not a dict")  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_document_searcher_handles_errors(monkeypatch) -> None:
    error = httpx.RequestError("timeout", request=None)
    monkeypatch.setattr(searchers, "get_http_client", lambda: _DummyClient(error))

    result = await searchers.document_searcher("query")

    assert result["error"] == "Document search service is currently unavailable"


@pytest.mark.asyncio
async def test_web_searcher_filters_results(monkeypatch) -> None:
    response_payload = {
        "results": [
            {"title": "A", "url": "https://example.com", "content": "c"},
            {"title": "B", "url": "", "content": "b"},
        ]
    }
    monkeypatch.setattr(searchers, "get_http_client", lambda: _DummyClient(_DummyResponse(response_payload)))

    result = await searchers.web_searcher("test", limit=5)

    assert result["query"] == "test"
    assert len(result["results"]) == 1


@pytest.mark.asyncio
async def test_web_searcher_handles_http_status(monkeypatch) -> None:
    response = _DummyResponse({}, status_code=500)
    async def _raise() -> _DummyResponse:
        raise httpx.HTTPStatusError("err", request=None, response=response)
    class _ErrClient:
        async def get(self, *args: Any, **kwargs: Any) -> _DummyResponse:
            raise httpx.HTTPStatusError("err", request=None, response=response)
    monkeypatch.setattr(searchers, "get_http_client", lambda: _ErrClient())

    result = await searchers.web_searcher("test")
    assert "error" in result


async def _call_external_stub(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return {"ok": True}


@pytest.mark.asyncio
async def test_file_viewer_builds_payload(monkeypatch) -> None:
    called_args: dict[str, Any] | None = None

    async def _fake_call(url: str, arguments: dict[str, Any]) -> dict[str, Any]:
        nonlocal called_args
        called_args = arguments
        return {"ok": True}

    monkeypatch.setattr(file_handlers, "call_external", AsyncMock(side_effect=_fake_call))

    response = await file_handlers.file_viewer(file_id="123", page=2)

    assert response == {"ok": True}
    assert called_args == {"file_id": "123", "page": 2}


@pytest.mark.asyncio
async def test_file_viewer_requires_identifier() -> None:
    with pytest.raises(ValueError):
        await file_handlers.file_viewer()


def test_image_generation_url_requires_setting() -> None:
    backup = settings.IMAGE_BACKEND_URL
    settings.IMAGE_BACKEND_URL = ""
    with pytest.raises(RuntimeError):
        images._image_generation_url()
    settings.IMAGE_BACKEND_URL = backup


@pytest.mark.asyncio
async def test_generate_image_success(async_http_client: Any, monkeypatch) -> None:
    payload = base64.b64encode(b"abc").decode()
    response = _DummyResponse({"data": [{"b64_json": payload}]})
    async_http_client.post = AsyncMock(return_value=response)
    settings.IMAGE_BACKEND_URL = "http://example"

    result = await images.generate_image("prompt")

    assert result["data"] == payload


@pytest.mark.asyncio
async def test_generate_image_invalid_response(async_http_client: Any) -> None:
    response = _DummyResponse({"data": []})
    async_http_client.post = AsyncMock(return_value=response)
    settings.IMAGE_BACKEND_URL = "http://example"

    with pytest.raises(RuntimeError):
        await images.generate_image("prompt")
