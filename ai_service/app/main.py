from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, Header, HTTPException, Query

from .config import settings
from .graph import build_assistant_message, resume_agent_turn, run_agent_turn
from .schemas import (
    AIActionCard,
    AIApprovalResponse,
    AIChatHistoryResponse,
    AIChatRequest,
    AIChatResponse,
    AIMessageOut,
    SupportChatRequest,
    SupportChatResponse,
    UserContext,
)
from .services.openai_client import support_answer
from .store import (
    action_thread_map,
    approval_store,
    session_owner,
    session_store,
    user_last_session,
)

app = FastAPI(title=settings.APP_NAME)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _require_user_context(
    x_user_id: str | None,
    x_user_role: str | None,
    x_tenant_id: str | None,
) -> UserContext:
    if not x_user_id or not x_user_role or not x_tenant_id:
        raise HTTPException(status_code=400, detail="Missing AI user context headers")
    return UserContext(user_id=x_user_id, role=x_user_role, tenant_id=x_tenant_id)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health")
def health_check():
    try:
        import langgraph  # type: ignore  # noqa: F401
        langgraph_ready = True
    except Exception:
        langgraph_ready = False

    return {
        "status": "ok",
        "demo_mode": settings.DEMO_MODE,
        "openai_configured": bool(settings.OPENAI_API_KEY),
        "langgraph_installed": langgraph_ready,
    }


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------

@app.post("/chat", response_model=AIChatResponse)
def chat(
    payload: AIChatRequest,
    x_user_id: str | None = Header(default=None),
    x_user_role: str | None = Header(default=None),
    x_tenant_id: str | None = Header(default=None),
):
    user = _require_user_context(x_user_id, x_user_role, x_tenant_id)
    session_id = payload.session_id or f"session_{uuid.uuid4().hex[:10]}"
    turn_id = str(uuid.uuid4())  # unique per message turn for LangGraph threading

    user_message = AIMessageOut(
        id=f"msg_{uuid.uuid4().hex[:10]}",
        role="user",
        content=payload.message,
        created_at=_now(),
    )

    state, was_interrupted = run_agent_turn(
        session_id=session_id,
        message=payload.message,
        user=user,
        turn_id=turn_id,
    )
    assistant_message = build_assistant_message(state)

    # If the graph is waiting for approval, persist the turn_id so /resume can continue it
    if was_interrupted and assistant_message.action_card:
        action_id = assistant_message.action_card.action_id
        approval_store[action_id] = {
            "status": "pending",
            "user_id": user.user_id,
            "action_card": assistant_message.action_card,
        }
        action_thread_map[action_id] = turn_id

    session_owner[session_id] = user.user_id
    user_last_session[user.user_id] = session_id
    session_store[session_id].extend([user_message, assistant_message])

    return AIChatResponse(session_id=session_id, message=assistant_message)


# ---------------------------------------------------------------------------
# Chat history
# ---------------------------------------------------------------------------

@app.get("/chat/history", response_model=AIChatHistoryResponse)
def chat_history(
    session_id: str | None = Query(default=None),
    x_user_id: str | None = Header(default=None),
    x_user_role: str | None = Header(default=None),
    x_tenant_id: str | None = Header(default=None),
):
    user = _require_user_context(x_user_id, x_user_role, x_tenant_id)
    resolved_session_id = session_id or user_last_session.get(user.user_id)
    if not resolved_session_id:
        return AIChatHistoryResponse(session_id=None, messages=[])

    if session_owner.get(resolved_session_id) != user.user_id:
        raise HTTPException(status_code=404, detail="Session not found")

    return AIChatHistoryResponse(
        session_id=resolved_session_id,
        messages=session_store.get(resolved_session_id, []),
    )


# ---------------------------------------------------------------------------
# Approve — record the decision (frontend renders the status update)
# ---------------------------------------------------------------------------

@app.post("/approve/{action_id}", response_model=AIApprovalResponse)
def approve_action(
    action_id: str,
    approved: bool = Query(...),
    x_user_id: str | None = Header(default=None),
    x_user_role: str | None = Header(default=None),
    x_tenant_id: str | None = Header(default=None),
):
    user = _require_user_context(x_user_id, x_user_role, x_tenant_id)
    approval = approval_store.get(action_id)
    if approval is None or approval.get("user_id") != user.user_id:
        raise HTTPException(status_code=404, detail="Approval request not found")

    if user.role not in {"owner", "manager"}:
        raise HTTPException(status_code=403, detail="Approval not permitted for this role")

    status = "approved" if approved else "rejected"
    approval["status"] = status
    action_card = approval.get("action_card")
    if isinstance(action_card, AIActionCard):
        approval["action_card"] = action_card.model_copy(update={"status": status})

    message = "Action approved. Call /resume/{action_id} to receive the follow-up." if approved else "Action rejected."
    return AIApprovalResponse(action_id=action_id, status=status, message=message)


# ---------------------------------------------------------------------------
# Resume — continue the paused LangGraph and return the follow-up message
# ---------------------------------------------------------------------------

@app.post("/resume/{action_id}", response_model=AIChatResponse)
def resume_action(
    action_id: str,
    x_user_id: str | None = Header(default=None),
    x_user_role: str | None = Header(default=None),
    x_tenant_id: str | None = Header(default=None),
):
    user = _require_user_context(x_user_id, x_user_role, x_tenant_id)

    approval = approval_store.get(action_id)
    if approval is None or approval.get("user_id") != user.user_id:
        raise HTTPException(status_code=404, detail="Approval request not found")

    approval_status = str(approval.get("status", "pending"))
    if approval_status == "pending":
        raise HTTPException(status_code=409, detail="Action has not been approved or rejected yet")

    turn_id = action_thread_map.get(action_id)
    if not turn_id:
        raise HTTPException(status_code=404, detail="No paused graph found for this action")

    state = resume_agent_turn(turn_id=turn_id, approval_status=approval_status)
    follow_up = AIMessageOut(
        id=f"msg_{uuid.uuid4().hex[:10]}",
        role="assistant",
        content=state.get("final_response", ""),
        created_at=_now(),
    )

    # Store in the original session so history reflects the full conversation
    session_id = state.get("session_id", "")
    if session_id:
        session_store[session_id].append(follow_up)

    # Clean up — action is now consumed
    action_thread_map.pop(action_id, None)

    return AIChatResponse(session_id=session_id, message=follow_up)


# ---------------------------------------------------------------------------
# Support chat — lightweight LLM Q&A, no user context or RAG required
# ---------------------------------------------------------------------------

@app.post("/support/chat", response_model=SupportChatResponse)
def support_chat(payload: SupportChatRequest):
    history = [{"role": m.role, "content": m.content} for m in payload.history]
    response = support_answer(payload.message, history)
    return SupportChatResponse(response=response)
