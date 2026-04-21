from typing import Any

from app import mcp, settings
from app.utils.external import call_external
from app.utils.validations import (
    _validate_format,
    _validate_query,
)


@mcp.tool()
async def image_generator(
    prompt: str,
    size: str | None = None,
) -> dict[str, Any]:
    """Generate images through an external image generation API."""
    prompt = _validate_query(prompt, max_length=2000)
    if size is not None:
        if not isinstance(size, str):
            raise TypeError("size must be a string")
        valid_sizes = ["small", "medium", "large", "256x256", "512x512", "1024x1024"]
        size = _validate_format(size)
        if size not in valid_sizes:
            raise ValueError(f"size must be one of {valid_sizes}")

    args: dict[str, Any] = {"prompt": prompt}
    if size is not None:
        args["size"] = size
    return await call_external(settings.IMAGE_GENERATOR_URL, args)
