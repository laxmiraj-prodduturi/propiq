from pydantic import BaseModel, ConfigDict
from typing import Optional
import datetime


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    lease_id: str
    tenant_name: str
    property_name: str
    amount: float
    due_date: datetime.date
    paid_date: Optional[datetime.date]
    payment_method: str
    status: str
    late_fee: float
    transaction_ref: str


class PaymentInitiate(BaseModel):
    lease_id: str
    amount: float
    payment_method: str
    due_date: datetime.date
