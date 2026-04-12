import { useState, useEffect } from 'react';
import { MOCK_NOTIFICATIONS } from '../../data/mockData';
import { getNotifications, markNotificationRead, markAllNotificationsRead } from '../../api/notifications';
import { useAuth } from '../../context/AuthContext';
import type { Notification, NotificationType } from '../../types';

const typeIcon: Record<NotificationType, string> = {
  payment: '💳',
  maintenance: '🔧',
  lease: '📋',
  ai: '🤖',
  system: '⚙️',
};

const typeBg: Record<NotificationType, string> = {
  payment: 'rgba(16,185,129,0.1)',
  maintenance: 'rgba(245,158,11,0.1)',
  lease: 'rgba(99,102,241,0.1)',
  ai: 'rgba(6,182,212,0.1)',
  system: 'rgba(255,255,255,0.05)',
};

function timeAgo(iso: string) {
  const diff = Date.now() - new Date(iso).getTime();
  const min = Math.floor(diff / 60000);
  const hr = Math.floor(diff / 3600000);
  const days = Math.floor(diff / 86400000);
  if (days > 0) return `${days}d ago`;
  if (hr > 0) return `${hr}h ago`;
  return `${min}m ago`;
}

export default function Notifications() {
  const { user } = useAuth();
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<NotificationType | 'all'>('all');

  useEffect(() => {
    getNotifications()
      .then(setNotifications)
      .catch(() => {
        // Fallback: filter mock to current user
        const userId = user?.id ?? 'u2';
        setNotifications(MOCK_NOTIFICATIONS.filter(n => n.userId === userId));
      })
      .finally(() => setLoading(false));
  }, [user]);

  if (loading) return <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>Loading…</div>;

  const unread = notifications.filter(n => !n.isRead).length;

  const markAllRead = async () => {
    try {
      await markAllNotificationsRead();
    } catch {
      // ignore
    }
    setNotifications(prev => prev.map(n => ({ ...n, isRead: true })));
  };

  const markRead = async (id: string) => {
    try {
      await markNotificationRead(id);
    } catch {
      // ignore
    }
    setNotifications(prev => prev.map(n => n.id === id ? { ...n, isRead: true } : n));
  };

  const filtered = notifications.filter(n => filter === 'all' || n.type === filter);

  return (
    <div className="animate-in">
      <div className="page-header">
        <div>
          <h2>Notifications</h2>
          <p>{unread} unread notification{unread !== 1 ? 's' : ''}</p>
        </div>
        {unread > 0 && (
          <button className="btn btn-secondary" onClick={markAllRead}>
            ✓ Mark all as read
          </button>
        )}
      </div>

      <div className="filter-bar">
        <div className="tabs">
          {(['all', 'payment', 'maintenance', 'lease', 'ai', 'system'] as const).map(t => (
            <button key={t} className={`tab ${filter === t ? 'active' : ''}`} onClick={() => setFilter(t)}>
              {t === 'all' ? 'All' : t.charAt(0).toUpperCase() + t.slice(1)}
              {t !== 'all' && notifications.filter(n => n.type === t && !n.isRead).length > 0 && (
                <span style={{ marginLeft: 5, display: 'inline-block', width: 6, height: 6, background: 'var(--danger)', borderRadius: '50%' }} />
              )}
            </button>
          ))}
        </div>
      </div>

      <div className="card">
        {filtered.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">🔕</div>
            <div className="empty-title">No notifications</div>
            <div className="empty-desc">You're all caught up!</div>
          </div>
        ) : (
          <div className="notification-list">
            {filtered.map(notif => (
              <div
                key={notif.id}
                className={`notification-item ${!notif.isRead ? 'unread' : ''}`}
                onClick={() => markRead(notif.id)}
              >
                <div
                  className="notif-icon-wrap"
                  style={{ background: typeBg[notif.type] }}
                >
                  {typeIcon[notif.type]}
                </div>
                <div className="notif-content">
                  <div className="notif-title">{notif.title}</div>
                  <div className="notif-body">{notif.body}</div>
                  <div className="notif-time">{timeAgo(notif.createdAt)}</div>
                </div>
                {!notif.isRead && (
                  <div style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--primary)', flexShrink: 0, marginTop: 6 }} />
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
