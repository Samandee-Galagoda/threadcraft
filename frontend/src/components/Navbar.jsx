import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function Navbar({ backLink = false, secure = false }) {
  // Reads AuthContext rather than localStorage directly. The old version knew
  // whether a token existed but nothing about the user, so an admin had no way
  // to reach /admin except by typing the URL.
  const { isAuthenticated, isAdmin } = useAuth();

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
            <li><Link to="/#about">About</Link></li>
            {isAuthenticated ? (
              <li>
                {/* One entry point for both roles — signing in routes an admin
                    to /admin and a customer to /dashboard, so the storefront
                    nav does not need to know the difference. */}
                <Link to={isAdmin ? '/admin' : '/dashboard'} style={{ fontWeight: 500 }}>
                  {isAdmin ? 'Admin panel' : 'My account'}
                </Link>
              </li>
            ) : (
              <li><Link to="/auth" style={{ fontWeight: 500 }}>Sign in</Link></li>
            )}
          </ul>
        </div>
      )}
    </nav>
  );
}
