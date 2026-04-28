from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool

from ..services.llm_factory import TEMP_PRECISE, build_llm

logger = logging.getLogger(__name__)


def run_specialist(
    *,
    name: str,
    system_prompt: str,
    tools: list[BaseTool],
    query: str,
    max_iterations: int = 5,
) -> str:
    """
    Run a specialist mini-agent: LLM with bound tools in a ReAct loop.
    Returns a plain-text summary of findings.
    Falls back to an error string if OpenAI is not configured.
    """
    # Append role context so specialist LLM scopes its answers correctly
    from ..services.agent_tools import _user_ctx
    user = _user_ctx.get()
    role_note = (
        f"\n\nCurrent user role: {user.role}. "
        + {
            "tenant": "Scope all answers to this tenant's own lease, property, and payments only.",
            "manager": "Full portfolio access — answer for all properties in the management org.",
            "owner": "Investment focus — emphasise revenue, occupancy, and portfolio performance.",
        }.get(user.role, "")
        if user else ""
    )

    llm = build_llm(temperature=TEMP_PRECISE, tools=tools)
    if not llm:
        return f"[{name}] OpenAI not configured — cannot run specialist."

    tool_map = {t.name: t for t in tools}
    messages: list[Any] = [
        SystemMessage(content=system_prompt + role_note),
        HumanMessage(content=query),
    ]

    try:
        for _ in range(max_iterations):
            response = llm.invoke(messages)
            messages.append(response)

            if not getattr(response, "tool_calls", None):
                return response.content or f"[{name}] No response generated."

            for tc in response.tool_calls:
                tool_fn = tool_map.get(tc["name"])
                if tool_fn:
                    try:
                        result = tool_fn.invoke(tc["args"])
                    except Exception as exc:
                        result = f"Tool error: {exc}"
                else:
                    result = f"Unknown tool: {tc['name']}"

                messages.append(ToolMessage(content=str(result), tool_call_id=tc["id"]))

        return f"[{name}] Reached max iterations without a final answer."

    except Exception as exc:
        logger.warning("[%s] specialist failed: %s", name, exc)
        return f"[{name}] Error: {exc}"
