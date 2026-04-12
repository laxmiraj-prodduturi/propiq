from pydantic import BaseModel, ConfigDict
from typing import Optional
import datetime


class LeaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    property_id: str
    tenant_user_id: str
    tenant_name: str
    start_date: datetime.date
    end_date: datetime.date
    rent_amount: float
    security_deposit: float
    status: str
    property_name: str = ""


class LeaseCreate(BaseModel):
    property_id: str
    tenant_user_id: str
    tenant_name: str
    start_date: datetime.date
    end_date: datetime.date
    rent_amount: float
    security_deposit: float = 0
    status: str = "active"


class LeaseRenew(BaseModel):
    new_end_date: datetime.date
