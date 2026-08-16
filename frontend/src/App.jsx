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

function ProtectedRoute({ children }) {
  const { isAuthenticated } = useAuth();
  const location = useLocation();
  if (!isAuthenticated) {
    return <Navigate to={`/auth?next=${encodeURIComponent(location.pathname)}`} replace />;
  }
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
          <Route path="*" element={<NotFound />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
