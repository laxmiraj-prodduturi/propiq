import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models.user import User
from ..models.vendor import Vendor
from ..schemas.vendor import VendorCreate, VendorOut, VendorUpdate

router = APIRouter(prefix="/vendors", tags=["vendors"])


@router.get("/", response_model=list[VendorOut])
def list_vendors(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(Vendor)
        .filter(Vendor.tenant_id == current_user.tenant_id, Vendor.is_active == True)
        .order_by(Vendor.name.asc())
        .all()
    )


@router.post("/", response_model=VendorOut, status_code=201)
def create_vendor(
    payload: VendorCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in {"owner", "manager"}:
        raise HTTPException(status_code=403, detail="Only owners and managers can add vendors")

    vendor = Vendor(
        id=f"v{uuid.uuid4().hex[:8]}",
        tenant_id=current_user.tenant_id,
        **payload.model_dump(),
    )
    db.add(vendor)
    db.commit()
    db.refresh(vendor)
    return vendor


@router.put("/{vendor_id}", response_model=VendorOut)
def update_vendor(
    vendor_id: str,
    payload: VendorUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in {"owner", "manager"}:
        raise HTTPException(status_code=403, detail="Only owners and managers can update vendors")

    vendor = db.query(Vendor).filter(
        Vendor.id == vendor_id,
        Vendor.tenant_id == current_user.tenant_id,
    ).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(vendor, field, value)

    db.commit()
    db.refresh(vendor)
    return vendor


@router.delete("/{vendor_id}", status_code=204)
def delete_vendor(
    vendor_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in {"owner", "manager"}:
        raise HTTPException(status_code=403, detail="Only owners and managers can delete vendors")

    vendor = db.query(Vendor).filter(
        Vendor.id == vendor_id,
        Vendor.tenant_id == current_user.tenant_id,
    ).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    vendor.is_active = False  # soft delete
    db.commit()
