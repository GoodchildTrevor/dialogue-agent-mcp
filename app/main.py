"""MCP server for dialogue-agent tools.

Exposes all tools from the original dialogue-agent as MCP tools
over HTTP/SSE transport (fastmcp). Each tool mirrors the original
ToolSpec signature so the agent can swap ExternalToolAdapter calls
for MCP calls without changing argument schemas.

Transport: Streamable HTTP (default fastmcp transport).
Endpoint:  POST /mcp  (SSE fallback: GET /mcp)
"""
from __future__ import annotations

from app import mcp

mcp_app = mcp.http_app()
