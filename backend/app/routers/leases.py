import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..deps import get_current_user, require_roles, require_same_tenant
from ..models.user import User
from ..models.lease import Lease
from ..models.property import Property
from ..schemas.lease import LeaseOut, LeaseCreate, LeaseRenew

router = APIRouter(prefix="/leases", tags=["leases"])

def _enrich_lease(lease: Lease, db: Session) -> LeaseOut:
    out = LeaseOut.model_validate(lease)
    prop = db.query(Property).filter(Property.id == lease.property_id).first()
    if prop:
        out.property_name = prop.name
    return out


@router.get("", response_model=List[LeaseOut])
def list_leases(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role == "tenant":
        leases = db.query(Lease).filter(Lease.tenant_user_id == current_user.id).all()
    else:
        leases = db.query(Lease).join(Property).filter(Property.tenant_id == current_user.tenant_id).all()
    return [_enrich_lease(l, db) for l in leases if _can_access_lease(l, db, current_user)]


def _can_access_lease(lease: Lease, db: Session, current_user: User) -> bool:
    prop = db.query(Property).filter(Property.id == lease.property_id).first()
    if not prop or prop.tenant_id != current_user.tenant_id:
        return False
    if current_user.role == "owner":
        return prop.owner_id == current_user.id
    if current_user.role == "tenant":
        return lease.tenant_user_id == current_user.id
    return True


@router.post("", response_model=LeaseOut)
def create_lease(
    payload: LeaseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["manager"])),
):
    prop = db.query(Property).filter(Property.id == payload.property_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    require_same_tenant(prop.tenant_id, current_user)
    lease = Lease(id=f"l{uuid.uuid4().hex[:8]}", **payload.model_dump())
    db.add(lease)
    db.commit()
    db.refresh(lease)
    return _enrich_lease(lease, db)


@router.get("/{lease_id}", response_model=LeaseOut)
def get_lease(lease_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    lease = db.query(Lease).filter(Lease.id == lease_id).first()
    if not lease or not _can_access_lease(lease, db, current_user):
        raise HTTPException(status_code=404, detail="Lease not found")
    return _enrich_lease(lease, db)


@router.put("/{lease_id}/renew", response_model=LeaseOut)
def renew_lease(
    lease_id: str,
    payload: LeaseRenew,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["manager"])),
):
    lease = db.query(Lease).filter(Lease.id == lease_id).first()
    if not lease or not _can_access_lease(lease, db, current_user):
        raise HTTPException(status_code=404, detail="Lease not found")
    lease.end_date = payload.new_end_date
    lease.status = "active"
    db.commit()
    db.refresh(lease)
    return _enrich_lease(lease, db)
