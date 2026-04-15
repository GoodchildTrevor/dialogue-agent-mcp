import httpx
from typing import Any

from app import _http, log, settings


async def _call_external(base_url: str, arguments: dict[str, Any]) -> dict[str, Any]:
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

        except httpx.TimeoutException as e:
            last_error = e
            if attempt < settings.MAX_RETRIES - 1:
                backoff = settings.INITIAL_BACKOFF * (2 ** attempt)
                log.warning(
                    f"Timeout calling {base_url} (attempt {attempt + 1}/{settings.MAX_RETRIES}), "
                    f"retrying in {backoff}s"
                )
                import asyncio
                await asyncio.sleep(backoff)
            else:
                log.error(f"Timeout calling {base_url} after {settings.MAX_RETRIES} attempts")

        except httpx.HTTPStatusError as e:
            log.error(
                f"HTTP error calling {base_url}: status={e.response.status_code}, "
                f"body={e.response.text[:500]}"
            )
            if e.response.status_code >= 500 and attempt < settings.MAX_RETRIES - 1:
                backoff = settings.INITIAL_BACKOFF * (2 ** attempt)
                log.info(
                    f"Server error from {base_url} (attempt {attempt + 1}/{settings.MAX_RETRIES}), "
                    f"retrying in {backoff}s"
                )
                import asyncio
                await asyncio.sleep(backoff)
            else:
                raise

        except httpx.RequestError as e:
            last_error = e
            if attempt < settings.MAX_RETRIES - 1:
                backoff = settings.INITIAL_BACKOFF * (2 ** attempt)
                log.warning(
                    f"Request error calling {base_url} (attempt {attempt + 1}/{settings.MAX_RETRIES}), "
                    f"retrying in {backoff}s: {e}"
                )
                import asyncio
                await asyncio.sleep(backoff)
            else:
                log.error(f"Request error calling {base_url} after {settings.MAX_RETRIES} attempts: {e}")

    raise RuntimeError(
        f"Failed to call external service {base_url} after {settings.MAX_RETRIES} attempts"
    ) from last_error
