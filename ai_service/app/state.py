from __future__ import annotations

from operator import add
from typing import Annotated

from langgraph.graph import MessagesState


class AgentState(MessagesState):
    # MessagesState provides: messages: Annotated[list[AnyMessage], add_messages]
    session_id: str
    user_id: str
    role: str
    tenant_id: str
    citations: Annotated[list[str], add]      # accumulated from search_documents calls
    approval_required: bool
    approval_status: str | None
    proposed_actions: list[dict]
    debug_steps: Annotated[list[str], add]    # appended by each node
