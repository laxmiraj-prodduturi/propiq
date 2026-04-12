import { useEffect, useRef, useState } from 'react';
import { MOCK_PROPERTIES } from '../../data/mockData';
import { createProperty, getProperties } from '../../api/properties';
import type { Property, PropertyType, UnitStatus } from '../../types';

const statusColor: Record<UnitStatus, string> = {
  occupied: 'var(--emerald)',
  vacant: 'var(--primary)',
  maintenance: 'var(--amber)',
};

const PROPERTY_TYPE_OPTIONS: { value: PropertyType; label: string }[] = [
  { value: 'residential', label: 'Residential Home' },
];

const COLOR_OPTIONS = ['#6366f1', '#06b6d4', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];

function AddPropertyPopover({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: (property: Property) => void;
}) {
  const popoverRef = useRef<HTMLDivElement>(null);
  const [form, setForm] = useState({
    name: '',
    address: '',
    city: '',
    state: '',
    zip: '',
    propertyType: 'residential' as PropertyType,
    bedrooms: '3',
    bathrooms: '2',
    sqft: '1600',
    status: 'vacant' as UnitStatus,
    rentAmount: '2800',
    imageColor: '#6366f1',
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (popoverRef.current && !popoverRef.current.contains(event.target as Node)) {
        onClose();
      }
    }

    function handleEscape(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        onClose();
      }
    }

    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleEscape);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleEscape);
    };
  }, [onClose]);

  const handleChange = (field: keyof typeof form, value: string) => {
    setForm(prev => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError('');

    try {
      const property = await createProperty({
        name: form.name.trim(),
        address: form.address.trim(),
        city: form.city.trim(),
        state: form.state.trim(),
        zip: form.zip.trim(),
        property_type: form.propertyType,
        bedrooms: Number(form.bedrooms),
        bathrooms: Number(form.bathrooms),
        sqft: Number(form.sqft),
        status: form.status,
        rent_amount: Number(form.rentAmount),
        image_color: form.imageColor,
      });
      onCreated(property);
      onClose();
    } catch (err: any) {
      setError(err?.message ?? 'Unable to create property');
    } finally {
      setSubmitting(false);
    }
  };

  const isValid = form.name.trim() && form.address.trim() && form.city.trim() && form.state.trim() && form.zip.trim();

  return (
    <div
      ref={popoverRef}
      className="card"
      style={{
        position: 'absolute',
        top: 'calc(100% + 10px)',
        right: 0,
        width: 'min(440px, calc(100vw - 32px))',
        zIndex: 20,
        boxShadow: 'var(--shadow-xl)',
        border: '1px solid var(--border-strong)',
      }}
    >
      <div className="section-header" style={{ marginBottom: 16 }}>
        <span className="section-title">Add Property</span>
        <button className="btn btn-ghost btn-sm" type="button" onClick={onClose}>✕</button>
      </div>

      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label className="form-label">Property Name</label>
          <input className="form-input" value={form.name} onChange={e => handleChange('name', e.target.value)} placeholder="Skyline Residences" />
        </div>

        <div className="form-group">
          <label className="form-label">Street Address</label>
          <input className="form-input" value={form.address} onChange={e => handleChange('address', e.target.value)} placeholder="420 Park Avenue" />
        </div>

        <div className="two-col" style={{ marginBottom: 14 }}>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label className="form-label">City</label>
            <input className="form-input" value={form.city} onChange={e => handleChange('city', e.target.value)} placeholder="New York" />
          </div>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label className="form-label">State</label>
            <input className="form-input" value={form.state} onChange={e => handleChange('state', e.target.value)} placeholder="NY" maxLength={32} />
          </div>
        </div>

        <div className="two-col" style={{ marginBottom: 14 }}>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label className="form-label">ZIP</label>
            <input className="form-input" value={form.zip} onChange={e => handleChange('zip', e.target.value)} placeholder="10022" />
          </div>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label className="form-label">Property Type</label>
            <select className="form-input form-select" value={form.propertyType} onChange={e => handleChange('propertyType', e.target.value)}>
              {PROPERTY_TYPE_OPTIONS.map(option => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
          </div>
        </div>

        <div className="two-col" style={{ marginBottom: 14 }}>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label className="form-label">Bedrooms</label>
            <input className="form-input" type="number" min="0" value={form.bedrooms} onChange={e => handleChange('bedrooms', e.target.value)} />
          </div>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label className="form-label">Bathrooms</label>
            <input className="form-input" type="number" min="0" step="0.5" value={form.bathrooms} onChange={e => handleChange('bathrooms', e.target.value)} />
          </div>
        </div>

        <div className="two-col" style={{ marginBottom: 14 }}>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label className="form-label">Square Feet</label>
            <input className="form-input" type="number" min="0" value={form.sqft} onChange={e => handleChange('sqft', e.target.value)} />
          </div>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label className="form-label">Monthly Rent</label>
            <input className="form-input" type="number" min="0" value={form.rentAmount} onChange={e => handleChange('rentAmount', e.target.value)} />
          </div>
        </div>

        <div className="form-group">
          <label className="form-label">Occupancy Status</label>
          <select className="form-input form-select" value={form.status} onChange={e => handleChange('status', e.target.value)}>
            <option value="vacant">Vacant</option>
            <option value="occupied">Occupied</option>
            <option value="maintenance">Maintenance</option>
          </select>
        </div>

        <div className="form-group">
          <label className="form-label">Accent Color</label>
          <div className="flex gap-2 flex-wrap">
            {COLOR_OPTIONS.map(color => (
              <button
                key={color}
                type="button"
                onClick={() => handleChange('imageColor', color)}
                style={{
                  width: 28,
                  height: 28,
                  borderRadius: '50%',
                  border: form.imageColor === color ? '2px solid var(--text-primary)' : '1px solid var(--border-default)',
                  background: color,
                  boxShadow: form.imageColor === color ? `0 0 0 2px ${color}55` : 'none',
                }}
                aria-label={`Select ${color}`}
              />
            ))}
          </div>
        </div>

        {error && (
          <div style={{ color: 'var(--danger)', fontSize: 12.5, marginBottom: 14 }}>
            {error}
          </div>
        )}

        <div className="flex gap-2 justify-end">
          <button className="btn btn-ghost" type="button" onClick={onClose}>Cancel</button>
          <button className="btn btn-primary" type="submit" disabled={!isValid || submitting}>
            {submitting ? 'Creating...' : 'Create Property'}
          </button>
        </div>
      </form>
    </div>
  );
}

function PropertyCard({ property, onClick }: { property: Property; onClick: () => void }) {
  const status = property.status;
  const rent = property.rentAmount;

  return (
    <div className="property-card" onClick={onClick}>
      <div className="property-banner" style={{ background: `linear-gradient(135deg, ${property.imageColor}33 0%, ${property.imageColor}15 100%)` }}>
        <div className="property-banner-pattern" />
        <span className="property-banner-icon">🏡</span>
        <div style={{ position: 'absolute', top: 12, right: 12 }}>
          <span className="badge badge-muted" style={{ fontSize: 10 }}>single family</span>
        </div>
        <div style={{ position: 'absolute', top: 12, left: 12 }}>
          <span style={{ fontSize: 11, fontWeight: 700, color: property.imageColor, background: `${property.imageColor}22`, padding: '3px 8px', borderRadius: 'var(--radius-full)', border: `1px solid ${property.imageColor}44` }}>
            {status}
          </span>
        </div>
      </div>

      <div className="property-info">
        <div className="property-name">{property.name}</div>
        <div className="property-address">{property.address}, {property.city}, {property.state} {property.zip}</div>

        <div className="property-stats">
          <div className="property-stat">
            <div className="property-stat-value">1</div>
            <div className="property-stat-label">Home</div>
          </div>
          <div className="property-stat">
            <div className="property-stat-value" style={{ color: statusColor[status] }}>{status}</div>
            <div className="property-stat-label">Status</div>
          </div>
          <div className="property-stat">
            <div className="property-stat-value">${rent.toLocaleString()}</div>
            <div className="property-stat-label">Monthly Rent</div>
          </div>
        </div>
      </div>
    </div>
  );
}

function PropertyDetail({ property, onBack }: { property: Property; onBack: () => void }) {
  const statusBadge: Record<UnitStatus, string> = {
    occupied: 'badge-success',
    vacant: 'badge-primary',
    maintenance: 'badge-warning',
  };
  const status = property.status;
  const monthlyRent = property.rentAmount;

  return (
    <div className="animate-in">
      <div className="page-header">
        <div>
          <button className="btn btn-ghost btn-sm" onClick={onBack} style={{ marginBottom: 8, paddingLeft: 0 }}>
            ← Back to Homes
          </button>
          <h2>{property.name}</h2>
          <p>{property.address}, {property.city}, {property.state} · single-family residential</p>
        </div>
      </div>

      <div className="stats-row">
        <div className="stat-cell">
          <div className="stat-cell-value">1</div>
          <div className="stat-cell-label">Home</div>
        </div>
        <div className="stat-cell">
          <div className="stat-cell-value" style={{ color: statusColor[status] }}>{status}</div>
          <div className="stat-cell-label">Occupancy</div>
        </div>
        <div className="stat-cell">
          <div className="stat-cell-value">{property.bedrooms}</div>
          <div className="stat-cell-label">Bedrooms</div>
        </div>
        <div className="stat-cell">
          <div className="stat-cell-value">${monthlyRent.toLocaleString()}</div>
          <div className="stat-cell-label">Monthly Rent</div>
        </div>
      </div>

      <div className="card">
        <div className="section-header">
          <span className="section-title">Home Details</span>
          <span className={`badge ${statusBadge[status]}`}>{status}</span>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 16 }}>
          <div>
            <div className="form-label">Beds / Baths</div>
            <div>{`${property.bedrooms} bd / ${property.bathrooms} ba`}</div>
          </div>
          <div>
            <div className="form-label">Square Footage</div>
            <div>{`${property.sqft.toLocaleString()} sqft`}</div>
          </div>
          <div>
            <div className="form-label">Monthly Rent</div>
            <div>{`$${property.rentAmount.toLocaleString()}`}</div>
          </div>
          <div>
            <div className="form-label">Occupancy Status</div>
            <div>{property.status}</div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function Properties() {
  const [properties, setProperties] = useState<Property[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Property | null>(null);
  const [search, setSearch] = useState('');
  const [showAddPopover, setShowAddPopover] = useState(false);

  useEffect(() => {
    getProperties()
      .then(setProperties)
      .catch(() => setProperties(MOCK_PROPERTIES))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>Loading…</div>;

  if (selected) return <PropertyDetail property={selected} onBack={() => setSelected(null)} />;

  const filtered = properties.filter(p => {
    if (search && !p.name.toLowerCase().includes(search.toLowerCase()) && !p.city.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  const occupiedHomes = properties.filter(property => property.status === 'occupied').length;
  const totalRent = properties.reduce((sum, property) => sum + property.rentAmount, 0);

  return (
    <div className="animate-in">
      <div className="page-header">
        <div>
          <h2>Homes</h2>
          <p>{properties.length} homes · {occupiedHomes} occupied · ${(totalRent / 1000).toFixed(1)}k scheduled monthly rent</p>
        </div>
        <div style={{ position: 'relative' }}>
          <button className="btn btn-primary" onClick={() => setShowAddPopover(prev => !prev)}>
            + Add Home
          </button>
          {showAddPopover && (
            <AddPropertyPopover
              onClose={() => setShowAddPopover(false)}
              onCreated={property => {
                setProperties(prev => [property, ...prev]);
                setSelected(property);
              }}
            />
          )}
        </div>
      </div>

      <div className="filter-bar">
        <div className="search-input-wrap">
          <span className="search-icon">🔍</span>
          <input
            className="form-input search-input"
            placeholder="Search homes…"
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>
      </div>

      {filtered.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">🏚️</div>
          <div className="empty-title">No homes found</div>
          <div className="empty-desc">Try adjusting your search or add a home</div>
        </div>
      ) : (
        <div className="property-grid">
          {filtered.map(p => (
            <PropertyCard key={p.id} property={p} onClick={() => setSelected(p)} />
          ))}
        </div>
      )}
    </div>
  );
}
