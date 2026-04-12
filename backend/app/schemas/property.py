from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict


class PropertyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    owner_id: str
    name: str
    address: str
    city: str
    state: str
    zip: str
    property_type: str
    bedrooms: int
    bathrooms: float
    sqft: int
    status: str
    rent_amount: float
    image_color: str


class PropertyCreate(BaseModel):
    name: str
    address: str
    city: str
    state: str
    zip: str
    property_type: Literal["residential"] = "residential"
    bedrooms: int = 0
    bathrooms: float = 1.0
    sqft: int = 0
    status: str = "vacant"
    rent_amount: float = 0
    image_color: str = "#6366f1"


class PropertyUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None
    property_type: Optional[Literal["residential"]] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[float] = None
    sqft: Optional[int] = None
    status: Optional[str] = None
    rent_amount: Optional[float] = None
    image_color: Optional[str] = None
