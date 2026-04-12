from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class VendorCreate(BaseModel):
    name: str
    trade: str
    email: Optional[str] = ""
    phone: Optional[str] = ""
    rating: Optional[float] = 0.0
    response_time: Optional[str] = ""


class VendorUpdate(BaseModel):
    name: Optional[str] = None
    trade: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    rating: Optional[float] = None
    response_time: Optional[str] = None
    is_active: Optional[bool] = None


class VendorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    name: str
    trade: str
    email: str
    phone: str
    rating: float
    response_time: str
    is_active: bool
    created_at: datetime
