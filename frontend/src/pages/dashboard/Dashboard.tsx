import { useAuth } from '../../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { MOCK_PROPERTIES, MOCK_PAYMENTS, MOCK_MAINTENANCE, MOCK_LEASES } from '../../data/mockData';
import { getProperties } from '../../api/properties';
import { getPayments } from '../../api/payments';
import { getMaintenanceRequests } from '../../api/maintenance';
import { getLeases } from '../../api/leases';
import type { Property, Payment, MaintenanceRequest, Lease, KPICard } from '../../types';

function OccupancyBar({ properties }: { properties: Property[] }) {
  const occupied = properties.filter(property => property.status === 'occupied').length;
  const vacant = properties.filter(property => property.status === 'vacant').length;
  const maintenance = properties.filter(property => property.status === 'maintenance').length;
  const total = properties.length;
  if (total === 0) return null;
  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>Home Occupancy Overview</span>
        <span style={{ fontSize: 13, fontWeight: 700 }}>{Math.round((occupied / total) * 100)}% occupied</span>
      </div>
      <div style={{ display: 'flex', height: 10, borderRadius: 'var(--radius-full)', overflow: 'hidden', gap: 2 }}>
        <div style={{ flex: occupied, background: 'var(--emerald)', borderRadius: 'var(--radius-full)' }} title={`Occupied: ${occupied}`} />
        <div style={{ flex: vacant, background: 'var(--primary)', borderRadius: 'var(--radius-full)' }} title={`Vacant: ${vacant}`} />
        <div style={{ flex: maintenance, background: 'var(--amber)', borderRadius: 'var(--radius-full)' }} title={`Maintenance: ${maintenance}`} />
      </div>
      <div className="flex gap-4 mt-2">
        {[
          { label: 'Occupied', count: occupied, color: 'var(--emerald)' },
          { label: 'Vacant', count: vacant, color: 'var(--primary)' },
          { label: 'Maintenance', count: maintenance, color: 'var(--amber)' },
        ].map(s => (
          <div key={s.label} className="flex items-center gap-1">
            <div style={{ width: 8, height: 8, borderRadius: '50%', background: s.color }} />
            <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{s.label}: {s.count}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function DashboardContent({
  kpis,
  isTenant = false,
  properties,
  payments,
  maintenance,
}: {
  kpis: KPICard[];
  isTenant?: boolean;
  properties: Property[];
  payments: Payment[];
  maintenance: MaintenanceRequest[];
}) {
  const navigate = useNavigate();
  const openMaintenance = maintenance.filter(m => m.status !== 'resolved' && m.status !== 'closed');
  const recentPayments = payments.slice(0, 4);

  const urgencyColor: Record<string, string> = {
    emergency: 'var(--rose)',
    high: 'var(--amber)',
    medium: 'var(--primary)',
    low: 'var(--text-muted)',
  };

  const statusBadge: Record<string, string> = {
    submitted: 'badge-muted',
    assigned: 'badge-info',
    in_progress: 'badge-warning',
    resolved: 'badge-success',
    closed: 'badge-muted',
  };

  const paymentBadge: Record<string, string> = {
    paid: 'badge-success',
    pending: 'badge-info',
    late: 'badge-warning',
    failed: 'badge-danger',
  };

  return (
    <>
      {/* KPI Grid */}
      <div className="kpi-grid">
        {kpis.map(kpi => (
          <div key={kpi.label} className="kpi-card">
            <div className="kpi-accent" style={{ background: kpi.color }} />
            <div className="kpi-icon-wrap" style={{ background: `${kpi.color}18` }}>
              <span style={{ fontSize: 20 }}>{kpi.icon}</span>
            </div>
            <div className="kpi-label">{kpi.label}</div>
            <div className="kpi-value">{kpi.value}</div>
            <div className={`kpi-change ${kpi.changeType}`}>
              {kpi.changeType === 'up' && '↑'}
              {kpi.changeType === 'down' && '↓'}
              {kpi.change}
            </div>
          </div>
        ))}
      </div>

      {/* Two column layout */}
      <div className="two-col">
        {/* Open Maintenance */}
        <div className="card">
          <div className="section-header">
            <span className="section-title">Open Maintenance</span>
            <button className="btn btn-ghost btn-sm" onClick={() => navigate('/maintenance')}>View all →</button>
          </div>
          {openMaintenance.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon">✅</div>
              <div className="empty-title">All clear!</div>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {openMaintenance.slice(0, 4).map(req => (
                <div key={req.id} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 0', borderBottom: '1px solid var(--border-subtle)' }}>
                  <div style={{
                    width: 8, height: 8, borderRadius: '50%',
                    background: urgencyColor[req.urgency], flexShrink: 0,
                    boxShadow: req.urgency === 'emergency' ? `0 0 8px ${urgencyColor[req.urgency]}` : 'none'
                  }} />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 2 }}>
                      {req.category}
                    </div>
                    <div style={{ fontSize: 11.5, color: 'var(--text-muted)' }}>
                      {req.propertyName}
                    </div>
                  </div>
                  <span className={`badge ${statusBadge[req.status]}`}>
                    {req.status.replace('_', ' ')}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Recent Payments */}
        <div className="card">
          <div className="section-header">
            <span className="section-title">Recent Payments</span>
            <button className="btn btn-ghost btn-sm" onClick={() => navigate('/payments')}>View all →</button>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {recentPayments.map(pay => (
              <div key={pay.id} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 0', borderBottom: '1px solid var(--border-subtle)' }}>
                <div style={{ width: 36, height: 36, borderRadius: 'var(--radius-sm)', background: 'var(--bg-input)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 16 }}>
                  💳
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 2 }}>
                    {pay.tenantName}
                  </div>
                  <div style={{ fontSize: 11.5, color: 'var(--text-muted)' }}>
                    {pay.propertyName} · {pay.dueDate}
                  </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: 13.5, fontWeight: 700, color: 'var(--text-primary)' }}>
                    ${pay.amount.toLocaleString()}
                  </div>
                  <span className={`badge ${paymentBadge[pay.status]}`}>{pay.status}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Occupancy Bar */}
      {!isTenant && (
        <div className="card mt-4">
          <OccupancyBar properties={properties} />
        </div>
      )}

      {/* Quick Actions */}
      <div className="card mt-4">
        <div className="section-title" style={{ marginBottom: 14 }}>Quick Actions</div>
        <div className="flex gap-3 flex-wrap">
          <button className="btn btn-primary" onClick={() => navigate('/ai-chat')}>
            🤖 Ask AI Assistant
          </button>
          <button className="btn btn-secondary" onClick={() => navigate('/maintenance')}>
            🔧 New Work Order
          </button>
          <button className="btn btn-secondary" onClick={() => navigate('/documents')}>
            📁 Upload Document
          </button>
          {!isTenant && (
            <button className="btn btn-secondary" onClick={() => navigate('/properties')}>
              🏢 View Properties
            </button>
          )}
        </div>
      </div>
    </>
  );
}

function OwnerDashboard({ properties, payments, maintenance, leases }: {
  properties: Property[]; payments: Payment[]; maintenance: MaintenanceRequest[]; leases: Lease[];
}) {
  const occupied = properties.filter(property => property.status === 'occupied').length;
  const monthlyRevenue = properties.filter(property => property.status === 'occupied').reduce((s, property) => s + property.rentAmount, 0);
  const pendingPayments = payments.filter(p => p.status === 'pending' || p.status === 'late');

  const kpis: KPICard[] = [
    { label: 'Total Homes', value: `${properties.length}`, change: 'Residential only', changeType: 'neutral', icon: '🏡', color: 'var(--primary)' },
    { label: 'Occupied Homes', value: `${occupied}`, change: `${properties.length - occupied} available`, changeType: 'neutral', icon: '🛏️', color: 'var(--cyan)' },
    { label: 'Monthly Revenue', value: `$${(monthlyRevenue / 1000).toFixed(1)}k`, change: '+4.2% vs last month', changeType: 'up', icon: '💰', color: 'var(--emerald)' },
    { label: 'Pending Payments', value: `${pendingPayments.length}`, change: 'Requires attention', changeType: 'down', icon: '⚠️', color: 'var(--amber)' },
  ];

  return <DashboardContent kpis={kpis} properties={properties} payments={payments} maintenance={maintenance} />;
}

function ManagerDashboard({ properties, payments, maintenance, leases }: {
  properties: Property[]; payments: Payment[]; maintenance: MaintenanceRequest[]; leases: Lease[];
}) {
  const openMaintenance = maintenance.filter(m => m.status !== 'resolved' && m.status !== 'closed').length;
  const activeLeases = leases.filter(l => l.status === 'active').length;
  const collectionRate = payments.length > 0 ? Math.round((payments.filter(p => p.status === 'paid').length / payments.length) * 100) : 0;

  const kpis: KPICard[] = [
    { label: 'Managed Homes', value: `${properties.length}`, change: 'Residential portfolio', changeType: 'neutral', icon: '🏡', color: 'var(--primary)' },
    { label: 'Active Leases', value: `${activeLeases}`, change: '1 expiring soon', changeType: 'neutral', icon: '📋', color: 'var(--cyan)' },
    { label: 'Open Work Orders', value: `${openMaintenance}`, change: '1 emergency', changeType: 'down', icon: '🔧', color: 'var(--rose)' },
    { label: 'Collection Rate', value: `${collectionRate}%`, change: '+3% vs last month', changeType: 'up', icon: '📈', color: 'var(--emerald)' },
  ];

  return <DashboardContent kpis={kpis} properties={properties} payments={payments} maintenance={maintenance} />;
}

function TenantDashboard({ properties, payments, maintenance, leases }: {
  properties: Property[]; payments: Payment[]; maintenance: MaintenanceRequest[]; leases: Lease[];
}) {
  const myLease = leases[0] ?? MOCK_LEASES[0];
  const myPayments = payments.filter(p => p.leaseId === myLease?.id);
  const myMaintenance = maintenance.filter(m => m.tenantName === 'Marcus Johnson');

  if (!myLease) {
    return <DashboardContent kpis={[]} isTenant properties={properties} payments={payments} maintenance={maintenance} />;
  }

  const leaseStart = new Date(myLease.startDate).getTime();
  const leaseEnd = new Date(myLease.endDate).getTime();
  const now = Date.now();
  const leaseProgress = Math.min(100, Math.round(((now - leaseStart) / (leaseEnd - leaseStart)) * 100));
  const daysLeft = Math.max(0, Math.round((leaseEnd - now) / (1000 * 60 * 60 * 24)));

  const kpis: KPICard[] = [
    { label: 'Monthly Rent', value: `$${myLease.rentAmount.toLocaleString()}`, change: 'Due 1st of month', changeType: 'neutral', icon: '💳', color: 'var(--primary)' },
    { label: 'Lease Expires', value: `${daysLeft}d`, change: myLease.endDate, changeType: daysLeft < 60 ? 'down' : 'neutral', icon: '📅', color: 'var(--amber)' },
    { label: 'My Requests', value: `${myMaintenance.length}`, change: `${myMaintenance.filter(m => m.status === 'in_progress').length} in progress`, changeType: 'neutral', icon: '🔧', color: 'var(--cyan)' },
    { label: 'Payments Made', value: `${myPayments.filter(p => p.status === 'paid').length}`, change: 'On-time record: 100%', changeType: 'up', icon: '✅', color: 'var(--emerald)' },
  ];

  return (
    <>
      {/* Lease Status Card */}
      <div className="lease-status-card">
        <div className="lease-status-header">
          <div>
            <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-primary)' }}>
              {myLease.propertyName}
            </div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
              {myLease.startDate} → {myLease.endDate}
            </div>
          </div>
          <span className="badge badge-success">Active Lease</span>
        </div>
        <div style={{ fontSize: 12.5, color: 'var(--text-secondary)' }}>
          Lease progress — {leaseProgress}% through your term ({daysLeft} days remaining)
        </div>
        <div className="lease-progress-bar">
          <div className="lease-progress-fill" style={{ width: `${leaseProgress}%` }} />
        </div>
      </div>

      <DashboardContent kpis={kpis} isTenant properties={properties} payments={payments} maintenance={maintenance} />
    </>
  );
}

export default function Dashboard() {
  const { user } = useAuth();
  const [properties, setProperties] = useState<Property[]>([]);
  const [payments, setPayments] = useState<Payment[]>([]);
  const [maintenance, setMaintenance] = useState<MaintenanceRequest[]>([]);
  const [leases, setLeases] = useState<Lease[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      getProperties().catch(() => MOCK_PROPERTIES),
      getPayments().catch(() => MOCK_PAYMENTS),
      getMaintenanceRequests().catch(() => MOCK_MAINTENANCE),
      getLeases().catch(() => MOCK_LEASES),
    ]).then(([props, pays, maint, lses]) => {
      setProperties(props);
      setPayments(pays);
      setMaintenance(maint);
      setLeases(lses);
    }).finally(() => setLoading(false));
  }, []);

  if (!user) return null;
  if (loading) return <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>Loading…</div>;

  if (user.role === 'owner') return <OwnerDashboard properties={properties} payments={payments} maintenance={maintenance} leases={leases} />;
  if (user.role === 'manager') return <ManagerDashboard properties={properties} payments={payments} maintenance={maintenance} leases={leases} />;
  return <TenantDashboard properties={properties} payments={payments} maintenance={maintenance} leases={leases} />;
}
