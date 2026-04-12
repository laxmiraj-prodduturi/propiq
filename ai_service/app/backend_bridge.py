from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import sys
from typing import Iterator


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.database import SessionLocal  # type: ignore  # noqa: E402
from backend.app.models.document import Document  # type: ignore  # noqa: E402
from backend.app.models.lease import Lease  # type: ignore  # noqa: E402
from backend.app.models.maintenance import MaintenanceRequest  # type: ignore  # noqa: E402
from backend.app.models.payment import Payment  # type: ignore  # noqa: E402
from backend.app.models.property import Property  # type: ignore  # noqa: E402


@contextmanager
def db_session() -> Iterator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


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


def payments_for_user(*, user_id: str, role: str, tenant_id: str) -> list[Payment]:
    try:
        with db_session() as db:
            query = db.query(Payment).join(Lease, Payment.lease_id == Lease.id).join(Property, Lease.property_id == Property.id)
            if role == "tenant":
                query = query.filter(Lease.tenant_user_id == user_id)
            elif role == "owner":
                query = query.filter(Property.owner_id == user_id)
            else:
                query = query.filter(Property.tenant_id == tenant_id)
            return query.order_by(Payment.due_date.desc()).all()
    except Exception:
        return []


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


def all_documents() -> list[Document]:
    """Fetch all documents without user filtering — used only by the RAG indexer."""
    try:
        with db_session() as db:
            return db.query(Document).order_by(Document.created_at.desc()).all()
    except Exception:
        return []


def documents_for_user(*, user_id: str, role: str, tenant_id: str) -> list[Document]:
    accessible_properties = properties_for_user(user_id=user_id, role=role, tenant_id=tenant_id)
    accessible_names = {property_item.name.lower() for property_item in accessible_properties}
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
