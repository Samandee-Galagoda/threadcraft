/**
 * Inline SVG line chart. Deliberately not a charting library — this is the only
 * chart in the app, and recharts would add ~150 KB to the bundle to draw one
 * polyline. The data is already zero-filled server-side, so the x-axis is
 * evenly spaced by construction.
 */
export default function RevenueChart({ trend }) {
  if (!trend?.length) return <p className="admin-empty">No revenue data yet.</p>;

  const values = trend.map((d) => Number(d.revenue));
  const max = Math.max(...values, 1);
  const width = 720;
  const height = 200;
  const padding = { top: 12, right: 12, bottom: 24, left: 52 };
  const plotW = width - padding.left - padding.right;
  const plotH = height - padding.top - padding.bottom;

  const x = (i) => padding.left + (trend.length === 1 ? plotW / 2 : (i / (trend.length - 1)) * plotW);
  const y = (v) => padding.top + plotH - (v / max) * plotH;

  const line = values.map((v, i) => `${i === 0 ? 'M' : 'L'} ${x(i)} ${y(v)}`).join(' ');
  const area = `${line} L ${x(values.length - 1)} ${padding.top + plotH} L ${x(0)} ${padding.top + plotH} Z`;

  // Label roughly six dates, whatever the range, so they never overlap.
  const step = Math.max(1, Math.floor(trend.length / 6));
  const total = values.reduce((sum, v) => sum + v, 0);

  return (
    <div className="chart-block">
      <div className="chart-total">
        LKR {total.toLocaleString(undefined, { minimumFractionDigits: 2 })}
        <span> over {trend.length} days</span>
      </div>
      <svg viewBox={`0 0 ${width} ${height}`} className="revenue-chart" role="img"
           aria-label={`Revenue over the last ${trend.length} days`}>
        {[0, 0.5, 1].map((f) => (
          <g key={f}>
            <line x1={padding.left} x2={width - padding.right}
                  y1={y(max * f)} y2={y(max * f)} className="chart-grid" />
            <text x={padding.left - 8} y={y(max * f) + 4} className="chart-axis" textAnchor="end">
              {Math.round(max * f).toLocaleString()}
            </text>
          </g>
        ))}
        <path d={area} className="chart-area" />
        <path d={line} className="chart-line" />
        {values.map((v, i) => v > 0 && (
          <circle key={trend[i].date} cx={x(i)} cy={y(v)} r="3" className="chart-dot">
            <title>{`${trend[i].date}: LKR ${v.toLocaleString()} (${trend[i].orders} orders)`}</title>
          </circle>
        ))}
        {trend.map((d, i) => i % step === 0 && (
          <text key={d.date} x={x(i)} y={height - 6} className="chart-axis" textAnchor="middle">
            {d.date.slice(5)}
          </text>
        ))}
      </svg>
    </div>
  );
}
