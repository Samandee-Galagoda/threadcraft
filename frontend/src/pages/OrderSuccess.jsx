import { useEffect, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import Navbar from '../components/Navbar';
import { mediaUrl, orders } from '../api';

const STAGES = [
  { key: 'received', label: 'Received' },
  { key: 'fabric_cut', label: 'Fabric cut' },
  { key: 'stitching', label: 'Stitching' },
  { key: 'qc', label: 'QC check' },
  { key: 'dispatched', label: 'Dispatched' },
];

export default function OrderSuccess() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const orderNumber = params.get('order');

  const [order, setOrder] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Data fetch on mount — the setState calls resolve asynchronously, so the
    // cascading-render case this rule guards against doesn't apply.
    /* eslint-disable react-hooks/set-state-in-effect */
    if (!orderNumber) {
      setError('No order reference was provided.');
      setLoading(false);
      return;
    }
    orders
      .track(orderNumber)
      .then(setOrder)
      .catch((err) => setError(err.message || 'Could not load your order.'))
      .finally(() => setLoading(false));
    /* eslint-enable react-hooks/set-state-in-effect */
  }, [orderNumber]);

  if (loading) {
    return (
      <>
        <Navbar secure />
        <div className="success-page">
          <div className="spinner" />
          <p className="success-sub">Loading your order…</p>
        </div>
      </>
    );
  }

  if (error || !order) {
    return (
      <>
        <Navbar secure />
        <div className="success-page">
          <h1 className="success-title">Order not found</h1>
          <p className="success-sub">{error}</p>
          <div className="success-actions">
            <button type="button" className="btn-primary" onClick={() => navigate('/design')}>
              Start a new design
            </button>
          </div>
        </div>
      </>
    );
  }

  const currentIndex = STAGES.findIndex((s) => s.key === order.status);

  return (
    <>
      <Navbar secure />
      <div className="success-page">
        <div className="success-icon">
          <svg viewBox="0 0 24 24">
            <polyline points="20 6 9 17 4 12" />
          </svg>
        </div>
        <div className="success-eyebrow">Order Confirmed</div>
        <h1 className="success-title">
          Your garment is
          <br />
          <em>on its way</em>
        </h1>
        <p className="success-sub">
          Thank you. We&apos;ve recorded your {order.cloth_type_name.toLowerCase()} in{' '}
          {order.material_name}
          {order.color_name ? ` (${order.color_name})` : ''} and our team will begin work shortly.
        </p>

        {order.mockup_url && (
          <div className="success-mockup">
            <img src={mediaUrl(order.mockup_url)} alt="Your AI generated preview" />
            <div className="success-mockup-label">
              Your AI preview — an approximation, not the finished garment
            </div>
          </div>
        )}

        <div className="order-num">Order {order.order_number}</div>

        <div className="timeline-strip">
          {STAGES.map((stage, index) => (
            <div
              className={`tl-item ${index <= currentIndex ? 'active' : ''}`}
              key={stage.key}
            >
              <div className="tl-dot" />
              <div className="tl-label">{stage.label}</div>
            </div>
          ))}
        </div>

        <div className="success-summary">
          <div className="summary-row">
            <span className="summary-key">Total</span>
            <span className="summary-val">
              {order.currency} {Number(order.price_total).toLocaleString()}
            </span>
          </div>
          <div className="summary-row">
            <span className="summary-key">Fabric used</span>
            <span className="summary-val">{Number(order.fabric_metres_used)} m</span>
          </div>
          <div className="summary-row">
            <span className="summary-key">Payment</span>
            <span className="summary-val">{order.payment_status}</span>
          </div>
        </div>

        <div className="success-actions">
          <Link to={`/track/${order.order_number}`} className="btn-primary">
            Track my order
          </Link>
          <button type="button" className="btn-secondary" onClick={() => navigate('/design')}>
            Design another
          </button>
        </div>
      </div>
    </>
  );
}
