import { useEffect, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import Navbar from '../components/Navbar';
import { mediaUrl, orders, payments } from '../api';

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
  const sessionId = params.get('session_id');

  const [order, setOrder] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [payNote, setPayNote] = useState(null);
  const [paying, setPaying] = useState(false);

  useEffect(() => {
    // Data fetch on mount — the setState calls resolve asynchronously, so the
    // cascading-render case this rule guards against doesn't apply.
    /* eslint-disable react-hooks/set-state-in-effect */
    if (!orderNumber) {
      setError('No order reference was provided.');
      setLoading(false);
      return;
    }
    // With a session_id in the URL the customer has just come back from
    // Checkout, so confirm the payment before reading the order — otherwise
    // the page would show "pending" for an order that was in fact just paid.
    // The session id is only a claim; the server checks it against Stripe.
    const confirmed = sessionId
      ? payments
          .verify(orderNumber, sessionId)
          .then((result) => {
            if (!result.paid) setPayNote(result.detail);
          })
          .catch((err) => setPayNote(err.message || 'Could not confirm your payment.'))
      : Promise.resolve();

    confirmed
      .then(() => orders.track(orderNumber))
      .then(setOrder)
      .catch((err) => setError(err.message || 'Could not load your order.'))
      .finally(() => setLoading(false));
    /* eslint-enable react-hooks/set-state-in-effect */
  }, [orderNumber, sessionId]);

  /** Resume an order that exists but was never paid — the customer cancelled
   *  at Checkout, or the tab was closed mid-redirect. */
  async function resumePayment() {
    setPaying(true);
    setPayNote(null);
    try {
      const session = await payments.checkout(orderNumber);
      if (session.url) {
        window.location.href = session.url;
        return;
      }
      const result = await payments.verify(orderNumber, session.session_id);
      setPayNote(result.detail);
      setOrder(await orders.track(orderNumber));
    } catch (err) {
      setPayNote(err.message || 'Could not start checkout.');
    } finally {
      setPaying(false);
    }
  }

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
  const isPaid = order.payment_status === 'paid';

  return (
    <>
      <Navbar secure />
      <div className="success-page">
        <div className="success-icon">
          <svg viewBox="0 0 24 24">
            <polyline points="20 6 9 17 4 12" />
          </svg>
        </div>
        <div className="success-eyebrow">{isPaid ? 'Order Confirmed' : 'Payment Pending'}</div>
        <h1 className="success-title">
          {isPaid ? (
            <>
              Your garment is
              <br />
              <em>on its way</em>
            </>
          ) : (
            <>
              Your order is
              <br />
              <em>saved</em>
            </>
          )}
        </h1>
        <p className="success-sub">
          {/* The order is real and recorded either way; only the payment state
              differs, so the copy must not claim work has started when it
              hasn't been paid for. */}
          {isPaid
            ? `Thank you. We've recorded your ${order.cloth_type_name.toLowerCase()} in ${order.material_name}${order.color_name ? ` (${order.color_name})` : ''} and our team will begin work shortly.`
            : `We've saved your ${order.cloth_type_name.toLowerCase()} in ${order.material_name}${order.color_name ? ` (${order.color_name})` : ''}. Complete the payment below and we'll begin work.`}
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
        {/* Confirms the receipt went out. The address itself is deliberately
            not echoed: the order number is the only credential needed to view
            this page, so printing the customer's email here would leak it to
            anyone holding a printed order slip. */}
        {isPaid && (
          <p className="ai-note" style={{ textAlign: 'center' }}>
            Your confirmation and receipt — including the price breakdown and design preview —
            have been emailed to the address you gave at checkout.
          </p>
        )}

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
            <span className={`summary-val ${isPaid ? '' : 'unpaid'}`}>{order.payment_status}</span>
          </div>
        </div>

        {payNote && <p className="pay-note">{payNote}</p>}

        <div className="success-actions">
          {!isPaid && (
            <button
              type="button"
              className="btn-primary"
              disabled={paying}
              onClick={resumePayment}
            >
              {paying ? 'Opening checkout…' : `Pay ${order.currency} ${Number(order.price_total).toLocaleString()}`}
            </button>
          )}
          <Link to={`/track/${order.order_number}`} className={isPaid ? 'btn-primary' : 'btn-secondary'}>
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
