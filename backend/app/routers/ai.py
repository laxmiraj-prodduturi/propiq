import json
from datetime import date, datetime, timedelta, timezone
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
from ..models.lease import Lease
from ..models.property import Property
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


def _fallback_reply(message: str, user: User, db: Session) -> tuple[str, AIActionCard | None]:
    """Local fallback when the AI service is unreachable — queries real DB for key intents."""
    text = message.strip().lower()

    # Lease expiry queries — return real data from DB
    if any(t in text for t in ("expir", "renew", "quarter", "ending soon", "lease end", "upcoming lease")):
        try:
            cutoff = date.today() + timedelta(days=90)
            query = (
                db.query(Lease, Property.name)
                .join(Property, Lease.property_id == Property.id)
                .filter(
                    Lease.status == "active",
                    Lease.end_date <= cutoff,
                    Lease.end_date >= date.today(),
                )
            )
            if user.role == "tenant":
                query = query.filter(Lease.tenant_user_id == user.id)
            elif user.role == "owner":
                query = query.filter(Property.owner_id == user.id)
            else:
                query = query.filter(Property.tenant_id == user.tenant_id)

            rows = query.order_by(Lease.end_date.asc()).all()
            if not rows:
                return ("No active leases are expiring in the next 90 days.", None)
            lines = [
                f"  • {lease.tenant_name} at {prop_name} — ends {lease.end_date}, ${lease.rent_amount:.0f}/mo"
                for lease, prop_name in rows
            ]
            return (
                f"{len(rows)} lease(s) expiring in the next 90 days:\n" + "\n".join(lines),
                None,
            )
        except Exception:
            return ("I can look up expiring leases — please ensure the backend is fully running.", None)

    # Tenant directory — return real names + phones from DB
    if any(t in text for t in ("tenant name", "tenant contact", "tenant phone", "phone number", "list tenant", "all tenant")):
        if user.role not in {"owner", "manager"}:
            return ("You can view your own contact details in your profile.", None)
        try:
            rows = (
                db.query(User.first_name, User.last_name, User.phone, User.email)
                .join(Property, Property.tenant_id == User.tenant_id)
                .filter(User.role == "tenant", User.tenant_id == user.tenant_id)
                .distinct()
                .order_by(User.last_name.asc())
                .all()
            )
            if not rows:
                return ("No tenant records found.", None)
            lines = [f"  • {r.first_name} {r.last_name} — {r.phone or '—'} — {r.email}" for r in rows]
            return (f"{len(rows)} tenant(s):\n" + "\n".join(lines), None)
        except Exception:
            return ("Could not retrieve tenant list right now.", None)

    if "maintenance" in text and user.role in {"owner", "manager"}:
        action_id = f"act_{uuid.uuid4().hex[:10]}"
        return (
            "I identified open maintenance items that may need attention. Review and approve before dispatching vendors.",
            AIActionCard(
                action_id=action_id,
                type="approve_work_order",
                title="Review Open Maintenance",
                description="Authorize review of open work orders before vendor dispatch.",
                status="pending",
            ),
        )
    if "report" in text and user.role == "owner":
        return ("Portfolio summary: check the Dashboard for current occupancy, overdue payments, and open maintenance.", None)
    if "payment" in text or "rent" in text:
        return ("I can review payment status and identify overdue balances. Make sure the AI service is running for full analysis.", None)
    if "lease" in text:
        return ("I can help with lease terms, renewals, and expiry tracking. Try asking 'which leases expire this quarter'.", None)
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
        reply_text, action_card = _fallback_reply(payload.message, current_user, db)
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
# Approve — proxies to AI service which generates confirmation inline
# ---------------------------------------------------------------------------

@router.post("/approve/{action_id}", response_model=AIApprovalResponse)
def approve_action(
    action_id: str,
    approved: bool = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        proxy_response = _proxy_request(
            f"/approve/{action_id}?{parse.urlencode({'approved': approved})}",
            method="POST",
            user=current_user,
        )
        validated = AIApprovalResponse.model_validate(proxy_response)

        # Update DB record
        approval = db.query(AIApproval).filter(AIApproval.action_id == action_id).first()
        if approval:
            approval.status = "approved" if approved else "rejected"
            approval.approver_user_id = current_user.id
            approval.resolved_at = _now()
            # Save follow-up confirmation message into the session
            if validated.follow_up and approval.session_id:
                _save_message(db, session_id=approval.session_id, msg=validated.follow_up)
            db.commit()

        return validated
    except (error.URLError, error.HTTPError, TimeoutError, ValueError) as exc:
        raise HTTPException(status_code=502, detail="AI service unavailable") from exc


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
