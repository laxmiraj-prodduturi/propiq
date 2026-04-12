from sqlalchemy import Column, String, Float, DateTime, func, ForeignKey
from ..database import Base


class MaintenanceRequest(Base):
    __tablename__ = "maintenance_requests"

    id = Column(String(50), primary_key=True)
    property_id = Column(String(50), ForeignKey("properties.id"), nullable=False)
    tenant_user_id = Column(String(50), nullable=False)
    property_name = Column(String(255), nullable=False)
    tenant_name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False)
    description = Column(String(2000), nullable=False)
    urgency = Column(String(20), default="medium")  # low | medium | high | emergency
    status = Column(String(20), default="submitted")  # submitted | assigned | in_progress | resolved | closed
    assigned_vendor = Column(String(255), nullable=True)
    estimated_cost = Column(Float, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    resolved_at = Column(DateTime, nullable=True)
