import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import type { Role } from '../../types';
import { getDefaultAppPath } from '../../routes';

const ROLES: { role: Role; icon: string; label: string; color: string }[] = [
  { role: 'owner', icon: '🏛️', label: 'Owner', color: 'var(--amber)' },
  { role: 'manager', icon: '🗂️', label: 'Manager', color: 'var(--primary-light)' },
  { role: 'tenant', icon: '🏠', label: 'Tenant', color: 'var(--emerald)' },
];

const DEMO_ACCOUNTS = [
  { role: 'owner' as Role, name: 'Alex Thompson', email: 'alex.thompson@example.com', color: 'var(--amber)', chip: 'Owner' },
  { role: 'manager' as Role, name: 'Sarah Chen', email: 'sarah.chen@example.com', color: 'var(--primary-light)', chip: 'Manager' },
  { role: 'tenant' as Role, name: 'Marcus Johnson', email: 'marcus.johnson@example.com', color: 'var(--emerald)', chip: 'Tenant' },
];

export default function Login() {
  const [selectedRole, setSelectedRole] = useState<Role>('owner');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleRoleSelect = (role: Role) => {
    setSelectedRole(role);
    const demo = DEMO_ACCOUNTS.find(a => a.role === role);
    if (demo) setEmail(demo.email);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const loggedInUser = await login(email, password);
      navigate(getDefaultAppPath(loggedInUser.role));
    } catch (err: any) {
      setError(err.message ?? 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  const handleDemoLogin = async (acc: typeof DEMO_ACCOUNTS[0]) => {
    setLoading(true);
    setError('');
    try {
      const loggedInUser = await login(acc.email, 'demo1234');
      navigate(getDefaultAppPath(loggedInUser.role));
    } catch (err: any) {
      setError(err.message ?? 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      {/* Hero Panel */}
      <div className="login-hero">
        <div className="hero-content">
          <div className="hero-logo">
            <div className="hero-logo-icon">Q</div>
            <div className="hero-logo-text">QuantumQuestProperties</div>
          </div>

          <h1 className="hero-headline">
            Intelligent Property<br />
            <span>Management Platform</span>
          </h1>

          <p className="hero-sub">
            Streamline leases, maintenance, payments, and tenant communications —
            all powered by an AI-driven assistant built for modern property teams.
          </p>

          <div className="hero-features">
            {[
              { icon: '🤖', label: 'AI-Powered Assistant', desc: 'Claude AI handles triage, reporting & renewals', color: 'var(--primary-10)' },
              { icon: '⚡', label: 'Real-Time Notifications', desc: 'Instant alerts for payments, maintenance & leases', color: 'rgba(245,158,11,0.1)' },
              { icon: '🛡️', label: 'Role-Based Access', desc: 'Owners, Managers & Tenants get tailored views', color: 'rgba(16,185,129,0.1)' },
              { icon: '📊', label: 'Financial Analytics', desc: 'Occupancy rates, rent collection & owner reports', color: 'rgba(6,182,212,0.1)' },
            ].map(f => (
              <div key={f.label} className="hero-feature">
                <div className="hero-feature-icon" style={{ background: f.color }}>
                  {f.icon}
                </div>
                <div>
                  <div style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: 13.5 }}>{f.label}</div>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{f.desc}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Form Panel */}
      <div className="login-form-panel">
        <div className="login-card">
          <h2 className="login-title">Welcome back</h2>
          <p className="login-subtitle">Sign in to your QuantumQuestProperties account</p>

          {/* Role Selector */}
          <div className="role-selector">
            {ROLES.map(r => (
              <button
                key={r.role}
                className={`role-btn ${selectedRole === r.role ? 'selected' : ''}`}
                onClick={() => handleRoleSelect(r.role)}
                type="button"
              >
                <span className="role-btn-icon">{r.icon}</span>
                <span className="role-btn-label" style={selectedRole === r.role ? { color: r.color } : {}}>
                  {r.label}
                </span>
              </button>
            ))}
          </div>

          {error && (
            <div style={{ background: 'rgba(239,68,68,0.12)', border: '1px solid rgba(239,68,68,0.3)', borderRadius: 'var(--radius-sm)', padding: '10px 14px', marginBottom: 16, fontSize: 13, color: 'var(--danger)' }}>
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label className="form-label">Email Address</label>
              <input
                type="email"
                className="form-input"
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="you@example.com"
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label">Password</label>
              <input
                type="password"
                className="form-input"
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="••••••••"
                required
              />
            </div>

            <button
              type="submit"
              className="btn btn-primary w-full btn-lg"
              style={{ marginBottom: 20 }}
              disabled={loading}
            >
              {loading ? 'Signing in…' : 'Sign In'}
            </button>
          </form>

          <div style={{ position: 'relative', textAlign: 'center', marginBottom: 20 }}>
            <div className="divider" style={{ position: 'absolute', top: '50%', left: 0, right: 0, margin: 0 }} />
            <span style={{ background: 'rgba(10,16,30,0.95)', padding: '0 12px', fontSize: 12, color: 'var(--text-muted)', position: 'relative' }}>
              or try a demo account
            </span>
          </div>

          <div>
            {DEMO_ACCOUNTS.map(acc => (
              <button
                key={acc.role}
                className="demo-login-btn"
                onClick={() => handleDemoLogin(acc)}
                disabled={loading}
              >
                <div>
                  <div style={{ fontWeight: 600, fontSize: 13.5 }}>{acc.name}</div>
                  <div style={{ fontSize: 11.5, color: 'var(--text-muted)' }}>{acc.email}</div>
                </div>
                <span className="role-chip badge" style={{ background: `${acc.color}20`, color: acc.color, border: `1px solid ${acc.color}40` }}>
                  {acc.chip}
                </span>
              </button>
            ))}
          </div>

          <p style={{ textAlign: 'center', fontSize: 12, color: 'var(--text-muted)', marginTop: 24 }}>
            Connected to FastAPI backend · JWT authentication
          </p>
        </div>
      </div>
    </div>
  );
}
