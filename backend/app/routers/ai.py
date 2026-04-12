import json
from datetime import datetime, timezone
from urllib import error, parse, request
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..deps import get_current_user
from ..models.ai_session import AIApproval, AIMessage, AISession
from ..models.user import User
from ..schemas.ai import (
    AIActionCard,
    AIApprovalResponse,
    AIChatHistoryResponse,
    AIChatRequest,
    AIChatResponse,
    AIMessageOut,
    SupportChatRequest,
    SupportChatResponse,
)

router = APIRouter(prefix="/ai", tags=["ai"])
limiter = Limiter(key_func=get_remote_address)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _proxy_headers(user: User) -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "x-user-id": user.id,
        "x-user-role": user.role,
        "x-tenant-id": user.tenant_id,
    }


def _proxy_request(path: str, *, method: str, user: User, payload: dict | None = None):
    url = f"{settings.AI_SERVICE_URL}{path}"
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    proxy_request = request.Request(url, data=body, headers=_proxy_headers(user), method=method)
    with request.urlopen(proxy_request, timeout=settings.AI_SERVICE_TIMEOUT_SECONDS) as response:
        return json.loads(response.read().decode("utf-8"))


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def _get_or_create_session(db: Session, *, user: User, session_id: str) -> AISession:
    session = db.query(AISession).filter(AISession.session_id == session_id).first()
    if not session:
        session = AISession(
            id=f"s{uuid.uuid4().hex[:8]}",
            tenant_id=user.tenant_id,
            user_id=user.id,
            session_id=session_id,
        )
        db.add(session)
        db.flush()
    else:
        session.last_active_at = _now()
    return session


def _save_message(db: Session, *, session_id: str, msg: AIMessageOut) -> None:
    action_card_json = None
    if msg.action_card:
        action_card_json = json.dumps(msg.action_card.model_dump())
    db.add(AIMessage(
        id=msg.id,
        session_id=session_id,
        role=msg.role,
        content=msg.content,
        action_card_json=action_card_json,
        created_at=msg.created_at,
    ))


def _load_messages(db: Session, session_id: str) -> list[AIMessageOut]:
    rows = (
        db.query(AIMessage)
        .filter(AIMessage.session_id == session_id)
        .order_by(AIMessage.created_at.asc())
        .all()
    )
    result = []
    for row in rows:
        action_card = None
        if row.action_card_json:
            try:
                action_card = AIActionCard(**json.loads(row.action_card_json))
            except Exception:
                pass
        result.append(AIMessageOut(
            id=row.id,
            role=row.role,
            content=row.content,
            created_at=row.created_at,
            action_card=action_card,
        ))
    return result


def _fallback_reply(message: str, user: User) -> tuple[str, AIActionCard | None]:
    """Local fallback when the AI service is unreachable."""
    text = message.strip().lower()
    if "maintenance" in text and user.role in {"owner", "manager"}:
        action_id = f"act_{uuid.uuid4().hex[:10]}"
        return (
            "I prioritized the open work orders and identified one item that should be approved before execution.",
            AIActionCard(
                action_id=action_id,
                type="approve_work_order",
                title="Approve Emergency HVAC Dispatch",
                description="Authorize vendor dispatch for Oak Ridge House at an estimated cost of $850.",
                status="pending",
            ),
        )
    if "report" in text and user.role == "owner":
        return ("Portfolio summary prepared: occupancy is stable, one payment is overdue, and one maintenance item requires approval.", None)
    if "lease" in text:
        return ("I can help with lease terms, renewals, and document questions.", None)
    if "payment" in text or "rent" in text:
        return ("I can review payment status, identify overdue balances, and explain next steps.", None)
    return ("I can help with maintenance triage, lease questions, payment follow-up, and owner reporting.", None)


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------

