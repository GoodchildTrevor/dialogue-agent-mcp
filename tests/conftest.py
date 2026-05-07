import copy

import httpx
import pytest
import pytest_asyncio

import app


@pytest_asyncio.fixture
async def async_http_client() -> httpx.AsyncClient:
    client = httpx.AsyncClient()
    app.http_client = client
    try:
        yield client
    finally:
        await client.aclose()
        app.http_client = None


@pytest.fixture(autouse=True)
def reset_settings() -> None:
    original = {k: copy.deepcopy(v) for k, v in app.settings.model_dump().items()}
    try:
        yield
    finally:
        for key, value in original.items():
            setattr(app.settings, key, value)
