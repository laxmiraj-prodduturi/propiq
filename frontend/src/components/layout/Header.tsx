import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { getAppPath, stripRolePrefix } from '../../routes';

const PAGE_META: Record<string, { title: string; desc: string }> = {
  '/dashboard': { title: 'Dashboard', desc: 'Welcome back — here\'s your overview' },
  '/properties': { title: 'Homes', desc: 'Manage your residential portfolio' },
  '/leases': { title: 'Leases', desc: 'Active and historical lease agreements' },
  '/maintenance': { title: 'Maintenance', desc: 'Work orders and service requests' },
  '/payments': { title: 'Payments', desc: 'Rent collection and financial history' },
  '/documents': { title: 'Documents', desc: 'Secure document vault' },
  '/ai-chat': { title: 'AI Assistant', desc: 'Powered by Claude AI' },
  '/notifications': { title: 'Notifications', desc: 'Alerts and updates' },
};

export default function Header() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const currentPath = stripRolePrefix(location.pathname);
  const meta = PAGE_META[currentPath] ?? { title: 'QuantumQuestProperties', desc: '' };

  const now = new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' });

  return (
    <header className="header">
      <div className="header-title">
        <h1>{meta.title}</h1>
        <p>{meta.desc} · {now}</p>
      </div>

      <div className="header-actions">
        <button className="icon-btn" title="Search" style={{ fontSize: 15 }}>🔍</button>
        <button
          className="icon-btn"
          title="Notifications"
          onClick={() => user && navigate(getAppPath(user.role, 'notifications'))}
        >
          🔔
          <span className="badge-dot" />
        </button>
        <div className="avatar" style={{ cursor: 'default', marginLeft: 4 }}>
          {user?.avatarInitials}
        </div>
      </div>
    </header>
  );
}
