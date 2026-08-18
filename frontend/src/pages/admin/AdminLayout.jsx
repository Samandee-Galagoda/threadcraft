import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

/** Icons are inline rather than from lucide-react so the sidebar's stroke
 *  weight matches the storefront's hand-drawn set exactly. */
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
  inventory: (
    <>
      <path d="M20 7H4a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2z" />
      <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16" />
    </>
  ),
  cloth: (
    <>
      <circle cx="12" cy="12" r="10" />
      <path d="M12 8v4l3 3" />
    </>
  ),
  materials: (
    <>
      <path d="M12 2 2 7l10 5 10-5-10-5z" />
      <path d="m2 17 10 5 10-5" />
      <path d="m2 12 10 5 10-5" />
    </>
  ),
  pricing: (
    <>
      <line x1="12" y1="1" x2="12" y2="23" />
      <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
    </>
  ),
  analytics: (
    <>
      <line x1="18" y1="20" x2="18" y2="10" />
      <line x1="12" y1="20" x2="12" y2="4" />
      <line x1="6" y1="20" x2="6" y2="14" />
    </>
  ),
  settings: (
    <>
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.6 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.6 1.65 1.65 0 0 0 10 3.09V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
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
      { to: '/admin', end: true, icon: 'dashboard', label: 'Dashboard' },
      { to: '/admin/orders', icon: 'orders', label: 'Orders' },
      { to: '/admin/inventory', icon: 'inventory', label: 'Inventory' },
    ],
  },
  {
    label: 'Catalogue',
    items: [
      { to: '/admin/cloth-types', icon: 'cloth', label: 'Cloth types' },
      { to: '/admin/materials', icon: 'materials', label: 'Materials' },
      { to: '/admin/pricing', icon: 'pricing', label: 'Pricing config' },
    ],
  },
  {
    label: 'Reports',
    items: [{ to: '/admin/analytics', icon: 'analytics', label: 'Analytics' }],
  },
  {
    label: 'Account',
    items: [{ to: '/admin/settings', icon: 'settings', label: 'Settings' }],
  },
];

function Icon({ name }) {
  return (
    <svg viewBox="0 0 24 24" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      {ICONS[name]}
    </svg>
  );
}

export default function AdminLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const initial = (user?.first_name || user?.email || 'A')[0].toUpperCase();

  return (
    <div className="admin-shell">
      <aside className="admin-sidebar">
        <div className="admin-sidebar-logo">
          <h1>THREADCRAFT</h1>
          <p>ADMIN PANEL</p>
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
        </nav>

        <div className="admin-sidebar-bottom">
          <div className="admin-badge">
            <div className="admin-avatar">{initial}</div>
            <div className="admin-info">
              <p>
                {user?.first_name} {user?.last_name}
              </p>
              <small>Administrator</small>
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

/** Shared page header — title, subtitle and optional actions, matching the
 *  design's main-header band. Exported so every admin page renders the same
 *  chrome rather than each inventing its own. */
export function AdminHeader({ title, subtitle, children }) {
  return (
    <div className="admin-main-header">
      <div>
        <h2>{title}</h2>
        {subtitle && <p>{subtitle}</p>}
      </div>
      {children && <div className="admin-header-actions">{children}</div>}
    </div>
  );
}
