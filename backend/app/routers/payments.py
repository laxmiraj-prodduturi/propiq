import uuid
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..deps import get_current_user
from ..models.user import User
from ..models.payment import Payment
from ..models.lease import Lease
from ..models.property import Property
from ..schemas.payment import PaymentOut, PaymentInitiate

router = APIRouter(prefix="/payments", tags=["payments"])


@router.get("", response_model=List[PaymentOut])
def list_payments(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role == "tenant":
        # Get leases for this tenant
        lease_ids = [l.id for l in db.query(Lease).filter(Lease.tenant_user_id == current_user.id).all()]
        payments = db.query(Payment).filter(Payment.lease_id.in_(lease_ids)).all()
    else:
        payments = db.query(Payment).join(Lease).join(Property, Lease.property_id == Property.id).filter(
            Property.tenant_id == current_user.tenant_id
        ).all()
        if current_user.role == "owner":
            payments = [payment for payment in payments if payment.lease.property.owner_id == current_user.id]
    return [PaymentOut.model_validate(p) for p in payments]


@router.post("/initiate", response_model=PaymentOut)
def initiate_payment(
    payload: PaymentInitiate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    lease = db.query(Lease).filter(Lease.id == payload.lease_id).first()
    if not lease:
        raise HTTPException(status_code=404, detail="Lease not found")
    prop = db.query(Property).filter(Property.id == lease.property_id).first()
    if not prop or prop.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="Lease not found")
    if current_user.role == "tenant" and lease.tenant_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Cannot pay for another tenant lease")

    payment = Payment(
        id=f"pay{uuid.uuid4().hex[:8]}",
        lease_id=payload.lease_id,
        tenant_name=lease.tenant_name,
        property_name=prop.name,
        amount=payload.amount,
        due_date=payload.due_date,
        paid_date=date.today(),
        payment_method=payload.payment_method,
        status="paid",
        late_fee=0,
        transaction_ref=f"TXN-{uuid.uuid4().hex[:8].upper()}",
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return PaymentOut.model_validate(payment)


@router.get("/history", response_model=List[PaymentOut])
def payment_history(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return list_payments(db, current_user)
