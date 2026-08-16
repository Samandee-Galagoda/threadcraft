import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import Navbar from '../components/Navbar';
import { dashboard as dashboardApi, measurements as measurementsApi } from '../api';
import { useAuth } from '../context/AuthContext';

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isEditingMeas, setIsEditingMeas] = useState(false);
  const [measForm, setMeasForm] = useState({
    bust: 0.0,
    waist: 0.0,
    hip: 0.0,
    shoulder: 0.0,
    sleeve: 0.0,
    total_length: 0.0,
    chest: 0.0,
    inseam: 0.0
  });

  const navigate = useNavigate();
  const { logout } = useAuth();

  const fetchDashboardData = useCallback(async () => {
    try {
      // A 401 is handled centrally by the API client, which clears the session
      // and redirects — no need to duplicate that here.
      const result = await dashboardApi.load();
      setData(result);
      if (result.measurements) {
        setMeasForm({
          bust: result.measurements.bust,
          waist: result.measurements.waist,
          hip: result.measurements.hip,
          shoulder: result.measurements.shoulder,
          sleeve: result.measurements.sleeve,
          total_length: result.measurements.total_length,
          chest: result.measurements.chest,
          inseam: result.measurements.inseam
        });
      }
      setLoading(false);
    } catch (err) {
      console.error(err);
      setError(err.message || 'Could not reach the server. Please try again shortly.');
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchDashboardData();
  }, [fetchDashboardData]);

  const handleSignOut = () => {
    logout();
    navigate('/');
  };

  const handleMeasChange = (e) => {
    const { name, value } = e.target;
    setMeasForm(prev => ({
      ...prev,
      [name]: parseFloat(value) || 0.0
    }));
  };

  const handleMeasSubmit = async (e) => {
    e.preventDefault();
    try {
      const updatedMeas = await measurementsApi.save(measForm);
      setData(prev => ({
        ...prev,
        measurements: updatedMeas,
        measurements_saved: true
      }));
      setIsEditingMeas(false);
    } catch (err) {
      console.error(err);
      alert(err.message || 'Error updating measurements. Please try again.');
    }
  };

  if (loading) {
    return (
      <div style={{ background: '#FAF7F2', minHeight: '100vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', fontFamily: "'Jost', sans-serif", color: '#5C4A35' }}>
        <div style={{ fontFamily: "'Cormorant Garamond', serif", fontSize: '28px', fontStyle: 'italic', marginBottom: '14px' }}>Loading your dashboard...</div>
        <div style={{ width: '40px', height: '40px', border: '3px solid #E8D5C0', borderTop: '3px solid #8B6B4A', borderRadius: '50%', animation: 'spin 1s linear infinite' }}></div>
        <style>{`@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ background: '#FAF7F2', minHeight: '100vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', fontFamily: "'Jost', sans-serif", color: '#5C4A35', padding: '24px', textAlign: 'center' }}>
        <div style={{ fontFamily: "'Cormorant Garamond', serif", fontSize: '32px', color: '#2C1F14', marginBottom: '14px' }}>Connection Failure</div>
        <p style={{ maxWidth: '480px', fontSize: '14px', lineHeight: '1.6', color: '#8B6B4A', marginBottom: '24px' }}>{error}</p>
        <button onClick={fetchDashboardData} style={{ background: '#8B6B4A', color: '#FAF7F2', border: 'none', padding: '12px 28px', fontSize: '11px', letterSpacing: '.14em', textTransform: 'uppercase', cursor: 'pointer', fontFamily: "'Jost', sans-serif" }}>Retry Connection</button>
      </div>
    );
  }

  const { user, total_orders, active_orders_count, measurements_saved, measurements, recent_orders, saved_designs } = data;
  const avatarInit = user.first_name ? user.first_name.charAt(0).toUpperCase() : 'U';
  const fullName = `${user.first_name} ${user.last_name}`;

  return (
    <>
      <Navbar />
      <div className="portal">
        {/* PORTAL SIDEBAR */}
        <div className="portal-sidebar">
          <div className="portal-user">
            <div className="user-avatar">{avatarInit}</div>
            <div className="user-name">{fullName}</div>
            <div className="user-email">{user.email}</div>
            <div className="user-since">{user.created_at}</div>
          </div>
          <div className="portal-nav">
            <div className="portal-nav-label">Account</div>
            <div className="portal-nav-item active">
              <svg viewBox="0 0 24 24"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>
              <span>Dashboard</span>
            </div>
            <div className="portal-nav-item" onClick={() => alert('Orders detail view is mock-integrated. Checkout your active orders below!')}>
              <svg viewBox="0 0 24 24"><path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"/><line x1="3" y1="6" x2="21" y2="6"/></svg>
              <span>My orders</span>
              <span className="portal-nav-badge">{total_orders}</span>
            </div>
            <div className="portal-nav-item" onClick={() => alert('Order tracking is integrated. Tracking number: TC-2026-00142 is Stitching.')}>
              <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
              <span>Order tracking</span>
            </div>
            <div className="portal-nav-label">Preferences</div>
            <div className="portal-nav-item" onClick={() => setIsEditingMeas(true)}>
              <svg viewBox="0 0 24 24"><path d="M20 7H4a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2z"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/></svg>
              <span>My measurements</span>
            </div>
            <div className="portal-nav-item">
              <svg viewBox="0 0 24 24"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg>
              <span>Saved designs</span>
              <span className="portal-nav-badge">{saved_designs.length}</span>
            </div>
            <div className="portal-nav-label">Settings</div>
            <div className="portal-nav-item" onClick={handleSignOut}>
              <svg viewBox="0 0 24 24"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
              <span>Sign out</span>
            </div>
          </div>
        </div>

        {/* PORTAL MAIN */}
        <div className="portal-main">
          <div className="portal-header">
            <h1>Welcome back, {user.first_name}</h1>
            <p>Your ThreadCraft account · Updated 2026</p>
          </div>

          {/* WELCOME STAT CARDS */}
          <div className="welcome-row">
            <div className="welcome-card dark">
              <div className="wc-icon"><svg viewBox="0 0 24 24"><path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"/><line x1="3" y1="6" x2="21" y2="6"/></svg></div>
              <div className="wc-num">{total_orders}</div>
              <div className="wc-label" style={{ color: '#8B6B4A' }}>Total orders</div>
            </div>
            <div className="welcome-card">
              <div className="wc-icon"><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg></div>
              <div className="wc-num">{active_orders_count}</div>
              <div className="wc-label">Active order{active_orders_count !== 1 && 's'}</div>
              {active_orders_count > 0 && <div className="wc-action" onClick={() => alert('Order TC-2026-00142 is currently in Stitching stage.')}>Track now →</div>}
            </div>
            <div className="welcome-card">
              <div className="wc-icon"><svg viewBox="0 0 24 24"><path d="M20 7H4a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2z"/></svg></div>
              <div className="wc-num">{measurements_saved ? '✓' : '—'}</div>
              <div className="wc-label">{measurements_saved ? 'Measurements saved' : 'No measurements'}</div>
              <div className="wc-action" onClick={() => setIsEditingMeas(true)}>{measurements_saved ? 'Edit →' : 'Create →'}</div>
            </div>
            <div className="welcome-card">
              <div className="wc-icon"><svg viewBox="0 0 24 24"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg></div>
              <div className="wc-num">{saved_designs.length}</div>
              <div className="wc-label">Saved designs</div>
              <div className="wc-action" onClick={() => navigate('/design')}>Continue →</div>
            </div>
          </div>

          {/* QUICK ACTIONS */}
          <div className="qa-grid">
            <div className="qa-card" onClick={() => navigate('/design')}>
              <svg viewBox="0 0 24 24" style={{ fill: 'none' }}><path d="M12 5v14M5 12h14" strokeWidth="1.5"/></svg>
              <h4>Start new design</h4>
              <p>Design a custom garment</p>
            </div>
            <div className="qa-card" onClick={() => alert('Reorder submitted for Midi Dress (Silk · Dusty Rose)')}>
              <svg viewBox="0 0 24 24" style={{ fill: 'none' }}><polyline points="17 1 21 5 17 9"/><path d="M3 11V9a4 4 0 0 1 4-4h14"/></svg>
              <h4>Reorder last item</h4>
              <p>Midi Dress · Dusty Rose</p>
            </div>
            <div className="qa-card" onClick={() => alert('TC-2026-00142 is In stitching. Estimated delivery: 10 days.')}>
              <svg viewBox="0 0 24 24" style={{ fill: 'none' }}><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
              <h4>Track active order</h4>
              <p>TC-2026-00142 · In stitching</p>
            </div>
          </div>

          {/* RECENT ORDERS + MEASUREMENTS */}
          <div className="grid-2">
            <div className="card">
              <div className="card-head">
                <div className="card-title">Recent orders</div>
                <div className="card-link" onClick={() => alert('Showing all orders')}>View all →</div>
              </div>
              {recent_orders.length === 0 ? (
                <p style={{ fontSize: '12px', color: 'var(--taupe)', fontStyle: 'italic', textAlign: 'center', padding: '36px 0' }}>No orders placed yet. Start your design above!</p>
              ) : (
                recent_orders.map((order, idx) => (
                  <div className="order-item" key={idx}>
                    <div className="order-thumb">
                      <svg viewBox="0 0 24 24" style={{ fill: 'none' }}>
                        {order.cloth_type.toLowerCase().includes('dress') ? (
                          <path d="M12 2l-5 5h3v7h4V7h3z" strokeWidth="1.4"/>
                        ) : order.cloth_type.toLowerCase().includes('blouse') ? (
                          <path d="M9 5h6l3 4v10H6V9z" strokeWidth="1.4"/>
                        ) : (
                          <path d="M8 3h8l4 5v13H4V8z" strokeWidth="1.4"/>
                        )}
                        <path d="M5 20h14" strokeWidth="1.4"/>
                      </svg>
                    </div>
                    <div className="order-info">
                      <div className="order-name">{order.cloth_type}</div>
                      <div className="order-detail">{order.material} · {order.fit}</div>
                      <div className="order-meta">
                        <span className="order-date">{new Date(order.created_at).toLocaleDateString('en-US', { day: 'numeric', month: 'short', year: 'numeric' })}</span>
                        <span className={`status-pill ${
                          order.status.toLowerCase() === 'stitching' ? 'sp-stitching' : 
                          order.status.toLowerCase() === 'dispatched' ? 'sp-dispatched' : 'sp-received'
                        }`}>{order.status}</span>
                      </div>
                    </div>
                    <div className="order-price">LKR {parseFloat(order.price).toLocaleString()}</div>
                    <div className="order-actions">
                      <button className="oa-btn" onClick={() => alert(`Tracking order ${order.order_number}: Current status is ${order.status}`)}>Track</button>
                      <button className="oa-btn" onClick={() => alert(`Reordering ${order.cloth_type}...`)}>Reorder</button>
                    </div>
                  </div>
                ))
              )}
            </div>

            <div className="card">
              <div className="card-head">
                <div className="card-title">My measurements</div>
                <div className="card-link" onClick={() => setIsEditingMeas(!isEditingMeas)}>
                  {isEditingMeas ? 'Cancel' : 'Edit →'}
                </div>
              </div>
              
              {isEditingMeas ? (
                <form onSubmit={handleMeasSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                    {Object.keys(measForm).map((key) => (
                      <div key={key} style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                        <label style={{ fontSize: '9px', textTransform: 'uppercase', letterSpacing: '.1em', color: 'var(--taupe)' }}>
                          {key.replace('_', ' ')}
                        </label>
                        <input
                          type="number"
                          step="0.1"
                          name={key}
                          value={measForm[key]}
                          onChange={handleMeasChange}
                          style={{ background: 'var(--cream)', border: '.5px solid var(--sand)', padding: '6px 10px', fontSize: '12px', fontFamily: "'Jost', sans-serif", color: 'var(--dark)' }}
                        />
                      </div>
                    ))}
                  </div>
                  <button type="submit" style={{ background: '#8B6B4A', color: '#FAF7F2', border: 'none', padding: '10px', fontSize: '10px', letterSpacing: '.14em', textTransform: 'uppercase', cursor: 'pointer', fontFamily: "'Jost', sans-serif", marginTop: '10px' }}>
                    Save Measurements
                  </button>
                </form>
              ) : (
                <>
                  <div className="meas-grid">
                    <div className="meas-item"><span className="meas-label">Bust</span><span className="meas-val">{measurements?.bust || 0}<span className="meas-unit">cm</span></span></div>
                    <div className="meas-item"><span className="meas-label">Waist</span><span className="meas-val">{measurements?.waist || 0}<span className="meas-unit">cm</span></span></div>
                    <div className="meas-item"><span className="meas-label">Hip</span><span className="meas-val">{measurements?.hip || 0}<span className="meas-unit">cm</span></span></div>
                    <div className="meas-item"><span className="meas-label">Shoulder</span><span className="meas-val">{measurements?.shoulder || 0}<span className="meas-unit">cm</span></span></div>
                    <div className="meas-item"><span className="meas-label">Sleeve</span><span className="meas-val">{measurements?.sleeve || 0}<span className="meas-unit">cm</span></span></div>
                    <div className="meas-item"><span className="meas-label">Total length</span><span className="meas-val">{measurements?.total_length || 0}<span className="meas-unit">cm</span></span></div>
                    <div className="meas-item"><span className="meas-label">Chest</span><span className="meas-val">{measurements?.chest || 0}<span className="meas-unit">cm</span></span></div>
                    <div className="meas-item"><span className="meas-label">Inseam</span><span className="meas-val">{measurements?.inseam || 0}<span className="meas-unit">cm</span></span></div>
                  </div>
                  <div style={{ marginTop: '18px', paddingTop: '16px', borderTop: '.5px solid var(--sand)', fontSize: '11px', color: 'var(--taupe)' }}>
                    These measurements are auto-filled in Step 4 when you place a new order.
                    <div style={{ marginTop: '10px' }}>
                      <span onClick={() => setIsEditingMeas(true)} style={{ fontSize: '10px', letterSpacing: '.14em', textTransform: 'uppercase', color: 'var(--brown)', cursor: 'pointer' }}>Update measurements →</span>
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>

          {/* SAVED DESIGNS */}
          <div className="card" style={{ marginTop: '20px' }}>
            <div className="card-head">
              <div className="card-title">Saved designs</div>
              <div className="card-link" onClick={() => navigate('/design')}>View all →</div>
            </div>
            <div className="saved-grid">
              {saved_designs.length === 0 ? (
                <p style={{ gridColumn: 'span 3', fontSize: '12px', color: 'var(--taupe)', fontStyle: 'italic', textAlign: 'center', padding: '24px 0' }}>No saved designs found.</p>
              ) : (
                saved_designs.map((design, idx) => (
                  <div className="saved-card" key={idx} onClick={() => navigate('/design')}>
                    <div className="saved-thumb" style={{ background: idx % 2 === 0 ? 'linear-gradient(135deg,#e8d5c0,#d4b896)' : 'linear-gradient(135deg,#ddd0c4,#c9b8a8)' }}>
                      <svg viewBox="0 0 60 60" style={{ fill: 'none' }}>
                        {design.name.toLowerCase().includes('dress') ? (
                          <path d="M20 8h20l6 18-8 28H22L14 26z" strokeWidth="1.5"/>
                        ) : (
                          <path d="M15 10L8 16v10h8v24h28V26h8V16l-7-6-7 5-7-5-7 5z" strokeWidth="1.5"/>
                        )}
                      </svg>
                      <div className="saved-badge">Draft</div>
                    </div>
                    <div className="saved-info">
                      <div className="saved-name">{design.name}</div>
                      <div className="saved-meta">{design.material} · {design.color} · Saved {new Date(design.created_at).toLocaleDateString('en-US', { day: 'numeric', month: 'short' })}</div>
                    </div>
                  </div>
                ))
              )}
              <div onClick={() => navigate('/design')} className="saved-card" style={{ borderStyle: 'dashed', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '220px', cursor: 'pointer', background: 'transparent' }}>
                <svg viewBox="0 0 24 24" style={{ width: '32px', height: '32px', stroke: 'var(--sand)', fill: 'none', marginBottom: '10px' }}><path d="M12 5v14M5 12h14" strokeWidth="1.5"/></svg>
                <span style={{ fontSize: '10px', letterSpacing: '.14em', textTransform: 'uppercase', color: 'var(--taupe)' }}>Start new design</span>
              </div>
            </div>
          </div>

        </div>
      </div>
    </>
  );
}
