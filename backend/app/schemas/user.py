from pydantic import BaseModel, ConfigDict
from typing import Optional


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    email: str
    role: str
    first_name: str
    last_name: str
    phone: str
    avatar_initials: str


class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
