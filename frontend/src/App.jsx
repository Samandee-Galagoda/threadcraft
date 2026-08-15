import { BrowserRouter, Routes, Route } from 'react-router-dom';
import MeasurementGuide from './pages/MeasurementGuide';
import Home from './pages/Home';
import Auth from './pages/Auth';
import Dashboard from './pages/Dashboard';
import DesignWizard from './pages/DesignWizard';
import OrderSuccess from './pages/OrderSuccess';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/auth" element={<Auth />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/measurement-guide" element={<MeasurementGuide />} />
        <Route path="/design/*" element={<DesignWizard />} />
        <Route path="/success" element={<OrderSuccess />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
