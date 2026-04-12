from pydantic import BaseModel, ConfigDict
import datetime


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    uploaded_by: str
    document_type: str
    file_name: str
    file_size: str
    mime_type: str
    related_entity: str
    created_at: datetime.datetime


class DocumentUpload(BaseModel):
    uploaded_by: str
    document_type: str
    file_name: str
    file_size: str = "—"
    mime_type: str = "application/pdf"
    related_entity: str = "—"
