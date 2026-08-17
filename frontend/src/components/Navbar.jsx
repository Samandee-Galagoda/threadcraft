import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function Navbar({ backLink = false, secure = false }) {
  // Reads AuthContext rather than localStorage directly. The old version knew
  // whether a token existed but nothing about the user, so an admin had no way
  // to reach /admin except by typing the URL.
  const { isAuthenticated, isAdmin } = useAuth();
  const navigate = useNavigate();

  const handleProfileClick = () => {
    navigate(isAuthenticated ? '/dashboard' : '/auth');
  };

  return (
    <nav>
      {backLink ? (
        <Link to="/" className="back-link">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M19 12H5m0 0 7 7m-7-7 7-7"/></svg>
          Back to home
        </Link>
      ) : (
        <ul className="nav-links">
          <li><Link to="/">Home</Link></li>
          <li><Link to="/measurement-guide">Measurement Guide</Link></li>
          <li><Link to="/#gallery">Gallery</Link></li>
        </ul>
      )}
      
      <div className="nav-logo" style={{textAlign: 'center'}}>
        <h1>THREADCRAFT</h1>
        <p>CUSTOM CLOTHING · SRI LANKA</p>
      </div>

      {secure ? (
        <div style={{fontSize: '11px', letterSpacing: '.1em', color: 'var(--taupe)'}}>
          Secure checkout <span style={{color: 'var(--brown)'}}>🔒</span>
        </div>
      ) : backLink ? (
        <div style={{fontSize: '11px', letterSpacing: '.1em', color: 'var(--taupe)'}}>
          Need help? <span style={{color: 'var(--brown)', cursor: 'pointer'}} onClick={() => alert('Support contact: support@threadcraft.lk')}>Contact us</span>
        </div>
      ) : (
        <div style={{display: 'flex', alignItems: 'center', gap: '20px'}}>
          <ul className="nav-links" style={{margin: 0}}>
            {isAuthenticated ? (
              <li><Link to="/dashboard" style={{ fontWeight: 500 }}>Dashboard</Link></li>
            ) : (
              <li><Link to="/auth">Sign In</Link></li>
            )}
            {isAdmin && (
              <li><Link to="/admin" className="nav-admin">Admin</Link></li>
            )}
            <li><Link to="/#about">About</Link></li>
          </ul>
          <div className="nav-icons">
            <svg viewBox="0 0 24 24" strokeWidth="1.4" onClick={() => alert('Search feature is coming soon!')} style={{ cursor: 'pointer' }}><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
            <svg viewBox="0 0 24 24" strokeWidth="1.4" onClick={handleProfileClick} style={{ cursor: 'pointer' }}><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
            <svg viewBox="0 0 24 24" strokeWidth="1.4" onClick={() => navigate('/design')} style={{ cursor: 'pointer' }}><path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"/><line x1="3" y1="6" x2="21" y2="6"/><path d="M16 10a4 4 0 0 1-8 0"/></svg>
          </div>
        </div>
      )}
    </nav>
  );
}
