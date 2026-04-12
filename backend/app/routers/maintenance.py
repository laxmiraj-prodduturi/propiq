import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..deps import get_current_user
from ..models.user import User
from ..models.maintenance import MaintenanceRequest
from ..models.property import Property
from ..schemas.maintenance import MaintenanceRequestOut, MaintenanceRequestCreate, MaintenanceStatusUpdate

router = APIRouter(prefix="/maintenance", tags=["maintenance"])


@router.get("/requests", response_model=List[MaintenanceRequestOut])
def list_requests(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role == "tenant":
        requests = db.query(MaintenanceRequest).filter(
            MaintenanceRequest.tenant_user_id == current_user.id
        ).all()
    else:
        requests = db.query(MaintenanceRequest).join(Property, MaintenanceRequest.property_id == Property.id).filter(
            Property.tenant_id == current_user.tenant_id
        ).all()
        if current_user.role == "owner":
            requests = [req for req in requests if db.query(Property).filter(Property.id == req.property_id).first().owner_id == current_user.id]
    return [MaintenanceRequestOut.model_validate(r) for r in requests]


@router.post("/requests", response_model=MaintenanceRequestOut)
def create_request(
    payload: MaintenanceRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    prop = db.query(Property).filter(Property.id == payload.property_id).first()
    if not prop or prop.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="Property not found")
    req = MaintenanceRequest(
        id=f"mr{uuid.uuid4().hex[:8]}",
        **payload.model_dump(),
        tenant_user_id=current_user.id,
        property_name=prop.name,
        tenant_name=f"{current_user.first_name} {current_user.last_name}",
        status="submitted",
        assigned_vendor=None,
        estimated_cost=None,
        resolved_at=None,
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    return MaintenanceRequestOut.model_validate(req)


@router.get("/requests/{request_id}", response_model=MaintenanceRequestOut)
def get_request(request_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    req = db.query(MaintenanceRequest).filter(MaintenanceRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    prop = db.query(Property).filter(Property.id == req.property_id).first()
    if not prop or prop.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="Request not found")
    return MaintenanceRequestOut.model_validate(req)


@router.put("/requests/{request_id}/status", response_model=MaintenanceRequestOut)
def update_status(
    request_id: str,
    payload: MaintenanceStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    req = db.query(MaintenanceRequest).filter(MaintenanceRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    prop = db.query(Property).filter(Property.id == req.property_id).first()
    if not prop or prop.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="Request not found")
    req.status = payload.status
    if payload.assigned_vendor is not None:
        req.assigned_vendor = payload.assigned_vendor
    if payload.estimated_cost is not None:
        req.estimated_cost = payload.estimated_cost
    if payload.status in ("resolved", "closed"):
        req.resolved_at = datetime.utcnow()
    db.commit()
    db.refresh(req)
    return MaintenanceRequestOut.model_validate(req)
