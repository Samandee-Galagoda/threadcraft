import { BrowserRouter, Navigate, Route, Routes, useLocation } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { WizardProvider } from './context/WizardContext';
import Auth from './pages/Auth';
import Dashboard from './pages/Dashboard';
import DesignWizard from './pages/DesignWizard';
import Home from './pages/Home';
import MeasurementGuide from './pages/MeasurementGuide';
import NotFound from './pages/NotFound';
import OrderSuccess from './pages/OrderSuccess';
import OrderTracking from './pages/OrderTracking';
import AdminCatalogue from './pages/admin/AdminCatalogue';
import AdminInventory from './pages/admin/AdminInventory';
import AdminLayout from './pages/admin/AdminLayout';
import AdminOrders from './pages/admin/AdminOrders';
import AdminOverview from './pages/admin/AdminOverview';
import AdminSettings from './pages/admin/AdminSettings';

function ProtectedRoute({ children }) {
  const { isAuthenticated } = useAuth();
  const location = useLocation();
  if (!isAuthenticated) {
    return <Navigate to={`/auth?next=${encodeURIComponent(location.pathname)}`} replace />;
  }
  return children;
}

/** Hiding /admin from non-admins is a usability measure, not the security
 *  boundary — every admin endpoint is behind require_admin server-side, so a
 *  customer who types the URL gets 403s from the API regardless. */
function AdminRoute({ children }) {
  const { isAuthenticated, isAdmin } = useAuth();
  const location = useLocation();
  if (!isAuthenticated) {
    return <Navigate to={`/auth?next=${encodeURIComponent(location.pathname)}`} replace />;
  }
  if (!isAdmin) return <Navigate to="/dashboard" replace />;
  return children;
}

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/auth" element={<Auth />} />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            }
          />
          <Route path="/measurement-guide" element={<MeasurementGuide />} />
          <Route
            path="/design/*"
            element={
              <WizardProvider>
                <DesignWizard />
              </WizardProvider>
            }
          />
          <Route path="/success" element={<OrderSuccess />} />
          <Route path="/track" element={<OrderTracking />} />
          <Route path="/track/:orderNumber" element={<OrderTracking />} />
          <Route
            path="/admin"
            element={
              <AdminRoute>
                <AdminLayout />
              </AdminRoute>
            }
          >
            <Route index element={<AdminOverview />} />
            <Route path="orders" element={<AdminOrders />} />
            <Route path="inventory" element={<AdminInventory />} />
            <Route path="catalogue" element={<AdminCatalogue />} />
            <Route path="settings" element={<AdminSettings />} />
          </Route>
          <Route path="*" element={<NotFound />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
