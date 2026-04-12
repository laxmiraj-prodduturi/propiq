const BASE = '/api/v1';

// Prevent multiple concurrent refresh calls
let refreshPromise: Promise<string> | null = null;

async function doRefresh(): Promise<string> {
  const res = await fetch(`${BASE}/auth/refresh`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) throw new Error('refresh_failed');
  const data = await res.json();
  const token: string = data.access_token;
  localStorage.setItem('access_token', token);
  return token;
}

export async function apiRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem('access_token');

  const makeRequest = (t: string | null) =>
    fetch(`${BASE}${path}`, {
      ...options,
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        ...(t ? { Authorization: `Bearer ${t}` } : {}),
        ...options.headers,
      },
    });

  let res = await makeRequest(token);

  // On 401, attempt a single token refresh then retry
  if (res.status === 401 && path !== '/auth/refresh' && path !== '/auth/login') {
    try {
      if (!refreshPromise) {
        refreshPromise = doRefresh().finally(() => { refreshPromise = null; });
      }
      const newToken = await refreshPromise;
      res = await makeRequest(newToken);
    } catch {
      localStorage.removeItem('access_token');
      // Re-throw so callers know authentication failed
      throw new Error('session_expired');
    }
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as any).detail ?? `HTTP ${res.status}`);
  }

  // 204 No Content
  if (res.status === 204) return undefined as unknown as T;
  return res.json();
}
