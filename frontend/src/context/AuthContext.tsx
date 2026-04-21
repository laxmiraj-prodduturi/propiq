import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import type { User } from '../types';
import { loginApi, getMeApi, logoutApi, refreshTokenApi } from '../api/auth';

interface AuthContextType {
  user: User | null;
  login: (emailOrRole: string, password?: string) => Promise<User>;
  logout: () => void;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);

  // Restore session on mount: try stored token, then refresh cookie, then give up
  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (token) {
      getMeApi()
        .then(setUser)
        .catch(() => {
          // Access token expired — try the refresh cookie
          refreshTokenApi()
            .then(({ token: newToken, user: refreshedUser }) => {
              localStorage.setItem('access_token', newToken);
              setUser(refreshedUser);
            })
            .catch(() => localStorage.removeItem('access_token'));
        });
    } else {
      // No stored token — see if there's a valid refresh cookie
      refreshTokenApi()
        .then(({ token: newToken, user: refreshedUser }) => {
          localStorage.setItem('access_token', newToken);
          setUser(refreshedUser);
        })
        .catch(() => {/* not logged in */});
    }
  }, []);

  const login = async (emailOrRole: string, password?: string): Promise<User> => {
    // If called with just a role (demo quick-login), look up the email
    const isRole = ['owner', 'manager', 'tenant'].includes(emailOrRole) && !password;
    let email = emailOrRole;
    let pwd = password ?? 'demo1234';

    if (isRole) {
      const roleToEmail: Record<string, string> = {
        owner: 'alex.thompson@example.com',
        manager: 'sarah.chen@example.com',
        tenant: 'marcus.johnson@example.com',
      };
      email = roleToEmail[emailOrRole];
    }

    const { token, user: apiUser } = await loginApi(email, pwd);
    localStorage.setItem('access_token', token);
    setUser(apiUser);
    return apiUser;
  };

  const logout = () => {
    logoutApi();
    localStorage.removeItem('access_token');
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, isAuthenticated: user !== null }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
