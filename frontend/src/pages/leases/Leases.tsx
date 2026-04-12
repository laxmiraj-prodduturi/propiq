import { useState, useEffect } from 'react';
import { MOCK_LEASES } from '../../data/mockData';
import { getLeases } from '../../api/leases';
import type { Lease, LeaseStatus } from '../../types';

const statusBadge: Record<LeaseStatus, string> = {
  active: 'badge-success',
  expired: 'badge-muted',
  terminated: 'badge-danger',
};

function LeaseProgress({ lease }: { lease: Lease }) {
  const start = new Date(lease.startDate).getTime();
  const end = new Date(lease.endDate).getTime();
  const now = Date.now();
  const pct = Math.min(100, Math.max(0, Math.round(((now - start) / (end - start)) * 100)));
  const daysLeft = Math.max(0, Math.round((end - now) / 86400000));

  return (
    <div style={{ marginTop: 8 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 5, fontSize: 11 }}>
        <span style={{ color: 'var(--text-muted)' }}>{pct}% through term</span>
        <span style={{ color: daysLeft < 60 ? 'var(--amber)' : 'var(--text-muted)' }}>
          {daysLeft === 0 ? 'Expired' : `${daysLeft}d left`}
        </span>
      </div>
      <div style={{ height: 5, background: 'var(--bg-input)', borderRadius: 'var(--radius-full)', overflow: 'hidden' }}>
        <div style={{ height: '100%', width: `${pct}%`, background: daysLeft < 60 ? 'var(--amber)' : 'var(--grad-primary)', borderRadius: 'var(--radius-full)', transition: 'width 0.5s' }} />
      </div>
    </div>
  );
}

export default function Leases() {
  const [leases, setLeases] = useState<Lease[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<LeaseStatus | 'all'>('all');

  useEffect(() => {
    getLeases()
      .then(setLeases)
      .catch(() => setLeases(MOCK_LEASES))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>Loading…</div>;

  const filtered = leases.filter(l => filter === 'all' || l.status === filter);
  const activeCount = leases.filter(l => l.status === 'active').length;
  const expiringSoon = leases.filter(l => {
    const daysLeft = Math.round((new Date(l.endDate).getTime() - Date.now()) / 86400000);
    return l.status === 'active' && daysLeft < 60;
  }).length;

  return (
    <div className="animate-in">
      <div className="page-header">
        <div>
          <h2>Leases</h2>
          <p>{activeCount} active · {expiringSoon} expiring within 60 days</p>
        </div>
        <button className="btn btn-primary">+ New Lease</button>
      </div>

      <div className="stats-row">
        <div className="stat-cell">
          <div className="stat-cell-value" style={{ color: 'var(--emerald)' }}>{leases.filter(l => l.status === 'active').length}</div>
          <div className="stat-cell-label">Active</div>
        </div>
        <div className="stat-cell">
          <div className="stat-cell-value" style={{ color: 'var(--amber)' }}>{expiringSoon}</div>
          <div className="stat-cell-label">Expiring Soon</div>
        </div>
        <div className="stat-cell">
          <div className="stat-cell-value" style={{ color: 'var(--text-muted)' }}>{leases.filter(l => l.status === 'expired').length}</div>
          <div className="stat-cell-label">Expired</div>
        </div>
        <div className="stat-cell">
          <div className="stat-cell-value">${leases.filter(l => l.status === 'active').reduce((s, l) => s + l.rentAmount, 0).toLocaleString()}</div>
          <div className="stat-cell-label">Active Monthly Revenue</div>
        </div>
      </div>

      <div className="filter-bar">
        <div className="tabs">
          {(['all', 'active', 'expired', 'terminated'] as const).map(s => (
            <button key={s} className={`tab ${filter === s ? 'active' : ''}`} onClick={() => setFilter(s)}>
              {s.charAt(0).toUpperCase() + s.slice(1)}
            </button>
          ))}
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        {filtered.map(lease => {
          const daysLeft = Math.round((new Date(lease.endDate).getTime() - Date.now()) / 86400000);
          return (
            <div key={lease.id} className="card" style={{ cursor: 'pointer' }}>
              <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 14 }}>
                <div>
                  <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 4 }}>
                    {lease.propertyName}
                  </div>
                  <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
                    Tenant: <strong>{lease.tenantName}</strong>
                  </div>
                </div>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                  {lease.status === 'active' && daysLeft < 60 && daysLeft > 0 && (
                    <span className="badge badge-warning">Expires Soon</span>
                  )}
                  <span className={`badge ${statusBadge[lease.status]}`}>{lease.status}</span>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 12 }}>
                <div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 2, textTransform: 'uppercase', letterSpacing: '0.5px' }}>Monthly Rent</div>
                  <div style={{ fontSize: 16, fontWeight: 700 }}>${lease.rentAmount.toLocaleString()}</div>
                </div>
                <div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 2, textTransform: 'uppercase', letterSpacing: '0.5px' }}>Security Deposit</div>
                  <div style={{ fontSize: 16, fontWeight: 700 }}>${lease.securityDeposit.toLocaleString()}</div>
                </div>
                <div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 2, textTransform: 'uppercase', letterSpacing: '0.5px' }}>Start Date</div>
                  <div style={{ fontSize: 14, fontWeight: 500 }}>{lease.startDate}</div>
                </div>
                <div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 2, textTransform: 'uppercase', letterSpacing: '0.5px' }}>End Date</div>
                  <div style={{ fontSize: 14, fontWeight: 500, color: daysLeft < 60 && lease.status === 'active' ? 'var(--amber)' : 'inherit' }}>
                    {lease.endDate}
                  </div>
                </div>
              </div>

              {lease.status === 'active' && <LeaseProgress lease={lease} />}

              <div style={{ display: 'flex', gap: 8, marginTop: 14 }}>
                <button className="btn btn-ghost btn-sm">📋 View Lease</button>
                {lease.status === 'active' && <button className="btn btn-secondary btn-sm">🔄 Initiate Renewal</button>}
                <button className="btn btn-ghost btn-sm">🤖 Ask AI</button>
              </div>
            </div>
          );
        })}
      </div>

      {filtered.length === 0 && (
        <div className="empty-state">
          <div className="empty-icon">📋</div>
          <div className="empty-title">No leases found</div>
        </div>
      )}
    </div>
  );
}
