from sqlalchemy import Column, String, DateTime, func
from ..database import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(String(50), primary_key=True)
    tenant_id = Column(String(50), default="t1")          # for multi-tenant RAG filtering
    uploaded_by = Column(String(255), nullable=False)
    document_type = Column(String(50), nullable=False)    # lease | notice | invoice | policy | disclosure | other
    file_name = Column(String(500), nullable=False)
    file_size = Column(String(50), default="")
    mime_type = Column(String(100), default="application/pdf")
    related_entity = Column(String(500), default="")
    file_path = Column(String(1000), default="")          # path to extracted text file for RAG indexing
    created_at = Column(DateTime, server_default=func.now())
