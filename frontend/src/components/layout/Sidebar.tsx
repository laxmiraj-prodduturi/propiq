import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import type { Role } from '../../types';
import { getAppPath, stripRolePrefix, type AppPage } from '../../routes';
import { Icon } from '../Icons';
import type { ComponentType } from 'react';

interface NavItem {
  icon: ComponentType<{ size?: number }>;
  label: string;
  path: string;
  roles: Role[];
  badge?: number;
}

const NAV_ITEMS: NavItem[] = [
  { icon: Icon.dashboard, label: 'Dashboard',    path: '/dashboard',     roles: ['owner', 'manager', 'tenant'] },
  { icon: Icon.home,      label: 'Properties',   path: '/properties',    roles: ['owner', 'manager'] },
  { icon: Icon.lease,     label: 'Leases',       path: '/leases',        roles: ['owner', 'manager', 'tenant'] },
  { icon: Icon.wrench,    label: 'Maintenance',  path: '/maintenance',   roles: ['owner', 'manager', 'tenant'] },
  { icon: Icon.card,      label: 'Payments',     path: '/payments',      roles: ['owner', 'manager', 'tenant'] },
  { icon: Icon.folder,    label: 'Documents',    path: '/documents',     roles: ['owner', 'manager', 'tenant'] },
  { icon: Icon.sparkles,  label: 'AI Assistant', path: '/ai-chat',       roles: ['owner', 'manager', 'tenant'] },
  { icon: Icon.bell,      label: 'Notifications',path: '/notifications', roles: ['owner', 'manager', 'tenant'], badge: 3 },
];

const roleColors: Record<Role, string> = {
  owner:   'var(--amber)',
  manager: 'var(--primary-light)',
  tenant:  'var(--emerald)',
};

const roleLabels: Record<Role, string> = {
  owner:   'Property Owner',
  manager: 'Property Manager',
  tenant:  'Tenant',
};

export default function Sidebar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  if (!user) return null;

  const filtered = NAV_ITEMS.filter(i => i.roles.includes(user.role));
  const currentPath = stripRolePrefix(location.pathname);

  return (
    <aside className="sidebar">
      {/* Brand */}
      <div className="sidebar-brand">
        <div className="sidebar-logo">P</div>
        <div className="sidebar-brand-text">
          <div className="sidebar-brand-name">PropIQ</div>
          <div className="sidebar-brand-tagline">Property Management</div>
        </div>
      </div>

      {/* Nav */}
      <nav className="sidebar-nav">
        {filtered.map(item => {
          const NavIcon = item.icon;
          return (
            <div
              key={item.path}
              className={`nav-item ${currentPath === item.path ? 'active' : ''}`}
              onClick={() => navigate(getAppPath(user.role, item.path.slice(1) as AppPage))}
            >
              <span className="nav-icon"><NavIcon size={17} /></span>
              <span>{item.label}</span>
              {item.badge && <span className="nav-badge">{item.badge}</span>}
            </div>
          );
        })}
      </nav>

      {/* User + Logout */}
      <div className="sidebar-footer">
        <div className="sidebar-user">
          <div className="avatar">{user.avatarInitials}</div>
          <div className="sidebar-user-info">
            <div className="sidebar-user-name">{user.firstName} {user.lastName}</div>
            <div className="sidebar-user-role" style={{ color: roleColors[user.role] }}>
              {roleLabels[user.role]}
            </div>
          </div>
          <button
            className="icon-btn sidebar-logout"
            title="Sign out"
            onClick={() => logout()}
          >
            <Icon.logout size={15} />
          </button>
        </div>
      </div>
    </aside>
  );
}
