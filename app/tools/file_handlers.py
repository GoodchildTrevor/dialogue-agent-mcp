from typing import Any

from app import mcp, settings
from app.utils.external import call_external
from app.utils.validations import (
    _validate_format,
    _validate_file_path,
)

@mcp.tool()
async def file_viewer(
    file_id: str | None = None,
    path: str | None = None,
    page: int | None = None,
) -> dict[str, Any]:
    """Preview or read file contents through an external file service."""
    # Input validation
    if file_id is None and path is None:
        raise ValueError("either file_id or path must be provided")
    if file_id is not None and not isinstance(file_id, str):
        raise TypeError("file_id must be a string")
    if path is not None:
        path = _validate_file_path(path)
    if page is not None:
        if not isinstance(page, int) or page < 1:
            raise ValueError("page must be a positive integer")

    args: dict[str, Any] = {}
    if file_id is not None:
        args["file_id"] = file_id
    if path is not None:
        args["path"] = path
    if page is not None:
        args["page"] = page
    return await call_external(settings.FILE_VIEWER_URL, args)


@mcp.tool()
async def file_converter(
    source_path: str,
    target_format: str,
) -> dict[str, Any]:
    """Convert files between supported formats through an external conversion API."""
    # Input validation
    source_path = _validate_file_path(source_path)
    target_format = _validate_format(target_format)

    return await call_external(
        settings.FILE_CONVERTER_URL,
        {"source_path": source_path, "target_format": target_format},
    )
