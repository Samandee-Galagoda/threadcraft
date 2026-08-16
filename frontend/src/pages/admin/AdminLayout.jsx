import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

const NAV = [
  { to: '/admin', end: true, label: 'Overview' },
  { to: '/admin/orders', label: 'Orders' },
  { to: '/admin/inventory', label: 'Inventory' },
  { to: '/admin/catalogue', label: 'Catalogue' },
  { to: '/admin/settings', label: 'Settings' },
];

export default function AdminLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="portal">
      <aside className="portal-sidebar admin-sidebar">
        <div className="portal-user">
          <div className="user-avatar">{(user?.first_name || 'A')[0].toUpperCase()}</div>
          <div className="user-name">
            {user?.first_name} {user?.last_name}
          </div>
          <div className="user-email">{user?.email}</div>
          <div className="user-since">Administrator</div>
        </div>

        <nav className="portal-nav">
          <div className="portal-nav-label">Manage</div>
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) => `portal-nav-item ${isActive ? 'active' : ''}`}
            >
              <span>{item.label}</span>
            </NavLink>
          ))}

          <div className="portal-nav-label">Account</div>
          <button type="button" className="portal-nav-item" onClick={() => navigate('/')}>
            <span>View storefront</span>
          </button>
          <button
            type="button"
            className="portal-nav-item"
            onClick={() => {
              logout();
              navigate('/');
            }}
          >
            <span>Sign out</span>
          </button>
        </nav>
      </aside>

      <main className="portal-main">
        <Outlet />
      </main>
    </div>
  );
}
