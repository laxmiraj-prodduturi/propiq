import { useAuth } from '../../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { MOCK_PROPERTIES, MOCK_PAYMENTS, MOCK_MAINTENANCE, MOCK_LEASES } from '../../data/mockData';
import { getProperties } from '../../api/properties';
import { getPayments } from '../../api/payments';
import { getMaintenanceRequests } from '../../api/maintenance';
import { getLeases } from '../../api/leases';
import type { Property, Payment, MaintenanceRequest, Lease, KPICard } from '../../types';
import { Icon } from '../../components/Icons';

// ── Occupancy bar ─────────────────────────────────────────────────────────────
function OccupancyBar({ properties }: { properties: Property[] }) {
  const occupied    = properties.filter(p => p.status === 'occupied').length;
  const vacant      = properties.filter(p => p.status === 'vacant').length;
  const maintenance = properties.filter(p => p.status === 'maintenance').length;
  const total = properties.length;
  if (total === 0) return null;
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
        <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>Occupancy Overview</span>
        <span style={{ fontSize: 13, fontWeight: 700 }}>{Math.round((occupied / total) * 100)}%</span>
      </div>
      <div style={{ display: 'flex', height: 6, borderRadius: 'var(--radius-full)', overflow: 'hidden', gap: 2 }}>
        <div style={{ flex: occupied, background: 'var(--emerald)' }} />
        <div style={{ flex: vacant, background: 'var(--primary)' }} />
        {maintenance > 0 && <div style={{ flex: maintenance, background: 'var(--amber)' }} />}
      </div>
      <div style={{ display: 'flex', gap: 16, marginTop: 8 }}>
        {[
          { label: 'Occupied', count: occupied, color: 'var(--emerald)' },
          { label: 'Vacant',   count: vacant,   color: 'var(--primary)' },
          { label: 'Under maintenance', count: maintenance, color: 'var(--amber)' },
        ].filter(s => s.count > 0).map(s => (
          <div key={s.label} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
            <div style={{ width: 7, height: 7, borderRadius: '50%', background: s.color }} />
            <span style={{ fontSize: 11.5, color: 'var(--text-muted)' }}>{s.label}: {s.count}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Shared dashboard body ─────────────────────────────────────────────────────
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
  const recentPayments  = payments.slice(0, 4);

  const urgencyColor: Record<string, string> = {
    emergency: 'var(--rose)',
    high:      'var(--amber)',
    medium:    'var(--primary)',
    low:       'var(--text-muted)',
  };

  const statusBadge: Record<string, string> = {
    submitted:   'badge-muted',
    assigned:    'badge-info',
    in_progress: 'badge-warning',
    resolved:    'badge-success',
    closed:      'badge-muted',
  };

  const paymentBadge: Record<string, string> = {
    paid:    'badge-success',
    pending: 'badge-info',
    late:    'badge-warning',
    failed:  'badge-danger',
  };

  return (
    <>
      {/* KPI grid */}
      <div className="kpi-grid">
        {kpis.map(kpi => (
          <div key={kpi.label} className="kpi-card">
            <div className="kpi-accent" style={{ background: kpi.color }} />
            <div className="kpi-icon-wrap" style={{ background: `${kpi.color}18`, color: kpi.color }}>
              {kpi.icon}
            </div>
            <div className="kpi-label">{kpi.label}</div>
            <div className="kpi-value">{kpi.value}</div>
            <div className={`kpi-change ${kpi.changeType}`}>
              {kpi.changeType === 'up'   && <Icon.trendUp   size={12} />}
              {kpi.changeType === 'down' && <Icon.trendDown  size={12} />}
              {kpi.change}
            </div>
          </div>
        ))}
      </div>

      {/* Two-column: Maintenance + Payments */}
      <div className="two-col">
        <div className="card">
          <div className="section-header">
            <span className="section-title">Open Maintenance</span>
            <button className="btn btn-ghost btn-sm" onClick={() => navigate('/maintenance')}>View all</button>
          </div>
          {openMaintenance.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon"><Icon.check size={32} /></div>
              <div className="empty-title">All clear</div>
              <div className="empty-desc">No open work orders</div>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              {openMaintenance.slice(0, 4).map(req => (
                <div key={req.id} className="list-row">
                  <div
                    className="urgency-dot"
                    style={{
                      background: urgencyColor[req.urgency],
                      boxShadow: req.urgency === 'emergency' ? `0 0 8px ${urgencyColor[req.urgency]}` : 'none',
                    }}
                  />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div className="list-row-title">{req.category}</div>
                    <div className="list-row-sub">{req.propertyName}</div>
                  </div>
                  <span className={`badge ${statusBadge[req.status]}`}>
                    {req.status.replace('_', ' ')}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="card">
          <div className="section-header">
            <span className="section-title">Recent Payments</span>
            <button className="btn btn-ghost btn-sm" onClick={() => navigate('/payments')}>View all</button>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            {recentPayments.map(pay => (
              <div key={pay.id} className="list-row">
                <div className="list-row-avatar">
                  {pay.tenantName.split(' ').map(n => n[0]).join('').slice(0, 2)}
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div className="list-row-title">{pay.tenantName}</div>
                  <div className="list-row-sub">{pay.propertyName}</div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: 13.5, fontWeight: 700, marginBottom: 3 }}>
                    ${pay.amount.toLocaleString()}
                  </div>
                  <span className={`badge ${paymentBadge[pay.status]}`}>{pay.status}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Occupancy */}
      {!isTenant && properties.length > 0 && (
        <div className="card" style={{ marginTop: 20 }}>
          <OccupancyBar properties={properties} />
        </div>
      )}
    </>
  );
}

// ── Role dashboards ───────────────────────────────────────────────────────────
function OwnerDashboard({ properties, payments, maintenance }: {
  properties: Property[]; payments: Payment[]; maintenance: MaintenanceRequest[];
}) {
  const occupied       = properties.filter(p => p.status === 'occupied').length;
  const monthlyRevenue = properties.filter(p => p.status === 'occupied').reduce((s, p) => s + p.rentAmount, 0);
  const pending        = payments.filter(p => p.status === 'pending' || p.status === 'late');

  const kpis: KPICard[] = [
    { label: 'Total Properties', value: `${properties.length}`, change: 'Residential', changeType: 'neutral', icon: <Icon.home size={20} />, color: 'var(--primary)' },
    { label: 'Occupied',         value: `${occupied}`,          change: `${properties.length - occupied} vacant`, changeType: 'neutral', icon: <Icon.users size={20} />, color: 'var(--cyan)' },
    { label: 'Monthly Revenue',  value: `$${(monthlyRevenue / 1000).toFixed(1)}k`, change: '+4.2% vs last month', changeType: 'up', icon: <Icon.dollar size={20} />, color: 'var(--emerald)' },
    { label: 'Pending Payments', value: `${pending.length}`,    change: 'Needs attention', changeType: pending.length > 0 ? 'down' : 'neutral', icon: <Icon.alert size={20} />, color: 'var(--amber)' },
  ];

  return <DashboardContent kpis={kpis} properties={properties} payments={payments} maintenance={maintenance} />;
}

function ManagerDashboard({ properties, payments, maintenance, leases }: {
  properties: Property[]; payments: Payment[]; maintenance: MaintenanceRequest[]; leases: Lease[];
}) {
  const openMaintenance = maintenance.filter(m => m.status !== 'resolved' && m.status !== 'closed').length;
  const activeLeases    = leases.filter(l => l.status === 'active').length;
  const collectionRate  = payments.length > 0
    ? Math.round((payments.filter(p => p.status === 'paid').length / payments.length) * 100)
    : 0;

  const kpis: KPICard[] = [
    { label: 'Managed Properties', value: `${properties.length}`, change: 'Residential portfolio', changeType: 'neutral', icon: <Icon.building size={20} />, color: 'var(--primary)' },
    { label: 'Active Leases',      value: `${activeLeases}`,      change: '1 expiring soon', changeType: 'neutral', icon: <Icon.lease size={20} />, color: 'var(--cyan)' },
    { label: 'Open Work Orders',   value: `${openMaintenance}`,   change: 'Review required', changeType: openMaintenance > 0 ? 'down' : 'neutral', icon: <Icon.wrench size={20} />, color: 'var(--rose)' },
    { label: 'Collection Rate',    value: `${collectionRate}%`,   change: '+3% vs last month', changeType: 'up', icon: <Icon.activity size={20} />, color: 'var(--emerald)' },
  ];

  return <DashboardContent kpis={kpis} properties={properties} payments={payments} maintenance={maintenance} />;
}

function TenantDashboard({ properties, payments, maintenance, leases }: {
  properties: Property[]; payments: Payment[]; maintenance: MaintenanceRequest[]; leases: Lease[];
}) {
  const myLease      = leases[0] ?? MOCK_LEASES[0];
  const myPayments   = payments.filter(p => p.leaseId === myLease?.id);
  const myMaintenance = maintenance.filter(m => m.tenantName === 'Marcus Johnson');

  if (!myLease) return <DashboardContent kpis={[]} isTenant properties={properties} payments={payments} maintenance={maintenance} />;

  const leaseStart    = new Date(myLease.startDate).getTime();
  const leaseEnd      = new Date(myLease.endDate).getTime();
  const now           = Date.now();
  const leaseProgress = Math.min(100, Math.round(((now - leaseStart) / (leaseEnd - leaseStart)) * 100));
  const daysLeft      = Math.max(0, Math.round((leaseEnd - now) / (1000 * 60 * 60 * 24)));

  const kpis: KPICard[] = [
    { label: 'Monthly Rent',   value: `$${myLease.rentAmount.toLocaleString()}`, change: 'Due 1st of month', changeType: 'neutral', icon: <Icon.card size={20} />, color: 'var(--primary)' },
    { label: 'Lease Expires',  value: `${daysLeft}d`, change: myLease.endDate, changeType: daysLeft < 60 ? 'down' : 'neutral', icon: <Icon.calendar size={20} />, color: 'var(--amber)' },
    { label: 'My Requests',    value: `${myMaintenance.length}`, change: `${myMaintenance.filter(m => m.status === 'in_progress').length} in progress`, changeType: 'neutral', icon: <Icon.wrench size={20} />, color: 'var(--cyan)' },
    { label: 'Payments Made',  value: `${myPayments.filter(p => p.status === 'paid').length}`, change: 'On-time: 100%', changeType: 'up', icon: <Icon.check size={20} />, color: 'var(--emerald)' },
  ];

  return (
    <>
      {/* Lease status card */}
      <div className="lease-status-card">
        <div className="lease-status-header">
          <div>
            <div style={{ fontSize: 14, fontWeight: 700 }}>{myLease.propertyName}</div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
              {myLease.startDate} → {myLease.endDate}
            </div>
          </div>
          <span className="badge badge-success">Active</span>
        </div>
        <div style={{ fontSize: 12.5, color: 'var(--text-secondary)', marginBottom: 8 }}>
          {leaseProgress}% through your term · {daysLeft} days remaining
        </div>
        <div className="lease-progress-bar">
          <div className="lease-progress-fill" style={{ width: `${leaseProgress}%` }} />
        </div>
      </div>

      <DashboardContent kpis={kpis} isTenant properties={properties} payments={payments} maintenance={maintenance} />
    </>
  );
}

// ── Root ──────────────────────────────────────────────────────────────────────
export default function Dashboard() {
  const { user } = useAuth();
  const [properties,  setProperties]  = useState<Property[]>([]);
  const [payments,    setPayments]    = useState<Payment[]>([]);
  const [maintenance, setMaintenance] = useState<MaintenanceRequest[]>([]);
  const [leases,      setLeases]      = useState<Lease[]>([]);
  const [loading,     setLoading]     = useState(true);

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
  if (loading) return (
    <div style={{ padding: 60, textAlign: 'center', color: 'var(--text-muted)' }}>
      Loading…
    </div>
  );

  if (user.role === 'owner')   return <OwnerDashboard   properties={properties} payments={payments} maintenance={maintenance} />;
  if (user.role === 'manager') return <ManagerDashboard properties={properties} payments={payments} maintenance={maintenance} leases={leases} />;
  return                              <TenantDashboard  properties={properties} payments={payments} maintenance={maintenance} leases={leases} />;
}
