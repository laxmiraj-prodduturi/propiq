from pydantic import BaseModel, ConfigDict
from typing import Optional
import datetime


class MaintenanceRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    property_id: str
    tenant_user_id: str
    property_name: str
    tenant_name: str
    category: str
    description: str
    urgency: str
    status: str
    assigned_vendor: Optional[str]
    estimated_cost: Optional[float]
    created_at: datetime.datetime
    resolved_at: Optional[datetime.datetime]


class MaintenanceRequestCreate(BaseModel):
    property_id: str
    property_name: str
    tenant_name: str
    category: str
    description: str
    urgency: str = "medium"


class MaintenanceStatusUpdate(BaseModel):
    status: str
    assigned_vendor: Optional[str] = None
    estimated_cost: Optional[float] = None
