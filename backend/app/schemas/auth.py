from pydantic import BaseModel, ConfigDict


class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    email: str
    password: str
    first_name: str
    last_name: str
    role: str = "tenant"
    tenant_id: str = "t1"
    phone: str = ""


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
