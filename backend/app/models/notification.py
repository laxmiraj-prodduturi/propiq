from sqlalchemy import Column, String, Boolean, DateTime, func
from ..database import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(String(50), primary_key=True)
    user_id = Column(String(50), nullable=False, index=True)
    type = Column(String(30), nullable=False)  # payment | maintenance | lease | ai | system
    title = Column(String(500), nullable=False)
    body = Column(String(2000), nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
