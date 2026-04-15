def _validate_query(query: str, max_length: int = 1000) -> str:
    """Validate and sanitize query input."""
    if not isinstance(query, str):
        raise TypeError("query must be a string")
    if not query.strip():
        raise ValueError("query cannot be empty")
    if len(query) > max_length:
        raise ValueError(f"query exceeds maximum length of {max_length} characters")
    return query.strip()


def _validate_limit(limit: int | None, default: int = 5, max_val: int = 100) -> int:
    """Validate and constrain limit parameter."""
    if limit is None:
        return default
    if not isinstance(limit, int):
        raise TypeError("limit must be an integer")
    if limit < 1:
        raise ValueError("limit must be at least 1")
    return min(limit, max_val)


def _validate_user_id(user_id: str) -> str:
    """Validate user_id input."""
    if not isinstance(user_id, str):
        raise TypeError("user_id must be a string")
    if not user_id.strip():
        raise ValueError("user_id cannot be empty")
    return user_id.strip()


def _validate_file_path(path: str, max_length: int = 2000) -> str:
    """Validate file path input."""
    if not isinstance(path, str):
        raise TypeError("path must be a string")
    if not path.strip():
        raise ValueError("path cannot be empty")
    if len(path) > max_length:
        raise ValueError(f"path exceeds maximum length of {max_length} characters")
    if ".." in path:
        raise ValueError("path traversal detected")
    return path.strip()


def _validate_format(format_str: str, valid_formats: list[str] | None = None) -> str:
    """Validate format input."""
    if not isinstance(format_str, str):
        raise TypeError("format must be a string")
    if not format_str.strip():
        raise ValueError("format cannot be empty")
    format_str = format_str.strip().lower()
    if valid_formats and format_str not in valid_formats:
        raise ValueError(f"invalid format: {format_str}")
    return format_str
