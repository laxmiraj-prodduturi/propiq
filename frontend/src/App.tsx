import type { ReactNode } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import Layout from './components/layout/Layout';
import Login from './pages/auth/Login';
import MarketingPage from './marketing/MarketingPage';
import Dashboard from './pages/dashboard/Dashboard';
import Properties from './pages/properties/Properties';
import Leases from './pages/leases/Leases';
import Maintenance from './pages/maintenance/Maintenance';
import Payments from './pages/payments/Payments';
import Documents from './pages/documents/Documents';
import AIChat from './pages/ai-chat/AIChat';
import Notifications from './pages/notifications/Notifications';
import type { Role } from './types';
import { getDefaultAppPath } from './routes';

function ProtectedRoute({
  children,
  role,
  allowedRoles,
}: {
  children: ReactNode;
  role: Role;
  allowedRoles: Role[];
}) {
  const { isAuthenticated, user } = useAuth();
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  if (!user) return <Navigate to="/login" replace />;
  if (user.role !== role || !allowedRoles.includes(user.role)) {
    return <Navigate to={getDefaultAppPath(user.role)} replace />;
  }
  return <Layout>{children}</Layout>;
}

function AppRoutes() {
  const { isAuthenticated, user } = useAuth();

  const renderScopedRoute = (role: Role, element: ReactNode, allowedRoles: Role[]) => (
    <ProtectedRoute role={role} allowedRoles={allowedRoles}>{element}</ProtectedRoute>
  );

  return (
    <Routes>
      <Route path="/login" element={isAuthenticated && user ? <Navigate to={getDefaultAppPath(user.role)} replace /> : <Login />} />

      <Route path="/owner/dashboard" element={renderScopedRoute('owner', <Dashboard />, ['owner'])} />
      <Route path="/owner/properties" element={renderScopedRoute('owner', <Properties />, ['owner'])} />
      <Route path="/owner/leases" element={renderScopedRoute('owner', <Leases />, ['owner'])} />
      <Route path="/owner/maintenance" element={renderScopedRoute('owner', <Maintenance />, ['owner'])} />
      <Route path="/owner/payments" element={renderScopedRoute('owner', <Payments />, ['owner'])} />
      <Route path="/owner/documents" element={renderScopedRoute('owner', <Documents />, ['owner'])} />
      <Route path="/owner/ai-chat" element={renderScopedRoute('owner', <AIChat />, ['owner'])} />
      <Route path="/owner/notifications" element={renderScopedRoute('owner', <Notifications />, ['owner'])} />
      <Route path="/manager/dashboard" element={renderScopedRoute('manager', <Dashboard />, ['manager'])} />
      <Route path="/manager/properties" element={renderScopedRoute('manager', <Properties />, ['manager'])} />
      <Route path="/manager/leases" element={renderScopedRoute('manager', <Leases />, ['manager'])} />
      <Route path="/manager/maintenance" element={renderScopedRoute('manager', <Maintenance />, ['manager'])} />
      <Route path="/manager/payments" element={renderScopedRoute('manager', <Payments />, ['manager'])} />
      <Route path="/manager/documents" element={renderScopedRoute('manager', <Documents />, ['manager'])} />
      <Route path="/manager/ai-chat" element={renderScopedRoute('manager', <AIChat />, ['manager'])} />
      <Route path="/manager/notifications" element={renderScopedRoute('manager', <Notifications />, ['manager'])} />

      <Route path="/tenant/dashboard" element={renderScopedRoute('tenant', <Dashboard />, ['tenant'])} />
      <Route path="/tenant/leases" element={renderScopedRoute('tenant', <Leases />, ['tenant'])} />
      <Route path="/tenant/maintenance" element={renderScopedRoute('tenant', <Maintenance />, ['tenant'])} />
      <Route path="/tenant/payments" element={renderScopedRoute('tenant', <Payments />, ['tenant'])} />
      <Route path="/tenant/documents" element={renderScopedRoute('tenant', <Documents />, ['tenant'])} />
      <Route path="/tenant/ai-chat" element={renderScopedRoute('tenant', <AIChat />, ['tenant'])} />
      <Route path="/tenant/notifications" element={renderScopedRoute('tenant', <Notifications />, ['tenant'])} />

      <Route path="/dashboard" element={user ? <Navigate to={getDefaultAppPath(user.role)} replace /> : <Navigate to="/login" replace />} />
      <Route path="/properties" element={user ? <Navigate to={`/${user.role}/properties`} replace /> : <Navigate to="/login" replace />} />
      <Route path="/leases" element={user ? <Navigate to={`/${user.role}/leases`} replace /> : <Navigate to="/login" replace />} />
      <Route path="/maintenance" element={user ? <Navigate to={`/${user.role}/maintenance`} replace /> : <Navigate to="/login" replace />} />
      <Route path="/payments" element={user ? <Navigate to={`/${user.role}/payments`} replace /> : <Navigate to="/login" replace />} />
      <Route path="/documents" element={user ? <Navigate to={`/${user.role}/documents`} replace /> : <Navigate to="/login" replace />} />
      <Route path="/ai-chat" element={user ? <Navigate to={`/${user.role}/ai-chat`} replace /> : <Navigate to="/login" replace />} />
      <Route path="/notifications" element={user ? <Navigate to={`/${user.role}/notifications`} replace /> : <Navigate to="/login" replace />} />

      <Route path="/" element={user ? <Navigate to={getDefaultAppPath(user.role)} replace /> : <MarketingPage />} />
      <Route path="*" element={user ? <Navigate to={getDefaultAppPath(user.role)} replace /> : <Navigate to="/login" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </AuthProvider>
  );
}
