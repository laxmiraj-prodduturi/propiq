import { apiRequest } from './client';
import type { Document } from '../types';

function mapDocument(raw: any): Document {
  return {
    id: raw.id,
    uploadedBy: raw.uploaded_by,
    documentType: raw.document_type,
    fileName: raw.file_name,
    fileSize: raw.file_size,
    mimeType: raw.mime_type,
    relatedEntity: raw.related_entity,
    createdAt: raw.created_at,
  };
}

export async function getDocuments(): Promise<Document[]> {
  const data = await apiRequest<any[]>('/documents');
  return data.map(mapDocument);
}

export async function uploadDocument(payload: {
  uploaded_by: string;
  document_type: string;
  file_name: string;
  file_size: string;
  mime_type: string;
  related_entity: string;
}): Promise<Document> {
  const raw = await apiRequest<any>('/documents/upload', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
  return mapDocument(raw);
}
