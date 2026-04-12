import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..deps import get_current_user, require_roles, require_same_tenant
from ..models.user import User
from ..models.property import Property
from ..schemas.property import PropertyOut, PropertyCreate, PropertyUpdate

router = APIRouter(prefix="/properties", tags=["properties"])


@router.get("", response_model=List[PropertyOut])
def list_properties(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role in ("manager",):
        props = db.query(Property).filter(
            Property.tenant_id == current_user.tenant_id,
            Property.property_type == "residential",
        ).all()
    elif current_user.role == "owner":
        props = db.query(Property).filter(
            Property.owner_id == current_user.id,
            Property.property_type == "residential",
        ).all()
    else:
        props = db.query(Property).filter(
            Property.tenant_id == current_user.tenant_id,
            Property.property_type == "residential",
        ).all()
    return [PropertyOut.model_validate(p) for p in props]


@router.post("", response_model=PropertyOut)
def create_property(
    payload: PropertyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["owner", "manager"])),
):
    owner_id = current_user.id
    if current_user.role == "manager":
        owner = db.query(User).filter(
            User.tenant_id == current_user.tenant_id,
            User.role == "owner",
        ).first()
        if owner is None:
            raise HTTPException(status_code=400, detail="No owner is configured for this tenant")
        owner_id = owner.id

    prop = Property(
        id=f"p{uuid.uuid4().hex[:8]}",
        tenant_id=current_user.tenant_id,
        owner_id=owner_id,
        **{**payload.model_dump(), "property_type": "residential"},
    )
    db.add(prop)
    db.commit()
    db.refresh(prop)
    return PropertyOut.model_validate(prop)


@router.get("/{property_id}", response_model=PropertyOut)
def get_property(property_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    prop = db.query(Property).filter(Property.id == property_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    require_same_tenant(prop.tenant_id, current_user)
    if current_user.role == "owner" and prop.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Property not found")
    return PropertyOut.model_validate(prop)


@router.put("/{property_id}", response_model=PropertyOut)
def update_property(
    property_id: str,
    payload: PropertyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["owner", "manager"])),
):
    prop = db.query(Property).filter(Property.id == property_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    require_same_tenant(prop.tenant_id, current_user)
    if current_user.role == "owner" and prop.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Property not found")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(prop, field, value)
    prop.property_type = "residential"
    db.commit()
    db.refresh(prop)
    return PropertyOut.model_validate(prop)


@router.delete("/{property_id}")
def delete_property(
    property_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["owner", "manager"])),
):
    prop = db.query(Property).filter(Property.id == property_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    require_same_tenant(prop.tenant_id, current_user)
    if current_user.role == "owner" and prop.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Property not found")
    db.delete(prop)
    db.commit()
    return {"message": "Property deleted"}
