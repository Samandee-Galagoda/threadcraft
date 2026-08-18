import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

/** The customer portal deliberately reuses the admin panel's shell classes
 *  (.admin-shell / .admin-sidebar / .admin-nav-item …) rather than cloning the
 *  CSS under new names. Two copies of a dark-sidebar layout would drift apart
 *  the first time either is restyled. Only the nav contents differ. */
const ICONS = {
  dashboard: (
    <>
      <rect x="3" y="3" width="7" height="7" />
      <rect x="14" y="3" width="7" height="7" />
      <rect x="14" y="14" width="7" height="7" />
      <rect x="3" y="14" width="7" height="7" />
    </>
  ),
  orders: (
    <>
      <path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z" />
      <line x1="3" y1="6" x2="21" y2="6" />
      <path d="M16 10a4 4 0 0 1-8 0" />
    </>
  ),
  measurements: (
    <>
      <path d="M2 12h20" />
      <path d="M6 8v8M10 9v6M14 9v6M18 8v8" />
    </>
  ),
  designs: (
    <>
      <path d="M12 2 2 7l10 5 10-5-10-5z" />
      <path d="m2 17 10 5 10-5" />
      <path d="m2 12 10 5 10-5" />
    </>
  ),
  profile: (
    <>
      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
      <circle cx="12" cy="7" r="4" />
    </>
  ),
  logout: (
    <>
      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
      <polyline points="16 17 21 12 16 7" />
      <line x1="21" y1="12" x2="9" y2="12" />
    </>
  ),
};

const SECTIONS = [
  {
    label: 'Main',
    items: [
      { to: '/dashboard', end: true, icon: 'dashboard', label: 'Dashboard' },
      { to: '/dashboard/orders', icon: 'orders', label: 'My orders' },
    ],
  },
  {
    label: 'My details',
    items: [
      { to: '/dashboard/measurements', icon: 'measurements', label: 'Measurements' },
      { to: '/dashboard/designs', icon: 'designs', label: 'Saved designs' },
    ],
  },
  {
    label: 'Account',
    items: [{ to: '/dashboard/profile', icon: 'profile', label: 'Profile' }],
  },
];

function Icon({ name }) {
  return (
    <svg viewBox="0 0 24 24" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      {ICONS[name]}
    </svg>
  );
}

export default function AccountLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const initial = (user?.first_name || user?.email || 'C')[0].toUpperCase();

  return (
    <div className="admin-shell">
      <aside className="admin-sidebar">
        <div className="admin-sidebar-logo">
          <h1>THREADCRAFT</h1>
          <p>MY ACCOUNT</p>
        </div>

        <nav className="admin-nav">
          {SECTIONS.map((section) => (
            <div key={section.label}>
              <div className="admin-nav-label">{section.label}</div>
              {section.items.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.end}
                  className={({ isActive }) => `admin-nav-item ${isActive ? 'active' : ''}`}
                >
                  <Icon name={item.icon} />
                  <span>{item.label}</span>
                </NavLink>
              ))}
            </div>
          ))}

          <div className="admin-nav-label">Shop</div>
          <button type="button" className="admin-nav-item" onClick={() => navigate('/design')}>
            <Icon name="designs" />
            <span>Start a new design</span>
          </button>
          <button type="button" className="admin-nav-item" onClick={() => navigate('/')}>
            <Icon name="dashboard" />
            <span>Back to shop</span>
          </button>
        </nav>

        <div className="admin-sidebar-bottom">
          <div className="admin-badge">
            <div className="admin-avatar">{initial}</div>
            <div className="admin-info">
              <p>
                {user?.first_name} {user?.last_name}
              </p>
              <small>Customer</small>
            </div>
          </div>
          <button
            type="button"
            className="admin-nav-item admin-logout"
            onClick={() => {
              logout();
              navigate('/');
            }}
          >
            <Icon name="logout" />
            <span>Sign out</span>
          </button>
        </div>
      </aside>

      <main className="admin-main">
        <Outlet />
      </main>
    </div>
  );
}
