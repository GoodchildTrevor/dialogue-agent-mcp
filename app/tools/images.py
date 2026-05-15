from typing import Any

import httpx
from mcp.types import ImageContent, TextContent

from app import mcp, settings, get_http_client
from app.utils.validations import (
    _validate_format,
    _validate_query,
)


def _image_generation_url() -> str:
    """Get the image generation URL from the settings.
    :return: The image generation URL.
    """
    base_url = settings.IMAGE_BACKEND_URL
    if not base_url or not isinstance(base_url, str):
        raise RuntimeError("IMAGE_BACKEND_URL is not configured")
    return base_url.rstrip("/") + "/v1/images/generations"


@mcp.tool()
async def generate_image(
    prompt: str,
    size: str | None = None,
) -> list[TextContent | ImageContent]:
    """Generate an image from the configured backend service.
    :param prompt: The prompt to generate the image from.
    :param size: The size of the image to generate.
    :return: The generated image.
    """
    prompt = _validate_query(prompt, max_length=2000)

    if size is not None:
        if not isinstance(size, str):
            raise TypeError("size must be a string")
        size = _validate_format(size)
        if size not in settings.IMAGE_VALID_SIZES:
            raise ValueError(f"size must be one of {settings.IMAGE_VALID_SIZES}")
    else:
        size = settings.IMAGE_VALID_SIZES[0]

    http_client = get_http_client()

    url = _image_generation_url()
    body: dict[str, Any] = {
        "prompt": prompt,
        "n": 1,
        "size": size,
        "response_format": "b64_json",
    }

    try:
        response = await http_client.post(url, json=body)
        response.raise_for_status()
    except (httpx.RequestError, httpx.HTTPStatusError) as exc:
        message = (
            f"Unable to reach the image backend at {url}."
            " Please check IMAGE_BACKEND_URL and backend health."
        )
        raise RuntimeError(message) from exc

    payload = response.json()
    data = payload.get("data")
    if not data or not isinstance(data, list) or "b64_json" not in data[0]:
        raise RuntimeError("Image backend returned an unexpected response")

    b64_string = data[0]["b64_json"]

    return [
        TextContent(type="text", text=f"Generated image (size: {size})."),
        ImageContent(type="image", mimeType="image/png", data=b64_string),
    ]
