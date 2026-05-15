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

import os

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.routing import Mount

from app import mcp
from app.middleware import BearerAuthMiddleware
import app.tools

_token = os.environ["MCP_AUTH_TOKEN"]

# Mount the FastMCP ASGI app inside a Starlette application so that
# the lifespan is managed by Starlette and our auth middleware only
# intercepts HTTP requests, not lifespan events.
mcp_app = Starlette(
    routes=[Mount("/", app=mcp.http_app())],
    middleware=[Middleware(BearerAuthMiddleware, token=_token)],
    lifespan=mcp.http_app().router.lifespan_context,
)
