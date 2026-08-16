import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import Navbar from '../components/Navbar';
import { mediaUrl, orders } from '../api';

const STAGES = [
  { key: 'received', label: 'Received', blurb: 'We have your order and your measurements.' },
  { key: 'fabric_cut', label: 'Fabric cut', blurb: 'Your fabric has been cut to your measurements.' },
  { key: 'stitching', label: 'Stitching', blurb: 'Your garment is being stitched.' },
  { key: 'qc', label: 'QC check', blurb: 'Final quality check before dispatch.' },
  { key: 'dispatched', label: 'Dispatched', blurb: 'On its way to you.' },
];

export default function OrderTracking() {
  const { orderNumber: paramNumber } = useParams();
  const navigate = useNavigate();

  const [query, setQuery] = useState(paramNumber ?? '');
  const [order, setOrder] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(Boolean(paramNumber));

  useEffect(() => {
    if (!paramNumber) return;
    // Data fetch driven by the route param; the results land asynchronously.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoading(true);
    orders
      .track(paramNumber)
      .then((data) => {
        setOrder(data);
        setError(null);
      })
      .catch((err) => {
        setOrder(null);
        setError(err.status === 404 ? 'No order found with that reference.' : err.message);
      })
      .finally(() => setLoading(false));
  }, [paramNumber]);

  function handleSubmit(event) {
    event.preventDefault();
    if (query.trim()) navigate(`/track/${encodeURIComponent(query.trim())}`);
  }

  const currentIndex = order ? STAGES.findIndex((s) => s.key === order.status) : -1;
  const isCancelled = order?.status === 'cancelled';

  return (
    <>
      <Navbar />
      <div className="page-header">
        <div className="page-header-eyebrow">Order Tracking</div>
        <h1>Where&apos;s my garment?</h1>
        <div className="page-header-rule">
          <span>✦</span>
        </div>
        <p>Enter the order reference from your confirmation to see live progress.</p>
      </div>

      <div className="track-page">
        <form className="track-form" onSubmit={handleSubmit}>
          <input
            type="text"
            value={query}
            placeholder="TC-2026-XXXXXX"
            onChange={(e) => setQuery(e.target.value)}
            aria-label="Order reference"
          />
          <button type="submit" className="btn-primary">
            Track
          </button>
        </form>

        {loading && <div className="wizard-loading">Looking up your order…</div>}
        {error && <div className="wizard-error">{error}</div>}

        {order && !loading && (
          <div className="track-result">
            <div className="track-head">
              <div>
                <div className="order-num">{order.order_number}</div>
                <p className="track-sub">
                  {order.cloth_type_name} · {order.material_name}
                  {order.color_name ? ` · ${order.color_name}` : ''}
                </p>
              </div>
              <div className="order-price">
                {order.currency} {Number(order.price_total).toLocaleString()}
              </div>
            </div>

            {isCancelled ? (
              <div className="wizard-error">This order was cancelled.</div>
            ) : (
              <div className="track-timeline">
                {STAGES.map((stage, index) => (
                  <div
                    className={`track-stage ${index < currentIndex ? 'done' : ''} ${
                      index === currentIndex ? 'current' : ''
                    }`}
                    key={stage.key}
                  >
                    <div className="track-dot">{index < currentIndex ? '✓' : index + 1}</div>
                    <div className="track-stage-body">
                      <div className="track-stage-label">{stage.label}</div>
                      <div className="track-stage-blurb">{stage.blurb}</div>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {order.mockup_url && (
              <div className="track-mockup">
                <img src={mediaUrl(order.mockup_url)} alt="Your design preview" />
                <span>Your AI preview at the time of ordering</span>
              </div>
            )}
          </div>
        )}
      </div>
    </>
  );
}