@router.post("/chat", response_model=AIChatResponse)
@limiter.limit("20/hour")
def chat(
    request: Request,
    payload: AIChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session_id = payload.session_id or f"session_{uuid.uuid4().hex[:10]}"

    user_msg = AIMessageOut(
        id=f"msg_{uuid.uuid4().hex[:10]}",
        role="user",
        content=payload.message,
        created_at=_now(),
    )

    # Try AI service
    assistant_msg: AIMessageOut | None = None
    try:
        proxy_response = _proxy_request("/chat", method="POST", user=current_user, payload=payload.model_dump())
        validated = AIChatResponse.model_validate(proxy_response)
        session_id = validated.session_id
        assistant_msg = validated.message
    except (error.URLError, error.HTTPError, TimeoutError, ValueError):
        pass

    if assistant_msg is None:
        reply_text, action_card = _fallback_reply(payload.message, current_user)
        assistant_msg = AIMessageOut(
            id=f"msg_{uuid.uuid4().hex[:10]}",
            role="assistant",
            content=reply_text,
            created_at=_now(),
            action_card=action_card,
        )

    # Persist to DB
    _get_or_create_session(db, user=current_user, session_id=session_id)
    _save_message(db, session_id=session_id, msg=user_msg)
    _save_message(db, session_id=session_id, msg=assistant_msg)

    # Persist approval request if action card present
    if assistant_msg.action_card:
        card = assistant_msg.action_card
        db.add(AIApproval(
            id=f"apr{uuid.uuid4().hex[:8]}",
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            session_id=session_id,
            action_id=card.action_id,
            action_type=card.type,
            action_payload_json=json.dumps(card.model_dump()),
            status="pending",
        ))

    db.commit()
    return AIChatResponse(session_id=session_id, message=assistant_msg)


# ---------------------------------------------------------------------------
# Chat history
# ---------------------------------------------------------------------------

@router.get("/chat/history", response_model=AIChatHistoryResponse)
def chat_history(
    session_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Try AI service first (it has LangGraph context)
    query = f"?{parse.urlencode({'session_id': session_id})}" if session_id else ""
    try:
        proxy_response = _proxy_request(f"/chat/history{query}", method="GET", user=current_user)
        return AIChatHistoryResponse.model_validate(proxy_response)
    except (error.URLError, error.HTTPError, TimeoutError, ValueError):
        pass

    # Fall back to DB
    resolved_session_id = session_id
    if not resolved_session_id:
        latest = (
            db.query(AISession)
            .filter(AISession.user_id == current_user.id)
            .order_by(AISession.last_active_at.desc())
            .first()
        )
        resolved_session_id = latest.session_id if latest else None

    if not resolved_session_id:
        return AIChatHistoryResponse(session_id=None, messages=[])

    session = db.query(AISession).filter(
        AISession.session_id == resolved_session_id,
        AISession.user_id == current_user.id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return AIChatHistoryResponse(
        session_id=resolved_session_id,
        messages=_load_messages(db, resolved_session_id),
    )


# ---------------------------------------------------------------------------
# Resume — continue the paused LangGraph
# ---------------------------------------------------------------------------

@router.post("/resume/{action_id}", response_model=AIChatResponse)
def resume_action(
    action_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    approval = db.query(AIApproval).filter(
        AIApproval.action_id == action_id,
        AIApproval.user_id == current_user.user_id if hasattr(current_user, "user_id") else AIApproval.user_id == current_user.id,
    ).first()
    # Lookup by user_id
    approval = db.query(AIApproval).filter(AIApproval.action_id == action_id).first()
    if not approval or approval.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Approval request not found")

    if approval.status == "pending":
        raise HTTPException(status_code=409, detail="Action has not been approved or rejected yet")

    try:
        proxy_response = _proxy_request(f"/resume/{action_id}", method="POST", user=current_user)
        validated = AIChatResponse.model_validate(proxy_response)
        # Persist the follow-up message
        _save_message(db, session_id=approval.session_id, msg=validated.message)
        db.commit()
        return validated
    except (error.URLError, error.HTTPError, TimeoutError, ValueError) as exc:
        raise HTTPException(status_code=502, detail="AI service unavailable") from exc


# ---------------------------------------------------------------------------
# Approve
# ---------------------------------------------------------------------------

@router.post("/approve/{action_id}", response_model=AIApprovalResponse)
def approve_action(
    action_id: str,
    approved: bool = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Try AI service first
    try:
        proxy_response = _proxy_request(
            f"/approve/{action_id}?{parse.urlencode({'approved': approved})}",
            method="POST",
            user=current_user,
        )
        # Also update DB record
        approval = db.query(AIApproval).filter(AIApproval.action_id == action_id).first()
        if approval:
            approval.status = "approved" if approved else "rejected"
            approval.approver_user_id = current_user.id
            approval.resolved_at = _now()
            db.commit()
        return AIApprovalResponse.model_validate(proxy_response)
    except (error.URLError, error.HTTPError, TimeoutError, ValueError):
        pass

    # Fallback: update DB only
    approval = db.query(AIApproval).filter(AIApproval.action_id == action_id).first()
    if not approval or approval.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Approval request not found")
    if current_user.role not in {"owner", "manager"}:
        raise HTTPException(status_code=403, detail="Approval not permitted for this role")

    approval.status = "approved" if approved else "rejected"
    approval.approver_user_id = current_user.id
    approval.resolved_at = _now()
    db.commit()

    message = "Action approved." if approved else "Action rejected."
    return AIApprovalResponse(action_id=action_id, status=approval.status, message=message)


# ---------------------------------------------------------------------------
# Support chat — general LLM Q&A, no property data
# ---------------------------------------------------------------------------

@router.post("/support/chat", response_model=SupportChatResponse)
def support_chat(
    payload: SupportChatRequest,
    current_user: User = Depends(get_current_user),
):
    try:
        proxy_response = _proxy_request(
            "/support/chat",
            method="POST",
            user=current_user,
            payload=payload.model_dump(),
        )
        return SupportChatResponse.model_validate(proxy_response)
    except (error.URLError, error.HTTPError, TimeoutError, ValueError):
        pass

    # Local fallback — keyword-based replies when AI service is down
    text = payload.message.strip().lower()
    if any(t in text for t in ("payment", "rent", "pay", "due")):
        reply = "You can view and make payments in the Payments section. For specific payment status, use the main AI Assistant."
    elif any(t in text for t in ("maintenance", "repair", "issue", "broken")):
        reply = "Submit maintenance requests in the Maintenance section. You can track request status there too."
    elif any(t in text for t in ("lease", "agreement", "contract")):
        reply = "Your lease details are available in the Leases section. The AI Assistant can answer specific lease questions."
    elif any(t in text for t in ("document", "upload", "file")):
        reply = "Documents can be uploaded and viewed in the Documents section."
    else:
        reply = "I'm here to help with platform navigation and general property questions. For account-specific data, use the main AI Assistant."
    return SupportChatResponse(response=reply)
