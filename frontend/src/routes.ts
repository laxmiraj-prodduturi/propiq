import type { Role } from './types';

export type AppPage =
  | 'dashboard'
  | 'properties'
  | 'leases'
  | 'maintenance'
  | 'payments'
  | 'documents'
  | 'ai-chat'
  | 'notifications';

export function getAppPath(role: Role, page: AppPage): string {
  return `/${role}/${page}`;
}

export function getDefaultAppPath(role: Role): string {
  return getAppPath(role, 'dashboard');
}

export function stripRolePrefix(pathname: string): string {
  const segments = pathname.split('/').filter(Boolean);
  if (segments.length >= 2 && ['owner', 'manager', 'tenant'].includes(segments[0])) {
    return `/${segments.slice(1).join('/')}`;
  }
  return pathname;
}
