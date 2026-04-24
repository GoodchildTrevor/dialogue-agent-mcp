"""Reference implementation of an orchestrator node that completes the RAG loop.

This file is an *example* — copy the pattern into your actual orchestrator.
It is NOT imported anywhere in the MCP server itself.

Acceptance criteria covered
----------------------------
- Orchestrator system prompt includes ``## Relevant past context`` section
  when history matches are found.
- History lookup is skipped gracefully if ``search_history`` tool is unavailable.
- A user asking a question similar to a past resolved query receives the
  previous answer as context.
"""
from __future__ import annotations

import logging
from typing import Any, Callable, Awaitable

from app.utils.history_context import inject_history_into_prompt

log = logging.getLogger(__name__)

DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful assistant. Answer clearly and concisely."
)


async def orchestrator_node(
    state: dict[str, Any],
    call_mcp_tool: Callable[..., Awaitable[dict[str, Any]]],
    available_tools: set[str],
    llm_chat: Callable[..., Awaitable[dict[str, Any]]],
) -> dict[str, Any]:
    """Orchestrator node that injects semantic history into the system prompt.

    Args:
        state: Conversation state dict. Expected keys:
               - ``messages``  — list of {role, content} dicts (last is latest user msg)
               - ``user_id``   — string user identifier for history lookup
               - ``system_prompt`` (optional) — overrides DEFAULT_SYSTEM_PROMPT
        call_mcp_tool: Async callable that invokes an MCP tool by name.
        available_tools: Set of tool names currently registered/reachable.
        llm_chat: Async callable that calls the LLM with a messages list.

    Returns:
        Updated state with the assistant reply appended to ``messages``.
    """
    messages: list[dict] = state["messages"]
    user_id: str = state["user_id"]
    user_message: str = messages[-1]["content"]
    base_prompt: str = state.get("system_prompt", DEFAULT_SYSTEM_PROMPT)

    # ── Step 1: RAG loop — always attempted, gracefully skipped on failure ──
    matches: list[dict[str, Any]] = []
    if "search_history" in available_tools:
        try:
            result = await call_mcp_tool(
                "search_history",
                query=user_message,
                user_id=user_id,
                limit=5,
            )
            matches = result.get("matches", [])
        except Exception as exc:
            log.warning(
                "search_history unavailable, skipping RAG history injection: %s", exc
            )
    else:
        log.debug("search_history tool not registered, skipping RAG loop")

    # ── Step 2: Inject ## Relevant past context when matches pass threshold ─
    # inject_history_into_prompt returns base_prompt unchanged if no relevant matches.
    system_prompt = inject_history_into_prompt(base_prompt, matches)

    if system_prompt != base_prompt:
        log.debug("Injected %d history match(es) into system prompt", len(matches))

    # ── Step 3: Call LLM with enriched system prompt ────────────────────────
    llm_messages = [{"role": "system", "content": system_prompt}] + messages
    response = await llm_chat(messages=llm_messages)

    return {
        **state,
        "messages": messages + [response],
    }
