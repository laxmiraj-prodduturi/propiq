from sqlalchemy import Column, String, Float, Date, DateTime, func, ForeignKey
from sqlalchemy.orm import relationship
from ..database import Base


class Payment(Base):
    __tablename__ = "payments"

    id = Column(String(50), primary_key=True)
    lease_id = Column(String(50), ForeignKey("leases.id"), nullable=False)
    tenant_name = Column(String(255), nullable=False)
    property_name = Column(String(255), nullable=False)
    amount = Column(Float, nullable=False)
    due_date = Column(Date, nullable=False)
    paid_date = Column(Date, nullable=True)
    payment_method = Column(String(100), default="")
    status = Column(String(20), default="pending")  # pending | paid | late | failed
    late_fee = Column(Float, default=0)
    transaction_ref = Column(String(100), default="")
    created_at = Column(DateTime, server_default=func.now())

    lease = relationship("Lease", back_populates="payments")
