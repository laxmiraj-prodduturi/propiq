from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, Header, HTTPException, Query

from .logging_config import configure_logging, get_logger
configure_logging()
logger = get_logger("main")

from .config import settings
from .graph import build_assistant_message, generate_approval_confirmation, run_agent_turn
from .schemas import (
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
from .backend_bridge import messages_for_session as _db_messages
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

    # Guard: if this user already has a pending approval, don't re-run the agent.
    # Typing "yes" / "approve" in the chat box while a card is waiting creates a loop.
    _AFFIRMATIONS = {"yes", "yeah", "yep", "ok", "okay", "approve", "confirm", "go ahead", "sure", "do it"}
    pending_action_id = next(
        (aid for aid, info in approval_store.items()
         if info.get("user_id") == user.user_id and info.get("status") == "pending"),
        None,
    )
    if pending_action_id and payload.message.strip().lower() in _AFFIRMATIONS:
        redirect = AIMessageOut(
            id=f"msg_{uuid.uuid4().hex[:10]}",
            role="assistant",
            content=(
                "It looks like there's already an action pending your approval above. "
                "Please click the **Approve** or **Reject** button on the action card to proceed — "
                "typing here won't trigger the approval."
            ),
            created_at=_now(),
        )
        session_store[session_id].extend([user_message, redirect])
        session_owner[session_id] = user.user_id
        user_last_session[user.user_id] = session_id
        return AIChatResponse(session_id=session_id, message=redirect)
    # Build conversation history so the agent maintains context across turns.
    # If the in-memory store is empty (e.g. after a restart), seed it from MySQL.
    from langchain_core.messages import AIMessage as LCAIMessage, HumanMessage as LCHumanMessage
    if session_id not in session_store or not session_store[session_id]:
        for row in _db_messages(session_id=session_id, limit=20):
            session_store[session_id].append(
                AIMessageOut(
                    id=row["id"],
                    role=row["role"],
                    content=row["content"],
                    created_at=row["created_at"],
                )
            )
        if session_store[session_id]:
            session_owner[session_id] = user.user_id
            user_last_session[user.user_id] = session_id

    history = []
    for msg in session_store.get(session_id, [])[-20:]:
        if msg.role == "user" and msg.content:
            history.append(LCHumanMessage(content=msg.content))
        elif msg.role == "assistant" and msg.content:
            history.append(LCAIMessage(content=msg.content))

    logger.info("Chat | user=%s role=%s session=%s msg=%.120s", user.user_id, user.role, session_id, payload.message)
    state, _ = run_agent_turn(
        session_id=session_id,
        message=payload.message,
        user=user,
        turn_id=turn_id,
        history=history,
    )
    assistant_message = build_assistant_message(state)
    logger.info("Chat | reply=%.200s action_card=%s", assistant_message.content, bool(assistant_message.action_card))

    # If agent proposed an action, store everything /approve needs to generate confirmation
    if assistant_message.action_card:
        action_id = assistant_message.action_card.action_id
        proposed = state.get("proposed_actions", [])
        approval_store[action_id] = {
            "status": "pending",
            "user_id": user.user_id,
            "session_id": session_id,
            "action_info": proposed[0] if proposed else {
                "action_id": action_id,
                "title": assistant_message.action_card.title,
                "description": assistant_message.action_card.description,
            },
        }

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
        # Not in memory — try MySQL before giving up
        db_msgs = _db_messages(session_id=resolved_session_id, limit=40)
        if not db_msgs:
            raise HTTPException(status_code=404, detail="Session not found")
        messages = [
            AIMessageOut(id=r["id"], role=r["role"], content=r["content"], created_at=r["created_at"])
            for r in db_msgs
        ]
        return AIChatHistoryResponse(session_id=resolved_session_id, messages=messages)

    return AIChatHistoryResponse(
        session_id=resolved_session_id,
        messages=session_store.get(resolved_session_id, []),
    )


# ---------------------------------------------------------------------------
# Approve — generates confirmation inline; no separate /resume needed
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

    approval_status = "approved" if approved else "rejected"
    logger.info("Approve | action=%s user=%s status=%s", action_id, user.user_id, approval_status)

    # Generate confirmation message directly — no graph resumption needed
    action_info = approval.get("action_info", {})
    follow_up_content = generate_approval_confirmation(
        action=action_info,
        approval_status=approval_status,
        user_id=user.user_id,
        role=user.role,
        tenant_id=user.tenant_id,
    )
    follow_up = AIMessageOut(
        id=f"msg_{uuid.uuid4().hex[:10]}",
        role="assistant",
        content=follow_up_content,
        created_at=_now(),
    )

    # Persist the confirmation into the session history
    session_id = approval.get("session_id", "")
    if session_id:
        session_store[session_id].append(follow_up)

    # Clean up — action is consumed
    approval_store.pop(action_id, None)
    action_thread_map.pop(action_id, None)

    return AIApprovalResponse(
        action_id=action_id,
        status=approval_status,
        message="Action processed.",
        follow_up=follow_up,
    )


# ---------------------------------------------------------------------------
# Support chat — lightweight LLM Q&A, no user context or RAG required
# ---------------------------------------------------------------------------

@app.post("/support/chat", response_model=SupportChatResponse)
def support_chat(payload: SupportChatRequest):
    history = [{"role": m.role, "content": m.content} for m in payload.history]
    response = support_answer(payload.message, history)
    return SupportChatResponse(response=response)
