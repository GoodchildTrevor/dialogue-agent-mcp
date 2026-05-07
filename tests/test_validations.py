import pytest

from app.utils.validations import (
    _validate_file_path,
    _validate_format,
    _validate_limit,
    _validate_query,
    _validate_user_id,
)


def test_validate_query_trims_whitespace() -> None:
    assert _validate_query("  hello world  ") == "hello world"


def test_validate_query_rejects_invalid_types() -> None:
    with pytest.raises(TypeError):
        _validate_query(123)  # type: ignore[arg-type]


def test_validate_query_rejects_empty_string() -> None:
    with pytest.raises(ValueError):
        _validate_query("   ")


def test_validate_limit_defaults_when_none() -> None:
    assert _validate_limit(None) == 5


def test_validate_limit_constraints() -> None:
    assert _validate_limit(2, default=1, max_val=3) == 2
    assert _validate_limit(100, max_val=10) == 10


def test_validate_limit_invalid_type() -> None:
    with pytest.raises(TypeError):
        _validate_limit("5")  # type: ignore[arg-type]


def test_validate_user_id_rejects_empty() -> None:
    with pytest.raises(ValueError):
        _validate_user_id(" ")


def test_validate_file_path_detects_traversal() -> None:
    with pytest.raises(ValueError):
        _validate_file_path("../../etc/passwd")


def test_validate_format_normalizes() -> None:
    assert _validate_format(" PNG ", valid_formats=["png"]) == "png"


def test_validate_format_rejects_unknown() -> None:
    with pytest.raises(ValueError):
        _validate_format("bmp", valid_formats=["png"])  # type: ignore[arg-type]
