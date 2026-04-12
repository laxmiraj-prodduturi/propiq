from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, String, func
from ..database import Base


class Vendor(Base):
    __tablename__ = "vendors"

    id = Column(String(50), primary_key=True)
    tenant_id = Column(String(50), ForeignKey("tenant_orgs.id"), nullable=False)
    name = Column(String(255), nullable=False)
    trade = Column(String(100), nullable=False)
    email = Column(String(255), default="")
    phone = Column(String(50), default="")
    rating = Column(Float, default=0.0)
    response_time = Column(String(50), default="")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
