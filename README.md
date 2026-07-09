# dialogue-agent-mcp

This repository contains the MCP server implementation that exposes the suite of dialogue-agent tools over HTTP/SSE via the FastMCP framework. Each tool mirrors the original dialogue-agent tool signatures so the agent can swap external tool adapters for MCP calls without changing the argument schema.

## Tools

- **file_viewer**: Reads or previews files through the external file viewer service.
- **document_searcher**: Hybrid vector search across configured Qdrant collections. The model selects the appropriate collection based on the query topic.
- **web_searcher**: Public web search via a self-hosted SearXNG instance.
- **generate_image** / **edit_image**: Request the configured image backend to create or edit PNG assets encoded in base64.

Each tool lives under `app/tools` and is decorated with `@mcp.tool()` so FastMCP registers it automatically.

## Configuration

Configuration is managed via Pydantic `Settings`. Copy `.env.example` to `.env` and fill in the required values.

### Environment variables

| Variable | Description |
|---|---|
| `MCP_AUTH_TOKEN` | Bearer token clients must send to authenticate against this MCP server |
| `IMAGE_BACKEND_URL` | Base URL of the image generation backend |
| `IMAGE_VALID_SIZES` | JSON list of accepted size strings, e.g. `["1K","2K","4K","512"]` |
| `DOCUMENT_SEARCHER_URL` | URL of the qdrant-searcher service |
| `DOCUMENT_SEARCHER_DEFAULT_COLLECTION` | Fallback collection when none is specified |
| `FILE_VIEWER_URL` | URL of the file viewer service |
| `WEB_SEARCHER_URL` | URL of the SearXNG instance |
| `TOOL_REQUEST_TIMEOUT_SECONDS` | Timeout for all outbound HTTP calls (default: 45) |

### Document collections (`collections.json`)

The `document_searcher` tool exposes multiple Qdrant collections to the model. The model reads the collection descriptions from the tool docstring and picks the most relevant one automatically.

1. Copy the example file:
   ```bash
   cp collections.example.json collections.json
   ```
2. Edit `collections.json` to match your actual Qdrant collections:
   ```json
   {
     "documents": "General corporate documents and knowledge base",
     "personal_notes": "Personal notes and memos"
   }
   ```
3. Mount the file into the container (already configured in `docker-compose.yml` if present), or place it in the project root for local development.

`collections.json` is listed in `.gitignore` — commit `collections.example.json` instead.

## Running the Server

Start the MCP server by running `app.main.mcp_app`, which exposes the MCP HTTP endpoint at `POST /mcp` (and `GET /mcp` for SSE fallback). Requests must include `Authorization: Bearer <MCP_AUTH_TOKEN>`.

The server defines a lifespan context that creates a shared `httpx.AsyncClient`, used by all tools to make outbound HTTP requests.

## Extending Tools

New tools should be declared in `app/tools` and decorated with `@mcp.tool()`. Reuse the shared `http_client` via `app.http_client` and follow existing input validation helpers under `app.utils.validations` for consistency.

## Deployment Notes

Adjust `docker-compose.yml`, `Dockerfile`, or other deployment artifacts to ensure all required backend services (searcher, file viewer, image generator, etc.) are reachable via the configured URLs.

Make sure `collections.json` is mounted into the container at `/app/collections.json`.
