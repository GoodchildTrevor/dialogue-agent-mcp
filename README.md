# dialogue-agent-mcp

This repository contains the MCP server implementation that exposes the suite of dialogue-agent tools over HTTP/SSE via the FastMCP framework. Each tool mirrors the original dialogue-agent tool signatures so the agent can swap external tool adapters for MCP calls without changing the argument schema.

## Tools

- **file_viewer**: Reads or previews files through the external file viewer service.
- **searchers**: Provides document/web search capabilities via dedicated services.
- **generate_image**: Requests the configured image backend to create PNG assets encoded in base64.

Each tool lives under `app/tools` and is decorated with `@mcp.tool()` so FastMCP registers it automatically.

## Configuration

Configuration is managed via Pydantic `Settings`. Set relevant environment variables (see `.env.example`) before running the MCP server. Key variables:

- `MCP_AUTH_TOKEN`: Bearer token used by clients to authenticate against the MCP server.
- `IMAGE_BACKEND_URL`: Base URL for the image generation backend (e.g. `http://image_generator:8094`). `generate_image` POSTs to `{IMAGE_BACKEND_URL}/v1/images/generations`.
- `DOCUMENT_SEARCHER_URL`, `FILE_VIEWER_URL`, `WEB_SEARCHER_URL`, `FILE_CONVERTER_URL`: URLs for the supporting services.
- `TOOL_REQUEST_TIMEOUT_SECONDS`: Timeout applied to all outbound HTTP calls.

## Running the Server

Start the MCP server by running `app.main.mcp_app`, which exposes the MCP HTTP endpoint at `POST /mcp` (and `GET /mcp` for SSE fallback). Requests must include `Authorization: Bearer <MCP_AUTH_TOKEN>`.

The server defines a lifespan context that creates a shared `httpx.AsyncClient`, used by all tools to make outbound HTTP requests.

## Extending Tools

New tools should be declared in `app/tools` and decorated with `@mcp.tool()`. Reuse the shared `http_client` via `app.http_client` and follow existing input validation helpers under `app.utils.validations` for consistency.

## Deployment Notes

Adjust `docker-compose.yml`, `Dockerfile`, or other deployment artifacts to ensure all required backend services (searcher, file viewer, image generator, etc.) are reachable via the configured URLs.
