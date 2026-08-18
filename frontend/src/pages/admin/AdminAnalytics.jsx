import { useEffect, useState } from 'react';
import { AdminHeader } from './AdminLayout';
import { admin } from '../../api';
import { STATUS_LABELS, money, moneyExact, statusClass } from '../../lib/adminFormat';

/** Weekly bars rather than a line: the question here is "how much work came in
 *  each week", which is a comparison between discrete buckets, not a trend
 *  through continuous time. */
function WeeklyBars({ buckets }) {
  const max = Math.max(...buckets.map((b) => b.orders), 1);
  return (
    <div className="week-bars">
      {buckets.map((bucket) => (
        <div className="week-bar" key={bucket.week_start}>
          <div className="week-bar-value">{bucket.orders}</div>
          <div className="week-bar-track">
            <div
              className="week-bar-fill"
              style={{ height: `${Math.max(3, (bucket.orders / max) * 100)}%` }}
              title={`${bucket.orders} orders · ${moneyExact(bucket.revenue)}`}
            />
          </div>
          <div className="week-bar-label">{bucket.label}</div>
        </div>
      ))}
    </div>
  );
}

function toCsv(rows) {
  // Quotes doubled and every field wrapped, so a garment called
  // 'Kurta, long' cannot shift every later column.
  const escape = (v) => `"${String(v ?? '').replace(/"/g, '""')}"`;
  return rows.map((row) => row.map(escape).join(',')).join('\n');
}

export default function AdminAnalytics() {
  const [weeks, setWeeks] = useState(8);
  const [weekly, setWeekly] = useState(null);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all([admin.weekly(weeks), admin.analytics(90)])
      .then(([week, analytics]) => {
        if (cancelled) return;
        setWeekly(week);
        setData(analytics);
      })
      .catch((err) => !cancelled && setError(err.message || 'Could not load analytics.'));
    return () => {
      cancelled = true;
    };
  }, [weeks]);

  function exportCsv() {
    const rows = [
      ['Week beginning', 'Week ending', 'Orders', 'Revenue (LKR, paid only)'],
      ...weekly.buckets.map((b) => [b.week_start, b.week_end, b.orders, b.revenue]),
      [],
      ['Garment', 'Orders', 'Revenue (LKR)'],
      ...data.popular_cloth_types.map((r) => [r.name, r.orders, r.revenue]),
      [],
      ['Material', 'Orders', 'Metres used'],
      ...data.popular_materials.map((r) => [r.name, r.orders, r.metres_used]),
    ];
    const blob = new Blob([toCsv(rows)], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `threadcraft-report-${new Date().toISOString().slice(0, 10)}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  }

  if (error) return <div className="admin-content wizard-error">{error}</div>;
  if (!weekly || !data)
    return <div className="admin-content wizard-loading">Loading analytics…</div>;

  const s = data.summary;
  const totalOrders = weekly.buckets.reduce((sum, b) => sum + b.orders, 0);
  const totalRevenue = weekly.buckets.reduce((sum, b) => sum + Number(b.revenue), 0);
  const busiest = weekly.buckets.reduce((a, b) => (b.orders > a.orders ? b : a), weekly.buckets[0]);

  return (
    <>
      <AdminHeader
        title="Analytics"
        subtitle={`Order volume and revenue over the last ${weeks} weeks`}
      >
        <div className="range-toggle">
          {[4, 8, 12].map((option) => (
            <button
              type="button"
              key={option}
              className={weeks === option ? 'active' : ''}
              onClick={() => setWeeks(option)}
            >
              {option}w
            </button>
          ))}
        </div>
        <button type="button" className="btn-sm btn-light" onClick={exportCsv}>
          Export report
        </button>
      </AdminHeader>

      <div className="admin-content">
        <div className="kpi-row">
          <div className="kpi-card dark">
            <div className="kpi-label">Orders · {weeks} weeks</div>
            <div className="kpi-value">{totalOrders}</div>
            <div className="kpi-change">{(totalOrders / weeks).toFixed(1)} per week average</div>
          </div>
          <div className="kpi-card">
            <div className="kpi-label">Revenue · {weeks} weeks</div>
            <div className="kpi-value">{money(totalRevenue)}</div>
            <div className="kpi-change">paid orders only</div>
          </div>
          <div className="kpi-card">
            <div className="kpi-label">Busiest week</div>
            <div className="kpi-value">{busiest.orders}</div>
            <div className="kpi-change">week of {busiest.label}</div>
          </div>
          <div className="kpi-card">
            <div className="kpi-label">Avg fulfilment</div>
            <div className="kpi-value">
              {s.average_fulfilment_days == null ? '—' : `${s.average_fulfilment_days}d`}
            </div>
            <div className="kpi-change">received → dispatched</div>
          </div>
        </div>

        <div className="admin-card" style={{ marginBottom: 20 }}>
          <div className="admin-card-title">Orders per week</div>
          <WeeklyBars buckets={weekly.buckets} />
        </div>

        <div className="admin-grid-3">
          <div className="admin-card">
            <div className="admin-card-title">Order pipeline</div>
            {data.status_breakdown.map((row) => (
              <div className="mini-stat" key={row.status}>
                <span className="mini-stat-label">
                  <span className={`status-badge ${statusClass(row.status)}`}>
                    {STATUS_LABELS[row.status] ?? row.status}
                  </span>
                </span>
                <span className="mini-stat-val">{row.count}</span>
              </div>
            ))}
          </div>

          <div className="admin-card">
            <div className="admin-card-title">Most ordered garments</div>
            {data.popular_cloth_types.length === 0 ? (
              <p className="admin-empty-row">No orders yet.</p>
            ) : (
              data.popular_cloth_types.slice(0, 6).map((row) => (
                <div className="mini-stat" key={row.name}>
                  <span className="mini-stat-label">{row.name}</span>
                  <span className="mini-stat-val">{row.orders}</span>
                </div>
              ))
            )}
          </div>

          <div className="admin-card">
            <div className="admin-card-title">Fabric consumed</div>
            {data.popular_materials.length === 0 ? (
              <p className="admin-empty-row">No orders yet.</p>
            ) : (
              data.popular_materials.slice(0, 6).map((row) => (
                <div className="mini-stat" key={row.name}>
                  <span className="mini-stat-label">{row.name}</span>
                  <span className="mini-stat-val">{Number(row.metres_used).toFixed(1)}m</span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </>
  );
}
