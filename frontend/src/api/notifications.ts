import { apiRequest } from './client';
import type { Notification } from '../types';

function mapNotification(raw: any): Notification {
  return {
    id: raw.id,
    userId: raw.user_id,
    type: raw.type,
    title: raw.title,
    body: raw.body,
    isRead: raw.is_read,
    createdAt: raw.created_at,
  };
}

export async function getNotifications(): Promise<Notification[]> {
  const data = await apiRequest<any[]>('/notifications');
  return data.map(mapNotification);
}

export async function markNotificationRead(id: string): Promise<Notification> {
  const raw = await apiRequest<any>(`/notifications/${id}/read`, { method: 'PUT' });
  return mapNotification(raw);
}

export async function markAllNotificationsRead(): Promise<void> {
  await apiRequest('/notifications/read-all', { method: 'PUT' });
}
