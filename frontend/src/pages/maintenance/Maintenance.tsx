import { useState, useEffect } from 'react';
import { MOCK_MAINTENANCE } from '../../data/mockData';
import { getMaintenanceRequests, updateMaintenanceStatus, createMaintenanceRequest } from '../../api/maintenance';
import type { MaintenanceRequest, MaintenanceStatus, MaintenanceUrgency } from '../../types';

const COLUMNS: { id: MaintenanceStatus; label: string; color: string }[] = [
  { id: 'submitted', label: 'Submitted', color: 'var(--text-muted)' },
  { id: 'assigned', label: 'Assigned', color: 'var(--cyan)' },
  { id: 'in_progress', label: 'In Progress', color: 'var(--amber)' },
  { id: 'resolved', label: 'Resolved', color: 'var(--emerald)' },
];

const urgencyBadge: Record<MaintenanceUrgency, string> = {
  emergency: 'badge-danger',
  high: 'badge-warning',
  medium: 'badge-primary',
  low: 'badge-muted',
};

const urgencyDot: Record<MaintenanceUrgency, string> = {
  emergency: 'var(--rose)',
  high: 'var(--amber)',
  medium: 'var(--primary)',
  low: 'var(--text-muted)',
};

function RequestDetail({ req, onClose, onStatusChange }: {
  req: MaintenanceRequest;
  onClose: () => void;
  onStatusChange: (id: string, status: MaintenanceStatus) => void;
}) {
  const nextStatus: Record<MaintenanceStatus, MaintenanceStatus | null> = {
    submitted: 'assigned',
    assigned: 'in_progress',
    in_progress: 'resolved',
    resolved: 'closed',
    closed: null,
  };

  const next = nextStatus[req.status];

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" style={{ maxWidth: 520 }} onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{ width: 10, height: 10, borderRadius: '50%', background: urgencyDot[req.urgency], boxShadow: req.urgency === 'emergency' ? `0 0 10px ${urgencyDot[req.urgency]}` : 'none' }} />
            <span className="modal-title">{req.category}</span>
          </div>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>

        <div style={{ display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap' }}>
          <span className={`badge ${urgencyBadge[req.urgency]}`}>{req.urgency}</span>
          <span className="badge badge-info">{req.status.replace('_', ' ')}</span>
        </div>

        <div style={{ marginBottom: 14 }}>
          <div className="form-label">Description</div>
          <div style={{ fontSize: 13.5, color: 'var(--text-primary)', lineHeight: 1.6, background: 'var(--bg-input)', padding: '10px 14px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-default)' }}>
            {req.description}
          </div>
        </div>

        <div className="two-col" style={{ marginBottom: 14 }}>
          <div>
            <div className="form-label">Property</div>
            <div style={{ fontSize: 13.5, color: 'var(--text-primary)' }}>{req.propertyName}</div>
          </div>
          <div>
            <div className="form-label">Reported By</div>
            <div style={{ fontSize: 13.5, color: 'var(--text-primary)' }}>{req.tenantName}</div>
          </div>
        </div>

        <div className="two-col" style={{ marginBottom: 14 }}>
          <div>
            <div className="form-label">Assigned Vendor</div>
            <div style={{ fontSize: 13.5, color: req.assignedVendor ? 'var(--text-primary)' : 'var(--text-muted)' }}>
              {req.assignedVendor ?? 'Not assigned'}
            </div>
          </div>
          <div>
            <div className="form-label">Est. Cost</div>
            <div style={{ fontSize: 13.5, color: 'var(--text-primary)' }}>
              {req.estimatedCost ? `$${req.estimatedCost.toLocaleString()}` : '—'}
            </div>
          </div>
        </div>

        <div className="two-col" style={{ marginBottom: 20 }}>
          <div>
            <div className="form-label">Submitted</div>
            <div style={{ fontSize: 13.5, color: 'var(--text-secondary)' }}>
              {new Date(req.createdAt).toLocaleDateString()}
            </div>
          </div>
          {req.resolvedAt && (
            <div>
              <div className="form-label">Resolved</div>
              <div style={{ fontSize: 13.5, color: 'var(--emerald)' }}>
                {new Date(req.resolvedAt).toLocaleDateString()}
              </div>
            </div>
          )}
        </div>

        <div className="flex gap-2 justify-end">
          <button className="btn btn-ghost" onClick={onClose}>Close</button>
          {next && (
            <button className="btn btn-primary" onClick={() => { onStatusChange(req.id, next); onClose(); }}>
              Move to {next.replace('_', ' ')} →
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

function NewRequestModal({ onClose, onSubmit }: { onClose: () => void; onSubmit: (data: Partial<MaintenanceRequest>) => void }) {
  const [form, setForm] = useState({ category: '', description: '', urgency: 'medium' as MaintenanceUrgency });

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <span className="modal-title">New Maintenance Request</span>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>

        <div className="form-group">
          <label className="form-label">Category</label>
          <select
            className="form-input form-select"
            value={form.category}
            onChange={e => setForm(f => ({ ...f, category: e.target.value }))}
          >
            <option value="">Select category…</option>
            {['Plumbing', 'Electrical', 'HVAC', 'Appliance', 'Elevator', 'Roofing', 'Pest Control', 'General Repair'].map(c => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>

        <div className="form-group">
          <label className="form-label">Urgency</label>
          <div className="flex gap-2">
            {(['low', 'medium', 'high', 'emergency'] as MaintenanceUrgency[]).map(u => (
              <button
                key={u}
                type="button"
                className={`btn btn-sm ${form.urgency === u ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setForm(f => ({ ...f, urgency: u }))}
              >
                {u}
              </button>
            ))}
          </div>
        </div>

        <div className="form-group">
          <label className="form-label">Description</label>
          <textarea
            className="form-input"
            rows={4}
            placeholder="Describe the issue in detail…"
            value={form.description}
            onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
            style={{ resize: 'vertical' }}
          />
        </div>

        <div className="flex gap-2 justify-end">
          <button className="btn btn-ghost" onClick={onClose}>Cancel</button>
          <button
            className="btn btn-primary"
            disabled={!form.category || !form.description}
            onClick={() => { onSubmit(form); onClose(); }}
          >
            Submit Request
          </button>
        </div>
      </div>
    </div>
  );
}

export default function Maintenance() {
  const [requests, setRequests] = useState<MaintenanceRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<MaintenanceRequest | null>(null);
  const [showNew, setShowNew] = useState(false);
  const [filterUrgency, setFilterUrgency] = useState<MaintenanceUrgency | 'all'>('all');

  useEffect(() => {
    getMaintenanceRequests()
      .then(setRequests)
      .catch(() => setRequests(MOCK_MAINTENANCE))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>Loading…</div>;

  const openCount = requests.filter(r => r.status !== 'resolved' && r.status !== 'closed').length;
  const emergencyCount = requests.filter(r => r.urgency === 'emergency' && r.status !== 'resolved').length;

  const handleStatusChange = async (id: string, status: MaintenanceStatus) => {
    try {
      const updated = await updateMaintenanceStatus(id, status);
      setRequests(prev => prev.map(r => r.id === id ? updated : r));
    } catch {
      setRequests(prev => prev.map(r => r.id === id ? { ...r, status } : r));
    }
  };

  const handleNewRequest = async (data: Partial<MaintenanceRequest>) => {
    try {
      const newReq = await createMaintenanceRequest({
        property_id: 'p1',
        property_name: 'Maple Street Home',
        tenant_name: 'Marcus Johnson',
        category: data.category ?? '',
        description: data.description ?? '',
        urgency: data.urgency ?? 'medium',
      });
      setRequests(prev => [newReq, ...prev]);
    } catch {
      const newReq: MaintenanceRequest = {
        id: `mr${Date.now()}`,
        propertyId: 'p1',
        tenantUserId: 'u3',
        propertyName: 'Maple Street Home',
        tenantName: 'Marcus Johnson',
        category: data.category ?? '',
        description: data.description ?? '',
        urgency: data.urgency ?? 'medium',
        status: 'submitted',
        assignedVendor: null,
        estimatedCost: null,
        createdAt: new Date().toISOString(),
        resolvedAt: null,
      };
      setRequests(prev => [newReq, ...prev]);
    }
  };

  const filtered = requests.filter(r => filterUrgency === 'all' || r.urgency === filterUrgency);

  return (
    <div className="animate-in">
      <div className="page-header">
        <div>
          <h2>Maintenance</h2>
          <p>{openCount} open requests{emergencyCount > 0 ? ` · ${emergencyCount} emergency` : ''}</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowNew(true)}>+ New Request</button>
      </div>

      <div className="stats-row">
        {['submitted', 'assigned', 'in_progress', 'resolved'].map(s => (
          <div key={s} className="stat-cell">
            <div className="stat-cell-value">{requests.filter(r => r.status === s).length}</div>
            <div className="stat-cell-label">{s.replace('_', ' ')}</div>
          </div>
        ))}
      </div>

      <div className="filter-bar">
        <div className="tabs">
          {(['all', 'emergency', 'high', 'medium', 'low'] as const).map(u => (
            <button key={u} className={`tab ${filterUrgency === u ? 'active' : ''}`} onClick={() => setFilterUrgency(u)}>
              {u === 'all' ? 'All' : u.charAt(0).toUpperCase() + u.slice(1)}
            </button>
          ))}
        </div>
      </div>

      <div className="kanban-board">
        {COLUMNS.map(col => {
          const cards = filtered.filter(r => r.status === col.id);
          return (
            <div key={col.id} className="kanban-col">
              <div className="kanban-col-header">
                <div style={{ width: 8, height: 8, borderRadius: '50%', background: col.color }} />
                <span className="kanban-col-title" style={{ color: col.color }}>{col.label}</span>
                <span className="kanban-col-count">{cards.length}</span>
              </div>
              <div className="kanban-cards">
                {cards.length === 0 ? (
                  <div style={{ textAlign: 'center', padding: '20px 10px', color: 'var(--text-muted)', fontSize: 12 }}>
                    No requests
                  </div>
                ) : cards.map(req => (
                  <div key={req.id} className="kanban-card" onClick={() => setSelected(req)}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
                      <div style={{ width: 7, height: 7, borderRadius: '50%', background: urgencyDot[req.urgency], flexShrink: 0 }} />
                      <span className="kanban-card-title">{req.category}</span>
                    </div>
                    <div className="kanban-card-meta">{req.propertyName}</div>
                    <div className="kanban-card-meta" style={{ marginBottom: 8 }}>{req.tenantName}</div>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <span className={`badge ${urgencyBadge[req.urgency]}`}>{req.urgency}</span>
                      {req.assignedVendor && (
                        <span style={{ fontSize: 10.5, color: 'var(--text-muted)' }}>👷 {req.assignedVendor.split(' ')[0]}</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>

      {selected && (
        <RequestDetail
          req={selected}
          onClose={() => setSelected(null)}
          onStatusChange={handleStatusChange}
        />
      )}

      {showNew && (
        <NewRequestModal
          onClose={() => setShowNew(false)}
          onSubmit={handleNewRequest}
        />
      )}
    </div>
  );
}
