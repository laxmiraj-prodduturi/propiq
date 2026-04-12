from sqlalchemy import Column, String, DateTime, func, ForeignKey
from sqlalchemy.orm import relationship
from ..database import Base


class TenantOrg(Base):
    __tablename__ = "tenant_orgs"

    id = Column(String(50), primary_key=True)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class User(Base):
    __tablename__ = "users"

    id = Column(String(50), primary_key=True)
    tenant_id = Column(String(50), ForeignKey("tenant_orgs.id"), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False)  # owner | manager | tenant
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    phone = Column(String(50), default="")
    avatar_initials = Column(String(5), default="")
    created_at = Column(DateTime, server_default=func.now())
