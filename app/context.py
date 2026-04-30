from contextvars import ContextVar
from typing import Any

current_app: ContextVar[Any] = ContextVar("current_app")
