import asyncio
import httpx
from typing import Any

from app import _http, log, settings


async def call_external(base_url: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """POST arguments to an ExternalToolAdapter's /invoke endpoint with retry logic."""
    if not base_url or not isinstance(base_url, str):
        raise ValueError("base_url must be a non-empty string")
    if not isinstance(arguments, dict):
        raise TypeError("arguments must be a dictionary")

    url = base_url.rstrip("/") + "/invoke"
    last_error = None

    for attempt in range(settings.MAX_RETRIES):
        try:
            response = await _http.post(
                url,
                json={"arguments": arguments},
                timeout=settings.TOOL_REQUEST_TIMEOUT_SECONDS,
            )
            response.raise_for_status()

            try:
                payload = response.json()
            except ValueError as e:
                log.error(f"Failed to parse JSON response from {url}: {e}")
                raise ValueError("External tool returned invalid JSON") from e

            if not isinstance(payload, dict):
                raise ValueError("External tool returned a non-object payload")

            return payload

        except httpx.HTTPStatusError as e:
            if 400 <= e.response.status_code < 500:
                log.error(
                    f"Client error calling {base_url}: status={e.response.status_code}, "
                    f"body={e.response.text[:500]}"
                )
                raise
            
            last_error = e
            log.warning(
                f"Server error from {base_url} (attempt {attempt + 1}/{settings.MAX_RETRIES}): "
                f"status={e.response.status_code}"
            )

        except (httpx.TimeoutException, httpx.RequestError) as e:
            last_error = e
            log.warning(
                f"Network/Timeout error calling {base_url} "
                f"(attempt {attempt + 1}/{settings.MAX_RETRIES}): {e}"
            )

        if last_error and attempt < settings.MAX_RETRIES - 1:
            backoff = settings.INITIAL_BACKOFF * (2 ** attempt)
            log.info(f"Retrying in {backoff}s...")
            await asyncio.sleep(backoff)

    raise RuntimeError(
        f"Failed to call external service {base_url} after {settings.MAX_RETRIES} attempts"
    ) from last_error
