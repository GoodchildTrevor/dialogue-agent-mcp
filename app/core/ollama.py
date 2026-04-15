from __future__ import annotations

from typing import Any

import httpx

from app.core.config import Settings

class OllamaClient:
    def __init__(self, settings: Settings) -> None:
        self._client = httpx.AsyncClient(
            base_url=settings.OLLAMA_BASE_URL.rstrip("/"),
            timeout=settings.TOOL_REQUEST_TIMEOUT_SECONDS,
        )

    async def embeddings(self, *, model: str, prompt: str) -> list[float]:
        response = await self._client.post(
            "/api/embeddings",
            json={"model": model, "prompt": prompt},
        )
        response.raise_for_status()
        embedding = response.json().get("embedding")
        if not embedding:
            raise ValueError("Ollama returned empty embedding")
        return embedding

    async def aclose(self) -> None:
        await self._client.aclose()