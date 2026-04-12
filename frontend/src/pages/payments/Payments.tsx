import { useState, useEffect } from 'react';
import { MOCK_PAYMENTS } from '../../data/mockData';
import { getPayments } from '../../api/payments';
import type { Payment, PaymentStatus } from '../../types';

const statusBadge: Record<PaymentStatus, string> = {
  paid: 'badge-success',
  pending: 'badge-info',
  late: 'badge-warning',
  failed: 'badge-danger',
};

const statusIcon: Record<PaymentStatus, string> = {
  paid: '✅',
  pending: '⏳',
  late: '⚠️',
  failed: '❌',
};

function PaymentModal({ onClose }: { onClose: () => void }) {
  const [amount, setAmount] = useState('2800');
  const [method, setMethod] = useState('ach');
  const [step, setStep] = useState(1);

  const handlePay = () => setStep(2);

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <span className="modal-title">{step === 1 ? 'Make a Payment' : '✅ Payment Submitted'}</span>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>

        {step === 1 ? (
          <>
            <div style={{ background: 'var(--primary-10)', border: '1px solid var(--primary-20)', borderRadius: 'var(--radius)', padding: '14px 16px', marginBottom: 20 }}>
              <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 4 }}>Rent Due</div>
              <div style={{ fontSize: 22, fontWeight: 800, color: 'var(--text-primary)' }}>$2,800.00</div>
              <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 2 }}>Maple Street Home · Due Jan 1, 2025</div>
            </div>

            <div className="form-group">
              <label className="form-label">Payment Amount</label>
              <input className="form-input" type="text" value={`$${amount}`} onChange={e => setAmount(e.target.value.replace('$', ''))} />
            </div>

            <div className="form-group">
              <label className="form-label">Payment Method</label>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {[
                  { id: 'ach', label: 'Bank Transfer (ACH)', sub: 'Checking account ending in ****4521', icon: '🏦' },
                  { id: 'card', label: 'Credit / Debit Card', sub: 'Visa ending in ****8832', icon: '💳' },
                ].map(m => (
                  <div
                    key={m.id}
                    style={{
                      display: 'flex', alignItems: 'center', gap: 12,
                      padding: '12px 14px', borderRadius: 'var(--radius-sm)',
                      border: `1.5px solid ${method === m.id ? 'var(--primary)' : 'var(--border-default)'}`,
                      background: method === m.id ? 'var(--primary-10)' : 'var(--bg-input)',
                      cursor: 'pointer', transition: 'all var(--t-fast) var(--ease)',
                    }}
                    onClick={() => setMethod(m.id)}
                  >
                    <span style={{ fontSize: 22 }}>{m.icon}</span>
                    <div>
                      <div style={{ fontSize: 13.5, fontWeight: 600, color: method === m.id ? 'var(--primary-light)' : 'var(--text-primary)' }}>{m.label}</div>
                      <div style={{ fontSize: 11.5, color: 'var(--text-muted)' }}>{m.sub}</div>
                    </div>
                    <div style={{ marginLeft: 'auto', width: 16, height: 16, borderRadius: '50%', border: `2px solid ${method === m.id ? 'var(--primary)' : 'var(--border-default)'}`, background: method === m.id ? 'var(--primary)' : 'transparent' }} />
                  </div>
                ))}
              </div>
            </div>

            <div className="flex gap-2 justify-end mt-4">
              <button className="btn btn-ghost" onClick={onClose}>Cancel</button>
              <button className="btn btn-primary btn-lg" onClick={handlePay}>
                Pay ${amount}
              </button>
            </div>
          </>
        ) : (
          <div style={{ textAlign: 'center', padding: '20px 0' }}>
            <div style={{ fontSize: 48, marginBottom: 16 }}>✅</div>
            <div style={{ fontSize: 20, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 8 }}>Payment Successful</div>
            <div style={{ fontSize: 14, color: 'var(--text-secondary)', marginBottom: 4 }}>${amount} submitted via {method === 'ach' ? 'ACH Transfer' : 'Card'}</div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 24 }}>Transaction ref: TXN-{Date.now().toString().slice(-8)}</div>
            <button className="btn btn-primary" onClick={onClose}>Done</button>
          </div>
        )}
      </div>
    </div>
  );
}

