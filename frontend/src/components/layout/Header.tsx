import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { getAppPath, stripRolePrefix } from '../../routes';
import { Icon } from '../Icons';

const PAGE_META: Record<string, { title: string; desc: string }> = {
  '/dashboard':     { title: 'Dashboard',    desc: 'Overview of your portfolio' },
  '/properties':    { title: 'Properties',   desc: 'Manage your residential portfolio' },
  '/leases':        { title: 'Leases',       desc: 'Active and historical agreements' },
  '/maintenance':   { title: 'Maintenance',  desc: 'Work orders and service requests' },
  '/payments':      { title: 'Payments',     desc: 'Rent collection and history' },
  '/documents':     { title: 'Documents',    desc: 'Secure document vault' },
  '/ai-chat':       { title: 'AI Assistant', desc: 'Ask anything about your portfolio' },
  '/notifications': { title: 'Notifications',desc: 'Alerts and updates' },
};

export default function Header() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const currentPath = stripRolePrefix(location.pathname);
  const meta = PAGE_META[currentPath] ?? { title: 'PropIQ', desc: '' };

  return (
    <header className="header">
      <div className="header-title">
        <h1>{meta.title}</h1>
        <p>{meta.desc}</p>
      </div>

      <div className="header-actions">
        <button className="icon-btn" title="Search">
          <Icon.search size={16} />
        </button>
        <button
          className="icon-btn"
          title="Notifications"
          onClick={() => user && navigate(getAppPath(user.role, 'notifications'))}
        >
          <Icon.bell size={16} />
          <span className="badge-dot" />
        </button>
        <div className="avatar" style={{ cursor: 'default', marginLeft: 4 }}>
          {user?.avatarInitials}
        </div>
      </div>
    </header>
  );
}
