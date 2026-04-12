import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import type { Role } from '../../types';
import { getAppPath, stripRolePrefix, type AppPage } from '../../routes';

interface NavItem {
  icon: string;
  label: string;
  path: string;
  roles: Role[];
  badge?: number;
}

const NAV_ITEMS: NavItem[] = [
  { icon: '⬡', label: 'Dashboard', path: '/dashboard', roles: ['owner', 'manager', 'tenant'] },
  { icon: '🏡', label: 'Homes', path: '/properties', roles: ['owner', 'manager'] },
  { icon: '📋', label: 'Leases', path: '/leases', roles: ['owner', 'manager', 'tenant'] },
  { icon: '🔧', label: 'Maintenance', path: '/maintenance', roles: ['owner', 'manager', 'tenant'] },
  { icon: '💳', label: 'Payments', path: '/payments', roles: ['owner', 'manager', 'tenant'] },
  { icon: '📁', label: 'Documents', path: '/documents', roles: ['owner', 'manager', 'tenant'] },
  { icon: '🤖', label: 'AI Assistant', path: '/ai-chat', roles: ['owner', 'manager', 'tenant'] },
];

const MANAGEMENT_ITEMS: NavItem[] = [
  { icon: '🔔', label: 'Notifications', path: '/notifications', roles: ['owner', 'manager', 'tenant'], badge: 3 },
];

export default function Sidebar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  if (!user) return null;

  const roleColors: Record<Role, string> = {
    owner: 'var(--amber)',
    manager: 'var(--primary-light)',
    tenant: 'var(--emerald)',
  };

  const roleLabels: Record<Role, string> = {
    owner: 'Property Owner',
    manager: 'Property Manager',
    tenant: 'Tenant',
  };

  const filtered = (items: NavItem[]) =>
    items.filter(i => i.roles.includes(user.role));
  const currentPath = stripRolePrefix(location.pathname);

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="sidebar-logo">Q</div>
        <div className="sidebar-brand-text">
          <div className="sidebar-brand-name">QuantumQuest</div>
          <div className="sidebar-brand-tagline">Properties</div>
        </div>
      </div>

      <nav className="sidebar-nav">
        <div className="nav-section-label">Main</div>
        {filtered(NAV_ITEMS).map(item => (
          <div
            key={item.path}
            className={`nav-item ${currentPath === item.path ? 'active' : ''}`}
            onClick={() => navigate(getAppPath(user.role, item.path.slice(1) as AppPage))}
          >
            <span className="nav-icon">{item.icon}</span>
            <span>{item.label}</span>
            {item.badge && <span className="nav-badge">{item.badge}</span>}
          </div>
        ))}

        <div className="nav-section-label" style={{ marginTop: 8 }}>Management</div>
        {filtered(MANAGEMENT_ITEMS).map(item => (
          <div
            key={item.path}
            className={`nav-item ${currentPath === item.path ? 'active' : ''}`}
            onClick={() => navigate(getAppPath(user.role, item.path.slice(1) as AppPage))}
          >
            <span className="nav-icon">{item.icon}</span>
            <span>{item.label}</span>
            {item.badge && <span className="nav-badge">{item.badge}</span>}
          </div>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div className="sidebar-user" onClick={() => logout()}>
          <div className="avatar">
            {user.avatarInitials}
          </div>
          <div className="sidebar-user-info">
            <div className="sidebar-user-name">{user.firstName} {user.lastName}</div>
            <div className="sidebar-user-role" style={{ color: roleColors[user.role] }}>
              {roleLabels[user.role]}
            </div>
          </div>
          <span style={{ color: 'var(--text-muted)', fontSize: 14 }}>↩</span>
        </div>
      </div>
    </aside>
  );
}
