import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import RevenueChart from '../../components/admin/RevenueChart';
import { admin } from '../../api';

const money = (v) => `LKR ${Number(v).toLocaleString(undefined, { minimumFractionDigits: 2 })}`;

export default function AdminOverview() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [days, setDays] = useState(30);

  useEffect(() => {
    let cancelled = false;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setError(null);
    admin
      .analytics(days)
      .then((result) => !cancelled && setData(result))
      .catch((err) => !cancelled && setError(err.message || 'Could not load analytics.'));
    return () => {
      cancelled = true;
    };
  }, [days]);

  if (error) return <div className="wizard-error">{error}</div>;
  if (!data) return <div className="wizard-loading">Loading analytics…</div>;

  const s = data.summary;
  const health = data.catalogue_health;

  return (
    <>
      <div className="portal-header">
        <h1>Overview</h1>
        <p>Business at a glance</p>
      </div>

      {s.low_stock_materials > 0 && (
        <div className="admin-alert">
          <strong>{s.low_stock_materials}</strong> material
          {s.low_stock_materials === 1 ? ' is' : 's are'} at or below the low-stock threshold.{' '}
          <Link to="/admin/inventory">Review inventory →</Link>
        </div>
      )}

      {health.cloth_types_without_measurement_fields.length > 0 && (
        <div className="admin-alert warn">
          {health.cloth_types_without_measurement_fields.join(', ')}{' '}
          {health.cloth_types_without_measurement_fields.length === 1 ? 'has' : 'have'} no
          measurement fields — Step 4 of the wizard will be empty for{' '}
          {health.cloth_types_without_measurement_fields.length === 1 ? 'it' : 'them'}.{' '}
          <Link to="/admin/catalogue">Fix in catalogue →</Link>
        </div>
      )}

      <div className="welcome-row">
        <div className="welcome-card dark">
          <div className="wc-num">{money(s.total_revenue)}</div>
          <div className="wc-label">Revenue (paid orders)</div>
        </div>
        <div className="welcome-card">
          <div className="wc-num">{s.total_orders}</div>
          <div className="wc-label">Total orders</div>
          <div className="wc-action">{s.paid_orders} paid</div>
        </div>
        <div className="welcome-card">
          <div className="wc-num">{money(s.average_order_value)}</div>
          <div className="wc-label">Average order value</div>
        </div>
        <div className="welcome-card">
          <div className="wc-num">
            {s.average_fulfilment_days == null ? '—' : `${s.average_fulfilment_days}d`}
          </div>
          <div className="wc-label">Avg fulfilment</div>
          <div className="wc-action">{s.dispatched_orders} dispatched</div>
        </div>
      </div>

      <div className="card">
        <div className="card-head">
          <div className="card-title">Revenue trend</div>
          <div className="range-toggle">
            {[7, 30, 90].map((option) => (
              <button
                type="button"
                key={option}
                className={days === option ? 'active' : ''}
                onClick={() => setDays(option)}
              >
                {option}d
              </button>
            ))}
          </div>
        </div>
        <RevenueChart trend={data.revenue_trend} />
      </div>

      <div className="grid-2">
        <div className="card">
          <div className="card-head">
            <div className="card-title">Order pipeline</div>
          </div>
          {data.status_breakdown.map((row) => (
            <div className="order-item" key={row.status}>
              <div className="order-info">
                <div className="order-name">{row.status.replace('_', ' ')}</div>
              </div>
              <div className="order-price">{row.count}</div>
            </div>
          ))}
        </div>

        <div className="card">
          <div className="card-head">
            <div className="card-title">Most ordered garments</div>
          </div>
          {data.popular_cloth_types.length === 0 ? (
            <p className="admin-empty">No orders yet.</p>
          ) : (
            data.popular_cloth_types.map((row) => (
              <div className="order-item" key={row.name}>
                <div className="order-info">
                  <div className="order-name">{row.name}</div>
                  <div className="order-detail">{money(row.revenue)} revenue</div>
                </div>
                <div className="order-price">{row.orders}</div>
              </div>
            ))
          )}
        </div>
      </div>

      <div className="card" style={{ marginTop: 20 }}>
        <div className="card-head">
          <div className="card-title">Most used materials</div>
        </div>
        {data.popular_materials.length === 0 ? (
          <p className="admin-empty">No orders yet.</p>
        ) : (
          data.popular_materials.map((row) => (
            <div className="order-item" key={row.name}>
              <div className="order-info">
                <div className="order-name">{row.name}</div>
                <div className="order-detail">{Number(row.metres_used).toFixed(2)} m used</div>
              </div>
              <div className="order-price">{row.orders}</div>
            </div>
          ))
        )}
      </div>
    </>
  );
}
