"""Bearer token authentication middleware for the FastMCP server."""
from __future__ import annotations

import os

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class BearerAuthMiddleware(BaseHTTPMiddleware):
    """Reject any request that does not carry a valid Bearer token."""

    def __init__(self, app, token: str) -> None:
        super().__init__(app)
        self._token = token

    async def dispatch(self, request: Request, call_next):
        auth = request.headers.get("Authorization", "")
        if auth != f"Bearer {self._token}":
            return JSONResponse({"detail": "Unauthorized"}, status_code=401)
        return await call_next(request)
