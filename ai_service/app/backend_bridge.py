from __future__ import annotations

import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
import sys
from typing import Iterator


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.database import SessionLocal  # type: ignore  # noqa: E402
from backend.app.models.ai_session import AIMessage as DBMessage  # type: ignore  # noqa: E402
from backend.app.models.document import Document  # type: ignore  # noqa: E402
from backend.app.models.lease import Lease  # type: ignore  # noqa: E402
from backend.app.models.maintenance import MaintenanceRequest  # type: ignore  # noqa: E402
from backend.app.models.notification import Notification  # type: ignore  # noqa: E402
from backend.app.models.payment import Payment  # type: ignore  # noqa: E402
from backend.app.models.property import Property  # type: ignore  # noqa: E402
from backend.app.models.user import User  # type: ignore  # noqa: E402
from backend.app.models.vendor import Vendor  # type: ignore  # noqa: E402


@contextmanager
def db_session() -> Iterator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Properties
# ---------------------------------------------------------------------------

def properties_for_user(*, user_id: str, role: str, tenant_id: str) -> list[Property]:
    try:
        with db_session() as db:
            query = db.query(Property).filter(Property.property_type == "residential")
            if role == "owner":
                query = query.filter(Property.owner_id == user_id)
            elif role == "manager":
                query = query.filter(Property.tenant_id == tenant_id)
            else:
                tenant_property_ids = [
                    lease.property_id
                    for lease in db.query(Lease).filter(Lease.tenant_user_id == user_id, Lease.status == "active").all()
                ]
                if not tenant_property_ids:
                    return []
                query = query.filter(Property.id.in_(tenant_property_ids))
            return query.order_by(Property.address.asc()).all()
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Leases
# ---------------------------------------------------------------------------

def leases_for_user(*, user_id: str, role: str, tenant_id: str) -> list[Lease]:
    try:
        with db_session() as db:
            query = db.query(Lease).join(Property, Lease.property_id == Property.id)
            if role == "tenant":
                query = query.filter(Lease.tenant_user_id == user_id)
            elif role == "owner":
                query = query.filter(Property.owner_id == user_id)
            else:
                query = query.filter(Property.tenant_id == tenant_id)
            return query.order_by(Lease.start_date.desc()).all()
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Payments
# ---------------------------------------------------------------------------

def payments_for_user(*, user_id: str, role: str, tenant_id: str) -> list[Payment]:
    try:
        with db_session() as db:
            query = (
                db.query(Payment)
                .join(Lease, Payment.lease_id == Lease.id)
                .join(Property, Lease.property_id == Property.id)
            )
            if role == "tenant":
                query = query.filter(Lease.tenant_user_id == user_id)
            elif role == "owner":
                query = query.filter(Property.owner_id == user_id)
            else:
                query = query.filter(Property.tenant_id == tenant_id)
            return query.order_by(Payment.due_date.desc()).all()
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Maintenance
# ---------------------------------------------------------------------------

def maintenance_for_user(*, user_id: str, role: str, tenant_id: str) -> list[MaintenanceRequest]:
    try:
        with db_session() as db:
            query = db.query(MaintenanceRequest).join(Property, MaintenanceRequest.property_id == Property.id)
            if role == "tenant":
                query = query.filter(MaintenanceRequest.tenant_user_id == user_id)
            elif role == "owner":
                query = query.filter(Property.owner_id == user_id)
            else:
                query = query.filter(Property.tenant_id == tenant_id)
            return query.order_by(MaintenanceRequest.created_at.desc()).all()
    except Exception:
        return []


def create_work_order(
    *,
    property_id: str,
    tenant_user_id: str,
    property_name: str,
    tenant_name: str,
    category: str,
    description: str,
    urgency: str,
    assigned_vendor: str = "",
    estimated_cost: float = 0.0,
) -> str:
    """Insert a new maintenance work order and return its ID."""
    try:
        with db_session() as db:
            work_order = MaintenanceRequest(
                id=f"mr_{uuid.uuid4().hex[:10]}",
                property_id=property_id,
                tenant_user_id=tenant_user_id,
                property_name=property_name,
                tenant_name=tenant_name,
                category=category,
                description=description,
                urgency=urgency,
                status="open",
                assigned_vendor=assigned_vendor,
                estimated_cost=estimated_cost,
            )
            db.add(work_order)
            db.commit()
            return work_order.id
    except Exception as exc:
        return f"error: {exc}"


