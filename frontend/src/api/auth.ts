import { apiRequest } from './client';
import type { User } from '../types';

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
}

// Backend returns snake_case, we need to map to camelCase for User type
function mapUser(raw: any): User {
  return {
    id: raw.id,
    tenantId: raw.tenant_id,
    email: raw.email,
    role: raw.role,
    firstName: raw.first_name,
    lastName: raw.last_name,
    phone: raw.phone ?? '',
    avatarInitials: raw.avatar_initials ?? '',
  };
}

export async function loginApi(email: string, password: string): Promise<{ token: string; user: User }> {
  const data = await apiRequest<any>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
  return { token: data.access_token, user: mapUser(data.user) };
}

export async function getMeApi(): Promise<User> {
  const raw = await apiRequest<any>('/users/me');
  return mapUser(raw);
}

export async function logoutApi(): Promise<void> {
  await apiRequest('/auth/logout', { method: 'POST' }).catch(() => {});
}

export async function refreshTokenApi(): Promise<{ token: string; user: User }> {
  const data = await apiRequest<any>('/auth/refresh', {
    method: 'POST',
    credentials: 'include', // send HttpOnly refresh_token cookie
  });
  return { token: data.access_token, user: mapUser(data.user) };
}
