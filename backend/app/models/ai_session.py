from sqlalchemy import Column, DateTime, ForeignKey, String, Text, func
from ..database import Base


class AISession(Base):
    __tablename__ = "ai_sessions"

    id = Column(String(50), primary_key=True)
    tenant_id = Column(String(50), ForeignKey("tenant_orgs.id"), nullable=False)
    user_id = Column(String(50), ForeignKey("users.id"), nullable=False)
    session_id = Column(String(100), unique=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    last_active_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class AIMessage(Base):
    __tablename__ = "ai_messages"

    id = Column(String(50), primary_key=True)
    session_id = Column(String(100), ForeignKey("ai_sessions.session_id"), nullable=False)
    role = Column(String(20), nullable=False)  # user | assistant | system
    content = Column(Text, nullable=False)
    action_card_json = Column(Text)  # JSON-serialised AIActionCard when present
    created_at = Column(DateTime, server_default=func.now())


class AIApproval(Base):
    __tablename__ = "ai_approvals"

    id = Column(String(50), primary_key=True)
    tenant_id = Column(String(50), ForeignKey("tenant_orgs.id"), nullable=False)
    user_id = Column(String(50), ForeignKey("users.id"), nullable=False)
    session_id = Column(String(100), ForeignKey("ai_sessions.session_id"), nullable=False)
    action_id = Column(String(50), unique=True, nullable=False)
    action_type = Column(String(100), nullable=False)
    action_payload_json = Column(Text)
    status = Column(String(20), default="pending")  # pending | approved | rejected
    approver_user_id = Column(String(50))
    created_at = Column(DateTime, server_default=func.now())
    resolved_at = Column(DateTime)
