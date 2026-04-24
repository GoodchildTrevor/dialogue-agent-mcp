from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger(__name__)

# Cosine distance threshold — matches above this value are considered too distant
# and are excluded from the injected context. Tune based on your embedding model.
DISTANCE_THRESHOLD: float = 0.45


def build_history_section(matches: list[dict[str, Any]]) -> str:
    """Convert search_history matches into a '## Relevant past context' block.

    Returns an empty string when no matches pass the distance threshold,
    so callers can safely check ``if history_section:`` before injecting.

    Args:
        matches: List of match dicts as returned by the ``search_history`` MCP tool.
                 Each dict must contain at least ``role``, ``content``, and ``distance``.
                 ``created_at`` (ISO-8601 string) is optional but rendered when present.

    Returns:
        A formatted markdown string starting with ``## Relevant past context``,
        or an empty string if there are no relevant matches.
    """
    if not matches:
        return ""

    filtered = [
        m for m in matches
        if isinstance(m.get("distance"), (int, float))
        and m["distance"] <= DISTANCE_THRESHOLD
    ]

    if not filtered:
        log.debug(
            "search_history returned %d match(es) but all exceeded distance threshold %.2f",
            len(matches),
            DISTANCE_THRESHOLD,
        )
        return ""

    lines: list[str] = ["## Relevant past context", ""]
    for i, m in enumerate(filtered, start=1):
        role = str(m.get("role") or "unknown").capitalize()
        content = str(m.get("content") or "").strip()
        created_at = m.get("created_at") or ""
        date_suffix = f", {created_at[:10]}" if created_at else ""
        lines.append(f"{i}. [{role}{date_suffix}]: {content}")

    return "\n".join(lines)


def inject_history_into_prompt(base_prompt: str, matches: list[dict[str, Any]]) -> str:
    """Return *base_prompt* with the history section appended when relevant.

    This is the single entry-point intended to be called from the orchestrator
    node at the start of every turn, right after ``search_history`` resolves.

    Example usage in the orchestrator node::

        try:
            result = await call_mcp_tool("search_history", query=user_message,
                                         user_id=user_id, limit=5)
            matches = result.get("matches", [])
        except Exception as exc:
            log.warning("search_history unavailable, skipping RAG loop: %s", exc)
            matches = []

        system_prompt = inject_history_into_prompt(base_prompt, matches)

    Args:
        base_prompt: The orchestrator's base system prompt string.
        matches: List of match dicts from ``search_history``. Pass ``[]`` on error.

    Returns:
        ``base_prompt`` unchanged when no relevant history exists,
        otherwise ``base_prompt + "\\n\\n" + history_section``.
    """
    history_section = build_history_section(matches)
    if not history_section:
        return base_prompt
    return f"{base_prompt}\n\n{history_section}"
