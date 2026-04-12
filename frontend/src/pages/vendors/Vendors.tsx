import { useEffect, useState } from 'react';
import { createVendor, deleteVendor, getVendors, type Vendor, type VendorCreate } from '../../api/vendors';
import { useAuth } from '../../context/AuthContext';

const BLANK_FORM: VendorCreate = { name: '', trade: '', email: '', phone: '', rating: 0, response_time: '' };

export default function Vendors() {
  const { user } = useAuth();
  const canEdit = user?.role === 'owner' || user?.role === 'manager';

  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<VendorCreate>(BLANK_FORM);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    getVendors()
      .then(setVendors)
      .catch(() => setVendors([]))
      .finally(() => setLoading(false));
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name.trim() || !form.trade.trim()) return;
    setSaving(true);
    setError('');
    try {
      const created = await createVendor(form);
      setVendors(prev => [...prev, created]);
      setShowForm(false);
      setForm(BLANK_FORM);
    } catch {
      setError('Failed to add vendor. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteVendor(id);
      setVendors(prev => prev.filter(v => v.id !== id));
    } catch {
      // silently ignore
    }
  };

  return (
    <div className="animate-in">
      <div className="page-header">
        <div>
          <h2>Vendors</h2>
          <p>Preferred service providers for maintenance dispatch</p>
        </div>
        {canEdit && (
          <button className="btn btn-primary" onClick={() => setShowForm(v => !v)}>
            {showForm ? 'Cancel' : '+ Add Vendor'}
          </button>
        )}
      </div>

      {showForm && (
        <div className="card" style={{ marginBottom: 24 }}>
          <h3 style={{ marginBottom: 16 }}>New Vendor</h3>
          <form onSubmit={e => void handleSubmit(e)}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
              <div>
                <label className="form-label">Name *</label>
                <input className="form-input" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} required />
              </div>
              <div>
                <label className="form-label">Trade *</label>
                <input className="form-input" placeholder="e.g. HVAC, Plumbing" value={form.trade} onChange={e => setForm(f => ({ ...f, trade: e.target.value }))} required />
              </div>
              <div>
                <label className="form-label">Email</label>
                <input className="form-input" type="email" value={form.email} onChange={e => setForm(f => ({ ...f, email: e.target.value }))} />
              </div>
              <div>
                <label className="form-label">Phone</label>
                <input className="form-input" value={form.phone} onChange={e => setForm(f => ({ ...f, phone: e.target.value }))} />
              </div>
              <div>
                <label className="form-label">Rating (0–5)</label>
                <input className="form-input" type="number" min={0} max={5} step={0.1} value={form.rating} onChange={e => setForm(f => ({ ...f, rating: parseFloat(e.target.value) || 0 }))} />
              </div>
              <div>
                <label className="form-label">Response Time</label>
                <input className="form-input" placeholder="e.g. 2h average" value={form.response_time} onChange={e => setForm(f => ({ ...f, response_time: e.target.value }))} />
              </div>
            </div>
            {error && <p style={{ color: 'var(--error)', marginTop: 8 }}>{error}</p>}
            <div className="flex gap-2 justify-end mt-3">
              <button type="submit" className="btn btn-primary" disabled={saving}>{saving ? 'Saving…' : 'Save Vendor'}</button>
            </div>
          </form>
        </div>
      )}

      <div className="card">
        {loading ? (
          <p style={{ color: 'var(--text-muted)', padding: 16 }}>Loading vendors…</p>
        ) : vendors.length === 0 ? (
          <p style={{ color: 'var(--text-muted)', padding: 16 }}>No vendors found. Add one above.</p>
        ) : (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Trade</th>
                  <th>Rating</th>
                  <th>Phone</th>
                  <th>Response Time</th>
                  {canEdit && <th></th>}
                </tr>
              </thead>
              <tbody>
                {vendors.map(vendor => (
                  <tr key={vendor.id}>
                    <td style={{ fontWeight: 600 }}>{vendor.name}</td>
                    <td>{vendor.trade}</td>
                    <td>{'⭐'.repeat(Math.round(vendor.rating))} {vendor.rating.toFixed(1)}</td>
                    <td>{vendor.phone}</td>
                    <td>{vendor.response_time}</td>
                    {canEdit && (
                      <td>
                        <button className="btn btn-danger btn-sm" onClick={() => void handleDelete(vendor.id)}>Remove</button>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
