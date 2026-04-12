import { useState, useEffect } from 'react';
import { MOCK_DOCUMENTS } from '../../data/mockData';
import { getDocuments, uploadDocument } from '../../api/documents';
import { useAuth } from '../../context/AuthContext';
import type { Document, DocumentType } from '../../types';

const typeIcon: Record<DocumentType, string> = {
  lease: '📋',
  notice: '📢',
  invoice: '🧾',
  policy: '📜',
  other: '📄',
};

const typeColor: Record<DocumentType, string> = {
  lease: 'var(--primary)',
  notice: 'var(--amber)',
  invoice: 'var(--emerald)',
  policy: 'var(--cyan)',
  other: 'var(--text-muted)',
};

const typeBadge: Record<DocumentType, string> = {
  lease: 'badge-primary',
  notice: 'badge-warning',
  invoice: 'badge-success',
  policy: 'badge-cyan',
  other: 'badge-muted',
};

function DocIcon({ type }: { type: DocumentType }) {
  return (
    <div
      className="doc-icon"
      style={{ background: `${typeColor[type]}18`, border: `1px solid ${typeColor[type]}33` }}
    >
      {typeIcon[type]}
    </div>
  );
}

function UploadModal({ onClose, onUpload, uploaderName }: { onClose: () => void; onUpload: (doc: Document) => void; uploaderName: string }) {
  const [docType, setDocType] = useState<DocumentType>('lease');
  const [fileName, setFileName] = useState('');
  const [dragging, setDragging] = useState(false);

  const handleSubmit = async () => {
    if (!fileName) return;
    try {
      const doc = await uploadDocument({
        uploaded_by: uploaderName,
        document_type: docType,
        file_name: fileName,
        file_size: '—',
        mime_type: 'application/pdf',
        related_entity: '—',
      });
      onUpload(doc);
    } catch {
      const doc: Document = {
        id: `d${Date.now()}`,
        uploadedBy: uploaderName,
        documentType: docType,
        fileName,
        fileSize: '—',
        mimeType: 'application/pdf',
        relatedEntity: '—',
        createdAt: new Date().toISOString(),
      };
      onUpload(doc);
    }
    onClose();
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <span className="modal-title">Upload Document</span>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>

        <div
          className="upload-zone"
          style={{ borderColor: dragging ? 'var(--primary)' : undefined, background: dragging ? 'var(--primary-10)' : undefined }}
          onDragOver={e => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={e => {
            e.preventDefault();
            setDragging(false);
            const file = e.dataTransfer.files[0];
            if (file) setFileName(file.name);
          }}
          onClick={() => {
            const input = document.createElement('input');
            input.type = 'file';
            input.accept = '.pdf,.doc,.docx,.xlsx';
            input.onchange = ev => {
              const file = (ev.target as HTMLInputElement).files?.[0];
              if (file) setFileName(file.name);
            };
            input.click();
          }}
        >
          <span className="upload-icon">☁️</span>
          {fileName ? (
            <>
              <div className="upload-text" style={{ color: 'var(--primary)' }}>{fileName}</div>
              <div className="upload-subtext">File selected — click to change</div>
            </>
          ) : (
            <>
              <div className="upload-text">Drop file here or click to browse</div>
              <div className="upload-subtext">PDF, DOC, DOCX, XLSX — max 25MB</div>
            </>
          )}
        </div>

        <div className="form-group mt-4">
          <label className="form-label">Document Type</label>
          <select
            className="form-input form-select"
            value={docType}
            onChange={e => setDocType(e.target.value as DocumentType)}
          >
            {(['lease', 'notice', 'invoice', 'policy', 'other'] as DocumentType[]).map(t => (
              <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>
            ))}
          </select>
        </div>

        <div className="flex gap-2 justify-end">
          <button className="btn btn-ghost" onClick={onClose}>Cancel</button>
          <button className="btn btn-primary" disabled={!fileName} onClick={handleSubmit}>
            Upload
          </button>
        </div>
      </div>
    </div>
  );
}

export default function Documents() {
  const { user } = useAuth();
  const [docs, setDocs] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<DocumentType | 'all'>('all');
  const [search, setSearch] = useState('');
  const [showUpload, setShowUpload] = useState(false);

  useEffect(() => {
    getDocuments()
      .then(setDocs)
      .catch(() => setDocs(MOCK_DOCUMENTS))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>Loading…</div>;

  const filtered = docs.filter(d => {
    if (filter !== 'all' && d.documentType !== filter) return false;
    if (search && !d.fileName.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  const handleUpload = (doc: Document) => {
    setDocs(prev => [doc, ...prev]);
  };

  const uploaderName = user ? `${user.firstName} ${user.lastName}` : 'You';

  return (
    <div className="animate-in">
      <div className="page-header">
        <div>
          <h2>Document Vault</h2>
          <p>{docs.length} documents stored securely</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowUpload(true)}>
          ☁️ Upload Document
        </button>
      </div>

      <div className="filter-bar">
        <div className="search-input-wrap">
          <span className="search-icon">🔍</span>
          <input
            className="form-input search-input"
            placeholder="Search documents…"
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>
        <div className="tabs">
          {(['all', 'lease', 'notice', 'invoice', 'policy', 'other'] as const).map(t => (
            <button key={t} className={`tab ${filter === t ? 'active' : ''}`} onClick={() => setFilter(t)}>
              {t.charAt(0).toUpperCase() + t.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {filtered.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">📭</div>
          <div className="empty-title">No documents found</div>
          <div className="empty-desc">Upload documents to get started</div>
        </div>
      ) : (
        <div className="document-list">
          {filtered.map(doc => (
            <div key={doc.id} className="document-item">
              <DocIcon type={doc.documentType} />
              <div className="doc-info">
                <div className="doc-name">{doc.fileName}</div>
                <div className="doc-meta">
                  {doc.relatedEntity} · {doc.fileSize} · Uploaded by {doc.uploadedBy} · {new Date(doc.createdAt).toLocaleDateString()}
                </div>
              </div>
              <span className={`badge ${typeBadge[doc.documentType]}`}>{doc.documentType}</span>
              <div className="flex gap-2">
                <button className="btn btn-ghost btn-sm">👁 View</button>
                <button className="btn btn-secondary btn-sm">⬇ Download</button>
              </div>
            </div>
          ))}
        </div>
      )}

      {showUpload && (
        <UploadModal onClose={() => setShowUpload(false)} onUpload={handleUpload} uploaderName={uploaderName} />
      )}
    </div>
  );
}
