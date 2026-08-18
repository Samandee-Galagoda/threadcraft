import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { AdminHeader } from './AdminLayout';
import { admin } from '../../api';
import { STATUS_LABELS, money, statusClass } from '../../lib/adminFormat';

function greeting() {
  const hour = new Date().getHours();
  if (hour < 12) return 'Good morning';
  return hour < 18 ? 'Good afternoon' : 'Good evening';
}

/** Sparkline over the weekly buckets. Same reasoning as the customer-side
 *  chart: one polyline does not justify a charting dependency. */
function WeeklyChart({ buckets }) {
  if (!buckets?.length) return <div className="admin-empty-row">No orders yet.</div>;

  const values = buckets.map((b) => Number(b.revenue));
  const max = Math.max(...values, 1);
  const step = buckets.length > 1 ? 280 / (buckets.length - 1) : 0;
  const y = (v) => 92 - (v / max) * 84;
  const points = values.map((v, i) => `${i * step},${y(v)}`).join(' ');

  return (
    <>
      <div className="chart-placeholder">
        <svg viewBox="0 0 280 100" preserveAspectRatio="none">
          <defs>
            <linearGradient id="area-fill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#C4A882" stopOpacity=".4" />
              <stop offset="100%" stopColor="#C4A882" stopOpacity="0" />
            </linearGradient>
          </defs>
          <polygon
            className="chart-area"
            points={`${points} 280,100 0,100`}
            fill="url(#area-fill)"
          />
          <polyline className="chart-line" points={points} />
        </svg>
      </div>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          marginTop: 10,
        }}
      >
        <span style={{ fontSize: 11, color: 'var(--taupe)' }}>{buckets[0].label}</span>
        <span
          style={{
            fontFamily: 'var(--serif)',
            fontSize: 16,
            color: 'var(--brown)',
          }}
        >
          {money(values.reduce((sum, v) => sum + v, 0))}
        </span>
        <span style={{ fontSize: 11, color: 'var(--taupe)' }}>
          {buckets[buckets.length - 1].label}
        </span>
      </div>
    </>
  );
}

