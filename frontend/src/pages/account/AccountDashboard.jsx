import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { AdminHeader } from '../admin/AdminLayout';
import { dashboard, measurements as measurementsApi } from '../../api';
import { useAuth } from '../../context/AuthContext';
import { STATUS_LABELS, STAGES, money, shortDate, statusClass } from '../../lib/adminFormat';

export default function AccountDashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [measured, setMeasured] = useState(0);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all([dashboard.load(), measurementsApi.load().catch(() => ({ values: {} }))])
      .then(([summary, saved]) => {
        if (cancelled) return;
        setData(summary);
        setMeasured(Object.keys(saved.values || {}).length);
      })
      .catch((err) => !cancelled && setError(err.message || 'Could not load your dashboard.'));
    return () => {
      cancelled = true;
    };
  }, []);

  if (error) return <div className="admin-content wizard-error">{error}</div>;
  if (!data) return <div className="admin-content wizard-loading">Loading your account…</div>;

  const orders = data.recent_orders || [];
  const designs = data.saved_designs || [];
  const inProgress = orders.filter((o) => STAGES.includes(o.status) && o.status !== 'dispatched');

  return (
    <>
      <AdminHeader
        title={`Welcome back, ${user?.first_name || 'there'}`}
        subtitle={data.user?.created_at}
      >
        <button type="button" className="btn-sm btn-dark" onClick={() => navigate('/design')}>
          + Start a new design
        </button>
      </AdminHeader>

      <div className="admin-content">
        <div className="kpi-row">
          <div className="kpi-card dark">
            <div className="kpi-label">Total orders</div>
            <div className="kpi-value">{data.total_orders}</div>
            <div className="kpi-change">
              <Link to="/dashboard/orders">View all →</Link>
            </div>
          </div>
          <div className="kpi-card">
            <div className="kpi-label">In progress</div>
            <div className="kpi-value">{data.active_orders_count}</div>
            <div className="kpi-change">
              {inProgress.length ? 'being made now' : 'nothing in production'}
            </div>
          </div>
          <div className="kpi-card">
            <div className="kpi-label">Saved designs</div>
            <div className="kpi-value">{designs.length}</div>
            <div className="kpi-change">
              <Link to="/dashboard/designs">Reorder →</Link>
            </div>
          </div>
          <div className="kpi-card">
            <div className="kpi-label">Measurements saved</div>
            <div className="kpi-value">{measured}</div>
            <div className={`kpi-change ${measured ? '' : 'warn'}`}>
              <Link to="/dashboard/measurements">{measured ? 'Review →' : 'Add yours →'}</Link>
            </div>
          </div>
        </div>

        <div className="admin-grid-2">
          <div className="admin-card">
            <div className="admin-card-title">
              Recent orders <Link to="/dashboard/orders">View all →</Link>
            </div>
            {orders.length === 0 ? (
              <p className="admin-empty-row">
                No orders yet — <Link to="/design">design your first garment</Link>.
              </p>
            ) : (
              <table className="orders-table">
                <thead>
                  <tr>
                    <th>Order</th>
                    <th>Garment</th>
                    <th>Total</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {orders.slice(0, 5).map((order) => (
                    <tr key={order.order_number}>
                      <td>{order.order_number}</td>
                      <td>{order.cloth_type_name}</td>
                      <td>{money(order.price_total)}</td>
                      <td>
                        <span className={`status-badge ${statusClass(order.status)}`}>
                          {STATUS_LABELS[order.status] ?? order.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          <div className="admin-card">
            <div className="admin-card-title">
              Saved designs <Link to="/dashboard/designs">Manage →</Link>
            </div>
            {designs.length === 0 ? (
              <p className="admin-empty-row">
                Nothing saved yet. Designs you save in the wizard appear here so you can reorder
                them in one click.
              </p>
            ) : (
              designs.slice(0, 5).map((design) => (
                <div className="mini-stat" key={design.id}>
                  <span className="mini-stat-label">{design.name}</span>
                  <span className="mini-stat-val">
                    {design.estimated_total ? money(design.estimated_total) : '—'}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>

        {inProgress.length > 0 && (
          <div className="admin-card" style={{ marginTop: 20 }}>
            <div className="admin-card-title">Being made now</div>
            {inProgress.map((order) => {
              const index = STAGES.indexOf(order.status);
              return (
                <div className="inv-item" key={order.order_number}>
                  <div className="inv-row">
                    <span className="inv-name">
                      {order.cloth_type_name} · {order.order_number}
                    </span>
                    <span className="inv-stock">
                      {STATUS_LABELS[order.status]} · ordered {shortDate(order.created_at)}
                    </span>
                  </div>
                  <div className="inv-bar">
                    <div
                      className="inv-fill"
                      style={{ width: `${((index + 1) / STAGES.length) * 100}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </>
  );
}
