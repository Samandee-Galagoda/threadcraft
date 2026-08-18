import { BrowserRouter, Link, Navigate, Route, Routes, useLocation } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { WizardProvider } from './context/WizardContext';
import About from './pages/About';
import Auth from './pages/Auth';

import DesignWizard from './pages/DesignWizard';
import Home from './pages/Home';
import MeasurementGuide from './pages/MeasurementGuide';
import NotFound from './pages/NotFound';
import OrderSuccess from './pages/OrderSuccess';
import OrderTracking from './pages/OrderTracking';
import AccountDashboard from './pages/account/AccountDashboard';
import AccountDesigns from './pages/account/AccountDesigns';
import AccountLayout from './pages/account/AccountLayout';
import AccountMeasurements from './pages/account/AccountMeasurements';
import AccountOrders from './pages/account/AccountOrders';
import AccountProfile from './pages/account/AccountProfile';
import AdminAnalytics from './pages/admin/AdminAnalytics';
import AdminCatalogue from './pages/admin/AdminCatalogue';
import AdminDashboard from './pages/admin/AdminDashboard';
import AdminInventory from './pages/admin/AdminInventory';
import AdminLayout from './pages/admin/AdminLayout';
import AdminMaterials from './pages/admin/AdminMaterials';
import AdminOrders from './pages/admin/AdminOrders';
import AdminPricing from './pages/admin/AdminPricing';
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
  // Say why, rather than bouncing to /dashboard silently. A silent redirect is
  // indistinguishable from "the admin dashboard is broken", which is exactly how
  // it was reported.
  if (!isAdmin) {
    return (
      <div className="success-page">
        <div className="success-eyebrow">Administrator access</div>
        <h1 className="success-title">
          This area is
          <br />
          <em>staff only</em>
        </h1>
        <p className="success-sub">
          You&apos;re signed in as a customer, so the admin dashboard isn&apos;t available on this
          account. Sign in with an administrator account to manage orders, stock and the catalogue.
        </p>
        <div className="success-actions">
          <Link to="/dashboard" className="btn-primary">
            Back to my dashboard
          </Link>
        </div>
      </div>
    );
  }
  return children;
}

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/about" element={<About />} />
          <Route path="/auth" element={<Auth />} />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <AccountLayout />
              </ProtectedRoute>
            }
          >
            <Route index element={<AccountDashboard />} />
            <Route path="orders" element={<AccountOrders />} />
            <Route path="measurements" element={<AccountMeasurements />} />
            <Route path="designs" element={<AccountDesigns />} />
            <Route path="profile" element={<AccountProfile />} />
          </Route>
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
            <Route index element={<AdminDashboard />} />
            <Route path="orders" element={<AdminOrders />} />
            <Route path="inventory" element={<AdminInventory />} />
            <Route path="cloth-types" element={<AdminCatalogue />} />
            <Route path="materials" element={<AdminMaterials />} />
            <Route path="pricing" element={<AdminPricing />} />
            <Route path="analytics" element={<AdminAnalytics />} />
            <Route path="settings" element={<AdminSettings />} />
          </Route>
          <Route path="*" element={<NotFound />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
