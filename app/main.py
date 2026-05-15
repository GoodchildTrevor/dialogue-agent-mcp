"""MCP server for dialogue-agent tools.

Exposes all tools from the original dialogue-agent as MCP tools
over HTTP/SSE transport (fastmcp). Each tool mirrors the original
ToolSpec signature so the agent can swap ExternalToolAdapter calls
for MCP calls without changing argument schemas.

Transport: Streamable HTTP (default fastmcp transport).
Endpoint:  POST /mcp  (SSE fallback: GET /mcp)

Auth: requests without a valid Authorization: Bearer <token> header
      receive HTTP 401. Token is read from MCP_AUTH_TOKEN env var.
"""
from __future__ import annotations

import json
import os

import app.tools  # noqa: F401  register tools with mcp
from app import mcp

_token = os.environ["MCP_AUTH_TOKEN"]


class _BearerASGI:
    """Minimal pure-ASGI auth wrapper that forwards lifespan unchanged."""

    def __init__(self, inner) -> None:
        self._inner = inner

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            # lifespan and websocket pass through untouched
            await self._inner(scope, receive, send)
            return

        headers = {k.lower(): v for k, v in scope.get("headers", [])}
        auth = headers.get(b"authorization", b"").decode()
        if auth != f"Bearer {_token}":
            body = json.dumps({"detail": "Unauthorized"}).encode()
            await send(
                {
                    "type": "http.response.start",
                    "status": 401,
                    "headers": [[b"content-type", b"application/json"]],
                }
            )
            await send({"type": "http.response.body", "body": body, "more_body": False})
            return

        await self._inner(scope, receive, send)


mcp_app = _BearerASGI(mcp.http_app())
