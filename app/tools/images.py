import base64
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


def _image_edit_url() -> str:
    """Get the image edit URL from the settings.
    :return: The image edit URL.
    """
    base_url = settings.IMAGE_BACKEND_URL
    if not base_url or not isinstance(base_url, str):
        raise RuntimeError("IMAGE_BACKEND_URL is not configured")
    return base_url.rstrip("/") + "/v1/images/edits"


def _resolve_size(size: str | None) -> str:
    if size is None:
        return settings.IMAGE_VALID_SIZES[0]
    if not isinstance(size, str):
        raise TypeError("size must be a string")
    size = _validate_format(size)
    if size not in settings.IMAGE_VALID_SIZES:
        raise ValueError(f"size must be one of {settings.IMAGE_VALID_SIZES}")
    return size


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
    size = _resolve_size(size)

    http_client = get_http_client()
    url = _image_generation_url()
    body: dict[str, Any] = {
        "model": settings.IMAGE_MODEL,
        "prompt": prompt,
        "n": 1,
        "size": size,
        "response_format": "b64_json",
    }

    try:
        response = await http_client.post(url, json=body)
        response.raise_for_status()
    except httpx.RequestError as exc:
        raise RuntimeError(
            f"Network error reaching image backend at {url}: {exc}"
        ) from exc
    except httpx.HTTPStatusError as exc:
        raise RuntimeError(
            f"Image backend returned HTTP {exc.response.status_code}: {exc.response.text}"
        ) from exc

    payload = response.json()
    data = payload.get("data")
    if not data or not isinstance(data, list) or "b64_json" not in data[0]:
        raise RuntimeError("Image backend returned an unexpected response")

    return [
        TextContent(type="text", text=f"Generated image (size: {size})."),
        ImageContent(type="image", mimeType=settings.IMAGE_MIME_TYPE, data=data[0]["b64_json"]),
    ]


@mcp.tool()
async def edit_image(
    prompt: str,
    image_b64: str,
    mime_type: str = "image/png",
    mask_b64: str | None = None,
    size: str | None = None,
) -> list[TextContent | ImageContent]:
    """Edit an existing image using the configured backend service.
    :param prompt: The instruction describing the desired edit.
    :param image_b64: Base64-encoded image to edit.
    :param mime_type: MIME type of the image (e.g. 'image/png', 'image/webp').
    :param mask_b64: Optional base64-encoded mask (PNG with transparency) defining the edit area.
    :param size: Output image size. Defaults to the first configured valid size.
    :return: The edited image.
    """
    prompt = _validate_query(prompt, max_length=2000)
    size = _resolve_size(size)

    try:
        image_bytes = base64.b64decode(image_b64)
    except Exception as exc:
        raise ValueError("image_b64 is not valid base64") from exc

    ext = mime_type.split("/")[-1]
    files: dict[str, Any] = {
        "image": (f"image.{ext}", image_bytes, mime_type),
        "prompt": (None, prompt),
        "model": (None, settings.IMAGE_MODEL),
        "n": (None, "1"),
        "size": (None, size),
        "response_format": (None, "b64_json"),
    }

    if mask_b64 is not None:
        try:
            mask_bytes = base64.b64decode(mask_b64)
        except Exception as exc:
            raise ValueError("mask_b64 is not valid base64") from exc
        files["mask"] = ("mask.png", mask_bytes, "image/png")

    http_client = get_http_client()
    url = _image_edit_url()

    try:
        response = await http_client.post(url, files=files)
        response.raise_for_status()
    except httpx.RequestError as exc:
        raise RuntimeError(
            f"Network error reaching image backend at {url}: {exc}"
        ) from exc
    except httpx.HTTPStatusError as exc:
        raise RuntimeError(
            f"Image backend returned HTTP {exc.response.status_code}: {exc.response.text}"
        ) from exc

    payload = response.json()
    data = payload.get("data")
    if not data or not isinstance(data, list) or "b64_json" not in data[0]:
        raise RuntimeError("Image backend returned an unexpected response")

    return [
        TextContent(type="text", text=f"Edited image (size: {size})."),
        ImageContent(type="image", mimeType=settings.IMAGE_MIME_TYPE, data=data[0]["b64_json"]),
    ]