export default function AdminDashboard() {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [weekly, setWeekly] = useState(null);
  const [orders, setOrders] = useState([]);
  const [materials, setMaterials] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all([admin.analytics(30), admin.weekly(8), admin.orders(), admin.materials()])
      .then(([analytics, week, orderList, materialList]) => {
        if (cancelled) return;
        setData(analytics);
        setWeekly(week);
        setOrders(orderList.slice(0, 6));
        setMaterials(materialList);
      })
      .catch((err) => !cancelled && setError(err.message || 'Could not load the dashboard.'));
    return () => {
      cancelled = true;
    };
  }, []);

  if (error) return <div className="admin-content wizard-error">{error}</div>;
  if (!data) return <div className="admin-content wizard-loading">Loading dashboard…</div>;

  const s = data.summary;
  const thisWeek = weekly?.buckets?.[weekly.buckets.length - 1];
  const lastWeek = weekly?.buckets?.[weekly.buckets.length - 2];
  const weekDelta =
    lastWeek && Number(lastWeek.revenue) > 0
      ? Math.round(
          ((Number(thisWeek.revenue) - Number(lastWeek.revenue)) / Number(lastWeek.revenue)) * 100,
        )
      : null;

  // Every colourway across every material, worst-stocked first — the thing an
  // admin actually needs to act on.
  const colours = materials
    .flatMap((m) => (m.colors || []).map((c) => ({ ...c, material: m.name })))
    .sort((a, b) => Number(a.stock_metres) - Number(b.stock_metres))
    .slice(0, 6);

  const popularMax = Math.max(...(data.popular_cloth_types.map((r) => r.orders) || [1]), 1);

  return (
    <>
      <AdminHeader
        title="Dashboard"
        subtitle={`${new Date().toLocaleDateString('en-GB', {
          weekday: 'long',
          day: 'numeric',
          month: 'long',
          year: 'numeric',
        })} · ${greeting()}`}
      >
        <button
          type="button"
          className="btn-sm btn-light"
          onClick={() => navigate('/admin/analytics')}
        >
          Export report
        </button>
        <button
          type="button"
          className="btn-sm btn-dark"
          onClick={() => navigate('/admin/cloth-types')}
        >
          + New cloth type
        </button>
      </AdminHeader>

      <div className="admin-content">
        <div className="kpi-row">
          <div className="kpi-card dark">
            <div className="kpi-label">Total orders</div>
            <div className="kpi-value">{s.total_orders}</div>
            <div className="kpi-change">{thisWeek ? `${thisWeek.orders} this week` : '—'}</div>
          </div>
          <div className="kpi-card">
            <div className="kpi-label">Revenue (paid)</div>
            <div className="kpi-value">{money(s.total_revenue)}</div>
            <div className="kpi-change">
              {weekDelta === null
                ? `${s.paid_orders} paid orders`
                : `${weekDelta >= 0 ? '↑' : '↓'} ${Math.abs(weekDelta)}% vs last week`}
            </div>
          </div>
          <div className="kpi-card">
            <div className="kpi-label">In production</div>
            <div className="kpi-value">{s.active_orders}</div>
            <div className={`kpi-change ${s.low_stock_materials ? 'warn' : ''}`}>
              {s.low_stock_materials
                ? `${s.low_stock_materials} material${s.low_stock_materials === 1 ? '' : 's'} low`
                : 'stock healthy'}
            </div>
          </div>
          <div className="kpi-card">
            <div className="kpi-label">Avg order value</div>
            <div className="kpi-value">{money(s.average_order_value)}</div>
            <div className="kpi-change">
              {s.average_fulfilment_days == null
                ? '—'
                : `${s.average_fulfilment_days}d avg fulfilment`}
            </div>
          </div>
        </div>

        <div className="admin-card" style={{ marginBottom: 20 }}>
          <div className="admin-card-title">
            Recent orders <Link to="/admin/orders">View all →</Link>
          </div>
          {orders.length === 0 ? (
            <p className="admin-empty-row">No orders yet.</p>
          ) : (
            <table className="orders-table">
              <thead>
                <tr>
                  <th>Order #</th>
                  <th>Customer</th>
                  <th>Garment</th>
                  <th>Material</th>
                  <th>Total</th>
                  <th>Status</th>
                  <th>Date</th>
                </tr>
              </thead>
              <tbody>
                {orders.map((order) => (
                  <tr
                    key={order.id}
                    style={{ cursor: 'pointer' }}
                    onClick={() => navigate('/admin/orders')}
                  >
                    <td>{order.order_number}</td>
                    <td>{order.guest_name || order.guest_email || 'Account customer'}</td>
                    <td>{order.cloth_type_name}</td>
                    <td>
                      {order.material_name}
                      {order.color_name ? ` · ${order.color_name}` : ''}
                    </td>
                    <td>{money(order.price_total)}</td>
                    <td>
                      <span className={`status-badge ${statusClass(order.status)}`}>
                        {STATUS_LABELS[order.status] ?? order.status}
                      </span>
                    </td>
                    <td>
                      {new Date(order.created_at).toLocaleDateString('en-GB', {
                        day: 'numeric',
                        month: 'short',
                      })}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <div className="admin-grid-3">
          <div className="admin-card">
            <div className="admin-card-title">
              Material stock <Link to="/admin/inventory">Manage →</Link>
            </div>
            {colours.length === 0 ? (
              <p className="admin-empty-row">No materials configured.</p>
            ) : (
              colours.map((colour) => {
                const stock = Number(colour.stock_metres);
                const threshold = Number(colour.low_stock_threshold);
                const level = stock <= threshold / 2 ? 'critical' : stock <= threshold ? 'low' : '';
                const pct = Math.max(2, Math.min(100, (stock / (threshold * 4 || 1)) * 100));
                return (
                  <div className="inv-item" key={colour.id}>
                    <div className="inv-row">
                      <span className="inv-name">
                        <span className="colour-dot" style={{ background: colour.hex_code }} />
                        {colour.material} · {colour.name}
                      </span>
                      <span className={`inv-stock ${level}`}>
                        {stock.toFixed(1)}m
                        {level === 'critical' ? ' ⚠' : level === 'low' ? ' ⚠' : ''}
                      </span>
                    </div>
                    <div className="inv-bar">
                      <div className={`inv-fill ${level}`} style={{ width: `${pct}%` }} />
                    </div>
                  </div>
                );
              })
            )}
          </div>

          <div className="admin-card">
            <div className="admin-card-title">Most ordered</div>
            {data.popular_cloth_types.length === 0 ? (
              <p className="admin-empty-row">No orders yet.</p>
            ) : (
              data.popular_cloth_types.slice(0, 6).map((row) => (
                <div className="mini-stat" key={row.name}>
                  <span className="mini-stat-label">{row.name}</span>
                  <span className="mini-stat-val">{row.orders}</span>
                  <div className="mini-stat-bar">
                    <div
                      className="mini-stat-fill"
                      style={{ width: `${(row.orders / popularMax) * 100}%` }}
                    />
                  </div>
                </div>
              ))
            )}
          </div>

          <div className="admin-card">
            <div className="admin-card-title">
              Revenue · last 8 weeks <Link to="/admin/analytics">Detail →</Link>
            </div>
            <WeeklyChart buckets={weekly?.buckets} />
          </div>
        </div>
      </div>
    </>
  );
}
