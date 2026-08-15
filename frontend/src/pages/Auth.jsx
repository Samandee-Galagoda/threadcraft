import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

export default function Auth() {
  const [tab, setTab] = useState('register');
  const [pwLength, setPwLength] = useState(0);
  const navigate = useNavigate();

  // Form states
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  // Redirect if already logged in
  useEffect(() => {
    const token = localStorage.getItem('tc_token');
    if (token) {
      navigate('/dashboard');
    }
  }, [navigate]);

  const handlePwChange = (e) => {
    setPassword(e.target.value);
    setPwLength(e.target.value.length);
  };

  const checkPwClass = (i) => {
    if (pwLength < 4) return '';
    if (pwLength < 7) return i === 0 ? 'weak' : '';
    if (pwLength < 10) return i < 2 ? 'medium' : '';
    return 'strong';
  };

  const handleGuest = () => {
    navigate('/design');
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    setError('');

    // Validations
    if (!firstName || !lastName || !email || !password) {
      setError('Please fill in all required fields.');
      return;
    }

    if (password !== confirmPassword) {
      setError('Passwords do not match. Please verify your passwords.');
      return;
    }

    if (password.length < 6) {
      setError('Password must be at least 6 characters long.');
      return;
    }

    setSubmitting(true);
    try {
      const response = await fetch('http://localhost:8000/api/auth/register', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          first_name: firstName,
          last_name: lastName,
          email: email,
          password: password,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Registration failed.');
      }

      // Store auth session
      localStorage.setItem('tc_token', data.access_token);
      localStorage.setItem('tc_user', JSON.stringify(data.user));

      // Navigate to dashboard
      navigate('/dashboard');
    } catch (err) {
      setError(err.message || 'Server error occurred. Please ensure the backend is running.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');

    if (!email || !password) {
      setError('Please fill in all required fields.');
      return;
    }

    setSubmitting(true);
    try {
      const response = await fetch('http://localhost:8000/api/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: email,
          password: password,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Login failed.');
      }

      // Store auth session
      localStorage.setItem('tc_token', data.access_token);
      localStorage.setItem('tc_user', JSON.stringify(data.user));

      // Navigate to dashboard
      navigate('/dashboard');
    } catch (err) {
      setError(err.message || 'Server error occurred. Please ensure the backend is running.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      <nav>
        <span className="nav-link" onClick={() => navigate('/')} style={{ cursor: 'pointer' }}>← Back to home</span>
        <div className="nav-logo">
          <h1>THREADCRAFT</h1>
          <p>CUSTOM CLOTHING · SRI LANKA</p>
        </div>
        <span className="nav-link" style={{ cursor: 'pointer' }}>Need help?</span>
      </nav>
      
      <div className="auth-wrap">
        <div className="auth-left">
          <div>
            <div className="auth-left-eyebrow">Welcome to ThreadCraft</div>
            <h2 className="auth-left-title">Your wardrobe,<br/><em>designed by you.</em></h2>
            <p className="auth-left-body">Create an account to save your measurements, track your orders, and reorder your favourite designs in one click.</p>
            <div className="auth-perks">
              <div className="auth-perk">
                <svg viewBox="0 0 24 24"><path d="M20 7H4a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2z"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/></svg>
                <span>Save your measurements — never re-enter them</span>
              </div>
              <div className="auth-perk">
                <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
                <span>Track every order from stitching to dispatch</span>
              </div>
              <div className="auth-perk">
                <svg viewBox="0 0 24 24"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 2 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/></svg>
                <span>Save unfinished designs and come back later</span>
              </div>
              <div className="auth-perk">
                <svg viewBox="0 0 24 24"><polyline points="17 1 21 5 17 9"/><path d="M3 11V9a4 4 0 0 1 4-4h14"/><polyline points="7 23 3 19 7 15"/><path d="M21 13v2a4 4 0 0 1-4 4H3"/></svg>
                <span>One-click reorder with saved preferences</span>
              </div>
            </div>
          </div>
          <div className="auth-left-bottom">Trusted by customers across Sri Lanka · 10-day delivery guarantee</div>
        </div>

        <div className="auth-right">
          <h2 className="auth-title">{tab === 'register' ? 'Create account' : 'Sign in'}</h2>
          <p className="auth-sub">{tab === 'register' ? 'Join us to customize your wardrobe' : 'Enter your credentials'}</p>
          
          <div className="auth-form-wrap">
            <div className="auth-tabs">
              <div className={`auth-tab ${tab === 'register' ? 'active' : ''}`} onClick={() => { setTab('register'); setError(''); }}>Create account</div>
              <div className={`auth-tab ${tab === 'login' ? 'active' : ''}`} onClick={() => { setTab('login'); setError(''); }}>Sign in</div>
            </div>

            {error && (
              <div style={{ background: '#FDF2F2', border: '.5px solid #F8B4B4', color: '#9B1C1C', fontSize: '12px', padding: '12px', marginBottom: '20px', fontFamily: "'Jost', sans-serif" }}>
                {error}
              </div>
            )}

            {tab === 'register' && (
              <form onSubmit={handleRegister}>
                <div className="field-row">
                  <div className="field">
                    <label>First name</label>
                    <input type="text" placeholder="Nimesha" value={firstName} onChange={e => setFirstName(e.target.value)} required />
                  </div>
                  <div className="field">
                    <label>Last name</label>
                    <input type="text" placeholder="Perera" value={lastName} onChange={e => setLastName(e.target.value)} required />
                  </div>
                </div>
                <div className="field">
                  <label>Email address</label>
                  <input type="email" placeholder="nimesha@email.com" value={email} onChange={e => setEmail(e.target.value)} required />
                  <div className="field-hint">Your order confirmations and mockup images will be sent here</div>
                </div>
                <div className="field">
                  <label>Password</label>
                  <input type="password" placeholder="Create a strong password" value={password} onChange={handlePwChange} required />
                  <div className="pw-strength">
                    <div className={`pw-bar ${checkPwClass(0)}`}></div>
                    <div className={`pw-bar ${checkPwClass(1)}`}></div>
                    <div className={`pw-bar ${checkPwClass(2)}`}></div>
                    <div className={`pw-bar ${checkPwClass(3)}`}></div>
                  </div>
                </div>
                <div className="field">
                  <label>Confirm password</label>
                  <input type="password" placeholder="Repeat your password" value={confirmPassword} onChange={e => setConfirmPassword(e.target.value)} required />
                </div>

                <button type="submit" className="btn-auth" disabled={submitting}>
                  {submitting ? 'Registering...' : 'Create my account'}
                </button>

                <div className="divider"><span>or</span></div>
                <button type="button" className="guest-btn" onClick={handleGuest}>Continue as guest — no account needed</button>

                <div className="auth-switch">Already have an account? <a onClick={() => { setTab('login'); setError(''); }}>Sign in here</a></div>

                <p className="terms-note">By creating an account you agree to our <a>Terms of Service</a> and <a>Privacy Policy</a>. We never share your measurements or personal data with third parties.</p>
              </form>
            )}

            {tab === 'login' && (
              <form onSubmit={handleLogin}>
                <div className="field">
                  <label>Email address</label>
                  <input type="email" placeholder="nimesha@email.com" value={email} onChange={e => setEmail(e.target.value)} required />
                </div>
                <div className="field">
                  <label>Password</label>
                  <input type="password" placeholder="Your password" value={password} onChange={e => setPassword(e.target.value)} required />
                </div>
                <a className="forgot-link" onClick={() => alert('Password reset is mock-integrated. Simply create a new account or log in with nimesha@email.com if registered!')}>Forgot your password?</a>

                <button type="submit" className="btn-auth" disabled={submitting}>
                  {submitting ? 'Signing in...' : 'Sign in to my account'}
                </button>

                <div className="divider"><span>or</span></div>
                <button type="button" className="guest-btn" onClick={handleGuest}>Continue as guest — no account needed</button>

                <div className="auth-switch">New to ThreadCraft? <a onClick={() => { setTab('register'); setError(''); }}>Create a free account</a></div>
              </form>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
