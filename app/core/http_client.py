from __future__ import annotations

import logging
from typing import Any

import httpx

log = logging.getLogger(__name__)


class BaseAPIClient:
    """Base HTTP client for external API integrations.

    Encapsulates:
    - URL construction (base_url + path)
    - Authorization header injection
    - Unified error handling with structured logging
    - Reuse of the shared httpx.AsyncClient managed by the app lifespan

    The httpx.AsyncClient is intentionally NOT stored on the instance —
    it lives in the app lifespan (app/__init__.py) and is passed explicitly
    to each request method to preserve correct connection lifecycle management.

    Subclasses should define domain-specific methods that call _get / _post
    and map raw response dicts to their own return types.
    """

    def __init__(
        self,
        base_url: str,
        auth_token: str | None = None,
        auth_header_name: str = "Authorization",
        auth_scheme: str = "Bearer",
    ) -> None:
        """Initialise the client with a base URL and optional auth credentials.

        :param base_url: Root URL of the target API. Trailing slashes are stripped.
        :param auth_token: Token value to send in the auth header. Omitted when None.
        :param auth_header_name: Name of the auth header (default: "Authorization").
        :param auth_scheme: Prefix placed before the token (default: "Bearer").
        """
        self.base_url = base_url.rstrip("/")
        self._auth_token = auth_token
        self._auth_header_name = auth_header_name
        self._auth_scheme = auth_scheme

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_url(self, path: str) -> str:
        """Join base_url and path, normalising leading slashes.

        :param path: Relative path to the endpoint.
        :return: Absolute URL string.
        """
        return f"{self.base_url}/{path.lstrip('/')}"

    def _auth_headers(self) -> dict[str, str]:
        """Return the Authorization header dict, or an empty dict when no token is set.

        :return: Header dict ready to be merged into a request.
        """
        if not self._auth_token:
            return {}
        return {self._auth_header_name: f"{self._auth_scheme} {self._auth_token}"}

    # ------------------------------------------------------------------
    # HTTP verb helpers
    # ------------------------------------------------------------------

    async def _get(
        self,
        client: httpx.AsyncClient,
        path: str,
        *,
        params: dict | None = None,
        extra_headers: dict | None = None,
        timeout: float | None = None,
    ) -> dict[str, Any] | None:
        """Send a GET request and return the parsed JSON body.

        :param client: Shared httpx.AsyncClient from the app lifespan.
        :param path: Relative path appended to base_url.
        :param params: Optional query-string parameters.
        :param extra_headers: Headers merged on top of the auth header.
        :param timeout: Per-request timeout override in seconds.
        :return: Parsed response dict, or None on any error.
        """
        url = self._build_url(path)
        headers = {**self._auth_headers(), **(extra_headers or {})}
        return await self._request(
            client, "GET", url, headers=headers, params=params, timeout=timeout
        )

    async def _post(
        self,
        client: httpx.AsyncClient,
        path: str,
        *,
        json: dict | None = None,
        data: dict | None = None,
        extra_headers: dict | None = None,
        timeout: float | None = None,
    ) -> dict[str, Any] | None:
        """Send a POST request and return the parsed JSON body.

        :param client: Shared httpx.AsyncClient from the app lifespan.
        :param path: Relative path appended to base_url.
        :param json: Request body serialised as JSON.
        :param data: Request body sent as form data.
        :param extra_headers: Headers merged on top of the auth header.
        :param timeout: Per-request timeout override in seconds.
        :return: Parsed response dict, or None on any error.
        """
        url = self._build_url(path)
        headers = {**self._auth_headers(), **(extra_headers or {})}
        return await self._request(
            client, "POST", url, headers=headers, json=json, data=data, timeout=timeout
        )

    # ------------------------------------------------------------------
    # Core request dispatcher
    # ------------------------------------------------------------------

    async def _request(
        self,
        client: httpx.AsyncClient,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> dict[str, Any] | None:
        """Execute an HTTP request and handle all error cases uniformly.

        Catches network-level errors (timeout, connection failure, generic
        request error), HTTP error status codes, and JSON decode failures.
        All errors are logged and result in a None return value so callers
        can handle unavailability without try/except boilerplate.

        :param client: Shared httpx.AsyncClient from the app lifespan.
        :param method: HTTP method string (e.g. "GET", "POST").
        :param url: Fully-qualified target URL.
        :param kwargs: Additional kwargs forwarded to httpx.AsyncClient.request.
        :return: Parsed response dict, or None on any error.
        """
        try:
            response = await client.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
        except (httpx.TimeoutException, httpx.ConnectError, httpx.RequestError) as e:
            log.warning("[%s] unreachable at %s: %s", self.__class__.__name__, url, e)
            return None
        except httpx.HTTPStatusError as e:
            log.error(
                "[%s] HTTP %s at %s",
                self.__class__.__name__,
                e.response.status_code,
                url,
            )
            return None
        except ValueError as e:
            log.error("[%s] invalid JSON from %s: %s", self.__class__.__name__, url, e)
            return None
