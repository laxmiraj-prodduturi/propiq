from sqlalchemy import Column, String, Float, Date, DateTime, func, ForeignKey
from sqlalchemy.orm import relationship
from ..database import Base


class Lease(Base):
    __tablename__ = "leases"

    id = Column(String(50), primary_key=True)
    property_id = Column(String(50), ForeignKey("properties.id"), nullable=False)
    tenant_user_id = Column(String(50), nullable=False)
    tenant_name = Column(String(255), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    rent_amount = Column(Float, nullable=False)
    security_deposit = Column(Float, default=0)
    status = Column(String(20), default="active")  # active | expired | terminated
    created_at = Column(DateTime, server_default=func.now())

    property = relationship("Property", back_populates="leases")
    payments = relationship("Payment", back_populates="lease")
