from sqlalchemy import Column, String, Integer, Float, DateTime, func, ForeignKey
from sqlalchemy.orm import relationship
from ..database import Base


class Property(Base):
    __tablename__ = "properties"

    id = Column(String(50), primary_key=True)
    tenant_id = Column(String(50), ForeignKey("tenant_orgs.id"), nullable=False)
    owner_id = Column(String(50), ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    address = Column(String(255), nullable=False)
    city = Column(String(100), nullable=False)
    state = Column(String(50), nullable=False)
    zip = Column(String(20), nullable=False)
    property_type = Column(String(20), nullable=False)  # residential | commercial | mixed
    bedrooms = Column(Integer, default=0)
    bathrooms = Column(Float, default=1.0)
    sqft = Column(Integer, default=0)
    status = Column(String(20), default="vacant")  # vacant | occupied | maintenance
    rent_amount = Column(Float, default=0)
    image_color = Column(String(20), default="#6366f1")
    created_at = Column(DateTime, server_default=func.now())

    owner = relationship("User", foreign_keys=[owner_id])
    leases = relationship("Lease", back_populates="property")
