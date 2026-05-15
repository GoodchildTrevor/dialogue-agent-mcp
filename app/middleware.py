"""Bearer token authentication middleware for the FastMCP server."""
from __future__ import annotations

import json


class BearerAuthMiddleware:
    """Reject any HTTP request that does not carry a valid Bearer token.

    Uses a pure ASGI implementation so that ``lifespan`` events are forwarded
    to the wrapped application unchanged — ``BaseHTTPMiddleware`` swallows them
    which prevents ``http_client`` from being initialised.

    :param app: The ASGI application to wrap.
    :param token: The expected Bearer token value.
    """

    def __init__(self, app, token: str) -> None:
        self._app = app
        self._token = token

    async def __call__(self, scope, receive, send) -> None:
        # Forward lifespan events directly — no auth check needed.
        if scope["type"] == "lifespan":
            await self._app(scope, receive, send)
            return

        if scope["type"] == "http":
            headers = {k.lower(): v for k, v in scope.get("headers", [])}
            auth = headers.get(b"authorization", b"").decode()
            if auth != f"Bearer {self._token}":
                await send(
                    {
                        "type": "http.response.start",
                        "status": 401,
                        "headers": [
                            [b"content-type", b"application/json"],
                        ],
                    }
                )
                body = json.dumps({"detail": "Unauthorized"}).encode()
                await send(
                    {
                        "type": "http.response.body",
                        "body": body,
                        "more_body": False,
                    }
                )
                return

        await self._app(scope, receive, send)
