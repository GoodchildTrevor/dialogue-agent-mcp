# Import all tool modules so their @mcp.tool() decorators
# are executed and tools are registered on the shared mcp instance.
from app.tools import file_handlers, images, searchers  # noqa: F401
