import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..deps import get_current_user
from ..models.user import User
from ..models.document import Document
from ..schemas.document import DocumentOut, DocumentUpload

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("", response_model=List[DocumentOut])
def list_documents(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    docs = db.query(Document).filter(Document.uploaded_by.like("%")).order_by(Document.created_at.desc()).all()
    return [DocumentOut.model_validate(d) for d in docs]


@router.post("/upload", response_model=DocumentOut)
def upload_document(
    payload: DocumentUpload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if payload.uploaded_by and payload.uploaded_by != f"{current_user.first_name} {current_user.last_name}":
        raise HTTPException(status_code=400, detail="uploaded_by must match the authenticated user")
    doc = Document(
        id=f"d{uuid.uuid4().hex[:8]}",
        **payload.model_dump(),
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return DocumentOut.model_validate(doc)


@router.get("/{document_id}/download")
def download_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"document_id": doc.id, "file_name": doc.file_name, "download_url": f"/documents/{doc.id}/content"}
