from __future__ import annotations

from operator import add
from typing import Annotated, Any, TypedDict


class AgentState(TypedDict):
    session_id: str
    user_id: str
    role: str
    tenant_id: str
    user_message: str
    intent: str
    retrieved_docs: list[dict[str, Any]]
    structured_context: dict[str, Any]
    tool_calls: Annotated[list[dict[str, Any]], add]   # appended by each node
    proposed_actions: list[dict[str, Any]]              # replaced (set once in plan, cleared in policy_check)
    approval_required: bool
    approval_status: str | None
    final_response: str
    citations: list[str]
    debug_steps: Annotated[list[str], add]              # appended by each node
