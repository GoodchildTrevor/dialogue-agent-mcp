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

from app import mcp
from app.middleware import BearerAuthMiddleware

_token = os.environ["MCP_AUTH_TOKEN"]
mcp_app = BearerAuthMiddleware(mcp.http_app(), token=_token)