# ---------------------------------------------------------------------------
# Vendors
# ---------------------------------------------------------------------------

def vendors_for_tenant(*, tenant_id: str, trade: str | None = None) -> list[Vendor]:
    try:
        with db_session() as db:
            query = db.query(Vendor).filter(Vendor.tenant_id == tenant_id, Vendor.is_active == True)
            if trade:
                query = query.filter(Vendor.trade == trade)
            return query.order_by(Vendor.rating.desc()).all()
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Tenants
# ---------------------------------------------------------------------------

def tenants_for_user(*, user_id: str, role: str, tenant_id: str) -> list[User]:
    try:
        with db_session() as db:
            if role == "tenant":
                user = db.query(User).filter(User.id == user_id).first()
                return [user] if user else []
            if role == "manager":
                return (
                    db.query(User)
                    .filter(User.tenant_id == tenant_id, User.role == "tenant")
                    .order_by(User.last_name.asc())
                    .all()
                )
            owner_property_ids = [
                p.id for p in db.query(Property).filter(Property.owner_id == user_id).all()
            ]
            if not owner_property_ids:
                return []
            tenant_user_ids = [
                lease.tenant_user_id
                for lease in db.query(Lease)
                .filter(Lease.property_id.in_(owner_property_ids), Lease.status == "active")
                .all()
            ]
            if not tenant_user_ids:
                return []
            return (
                db.query(User)
                .filter(User.id.in_(tenant_user_ids))
                .order_by(User.last_name.asc())
                .all()
            )
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------

def send_notification(*, user_id: str, type: str, title: str, body: str) -> str:
    """Persist a notification to the DB and return its ID."""
    try:
        with db_session() as db:
            notif = Notification(
                id=f"n_{uuid.uuid4().hex[:10]}",
                user_id=user_id,
                type=type,
                title=title,
                body=body,
                is_read=False,
            )
            db.add(notif)
            db.commit()
            return notif.id
    except Exception as exc:
        return f"error: {exc}"


def notifications_for_user(*, user_id: str, limit: int = 20) -> list[Notification]:
    try:
        with db_session() as db:
            return (
                db.query(Notification)
                .filter(Notification.user_id == user_id)
                .order_by(Notification.created_at.desc())
                .limit(limit)
                .all()
            )
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------

def all_documents() -> list[Document]:
    try:
        with db_session() as db:
            return db.query(Document).order_by(Document.created_at.desc()).all()
    except Exception:
        return []


def messages_for_session(*, session_id: str, limit: int = 20) -> list[dict]:
    """Return the last N messages for a session from MySQL, ordered oldest-first."""
    try:
        with db_session() as db:
            rows = (
                db.query(DBMessage)
                .filter(DBMessage.session_id == session_id)
                .order_by(DBMessage.created_at.asc())
                .limit(limit)
                .all()
            )
            return [
                {"id": r.id, "role": r.role, "content": r.content, "created_at": r.created_at}
                for r in rows
                if r.content
            ]
    except Exception:
        return []


def documents_for_user(*, user_id: str, role: str, tenant_id: str) -> list[Document]:
    accessible_properties = properties_for_user(user_id=user_id, role=role, tenant_id=tenant_id)
    accessible_names = {p.name.lower() for p in accessible_properties}
    try:
        with db_session() as db:
            docs = db.query(Document).order_by(Document.created_at.desc()).all()
            if role != "tenant":
                return docs
            filtered: list[Document] = []
            for doc in docs:
                related = (doc.related_entity or "").lower()
                if "all homes" in related or any(name in related for name in accessible_names):
                    filtered.append(doc)
            return filtered
    except Exception:
        return []