export default function Payments() {
  const [payments, setPayments] = useState<Payment[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<PaymentStatus | 'all'>('all');
  const [showPayModal, setShowPayModal] = useState(false);

  useEffect(() => {
    getPayments()
      .then(setPayments)
      .catch(() => setPayments(MOCK_PAYMENTS))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>Loading…</div>;

  const paid = payments.filter(p => p.status === 'paid');
  const pending = payments.filter(p => p.status === 'pending');
  const late = payments.filter(p => p.status === 'late');
  const failed = payments.filter(p => p.status === 'failed');

  const totalCollected = paid.reduce((s, p) => s + p.amount, 0);
  const totalPending = [...pending, ...late].reduce((s, p) => s + p.amount + p.lateFee, 0);

  const filtered = payments.filter(p => filter === 'all' || p.status === filter);

  return (
    <div className="animate-in">
      <div className="page-header">
        <div>
          <h2>Payments</h2>
          <p>Track rent collection and payment history</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowPayModal(true)}>
          💳 Pay Rent
        </button>
      </div>

      <div className="kpi-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))' }}>
        {[
          { label: 'Collected', value: `$${(totalCollected / 1000).toFixed(1)}k`, icon: '✅', color: 'var(--emerald)', count: paid.length },
          { label: 'Pending', value: `$${pending.reduce((s, p) => s + p.amount, 0).toLocaleString()}`, icon: '⏳', color: 'var(--blue)', count: pending.length },
          { label: 'Late / Overdue', value: `$${totalPending.toLocaleString()}`, icon: '⚠️', color: 'var(--amber)', count: late.length },
          { label: 'Failed', value: `${failed.length}`, icon: '❌', color: 'var(--rose)', count: failed.length },
        ].map(kpi => (
          <div key={kpi.label} className="kpi-card">
            <div className="kpi-accent" style={{ background: kpi.color }} />
            <div className="kpi-icon-wrap" style={{ background: `${kpi.color}18` }}>
              <span style={{ fontSize: 18 }}>{kpi.icon}</span>
            </div>
            <div className="kpi-label">{kpi.label}</div>
            <div className="kpi-value">{kpi.value}</div>
            <div className="kpi-change neutral">{kpi.count} transaction{kpi.count !== 1 ? 's' : ''}</div>
          </div>
        ))}
      </div>

      <div className="filter-bar">
        <div className="tabs">
          {(['all', 'paid', 'pending', 'late', 'failed'] as const).map(s => (
            <button key={s} className={`tab ${filter === s ? 'active' : ''}`} onClick={() => setFilter(s)}>
              {s.charAt(0).toUpperCase() + s.slice(1)}
              {s !== 'all' && (
                <span style={{ marginLeft: 5, fontSize: 10, fontWeight: 700 }}>
                  ({payments.filter(p => p.status === s).length})
                </span>
              )}
            </button>
          ))}
        </div>
      </div>

      <div className="card">
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Tenant</th>
                <th>Property</th>
                <th>Amount</th>
                <th>Late Fee</th>
                <th>Due Date</th>
                <th>Paid Date</th>
                <th>Method</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(pay => (
                <tr key={pay.id}>
                  <td style={{ fontWeight: 600 }}>{pay.tenantName}</td>
                  <td className="muted">{pay.propertyName}</td>
                  <td style={{ fontWeight: 700 }}>${pay.amount.toLocaleString()}</td>
                  <td style={{ color: pay.lateFee > 0 ? 'var(--amber)' : 'var(--text-muted)' }}>
                    {pay.lateFee > 0 ? `+$${pay.lateFee}` : '—'}
                  </td>
                  <td className="muted">{pay.dueDate}</td>
                  <td className="muted">{pay.paidDate ?? '—'}</td>
                  <td className="muted">{pay.paymentMethod || '—'}</td>
                  <td>
                    <span className={`badge ${statusBadge[pay.status]}`}>
                      {statusIcon[pay.status]} {pay.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {filtered.length === 0 && (
          <div className="empty-state">
            <div className="empty-icon">💸</div>
            <div className="empty-title">No payments found</div>
          </div>
        )}
      </div>

      {showPayModal && <PaymentModal onClose={() => setShowPayModal(false)} />}
    </div>
  );
}
