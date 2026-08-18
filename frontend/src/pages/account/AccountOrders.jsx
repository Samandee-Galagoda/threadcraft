import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { AdminHeader } from '../admin/AdminLayout';
import Modal from '../../components/Modal';
import { orders as ordersApi } from '../../api';
import { STAGES, STATUS_LABELS, moneyExact, shortDate, statusClass } from '../../lib/adminFormat';

export default function AccountOrders() {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState(null);
  const [cancelling, setCancelling] = useState(null);
  const [reason, setReason] = useState('');
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      setOrders(await ordersApi.mine());
    } catch (err) {
      setError(err.message || 'Could not load your orders.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
  }, [load]);

  async function confirmCancel() {
    setBusy(true);
    setError(null);
    try {
      await ordersApi.cancel(cancelling.order_number, reason ? { reason } : {});
      setNotice(
        `${cancelling.order_number} cancelled. Any fabric reserved for it is back in stock.`,
      );
      setCancelling(null);
      setReason('');
      await load();
    } catch (err) {
      setError(err.message || 'Could not cancel that order.');
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <div className="admin-content wizard-loading">Loading your orders…</div>;

  return (
    <>
      <AdminHeader
        title="My orders"
        subtitle={`${orders.length} order${orders.length === 1 ? '' : 's'}`}
      />

      <div className="admin-content">
        {notice && <div className="admin-alert">{notice}</div>}
        {error && <div className="wizard-error">{error}</div>}

        {orders.length === 0 ? (
          <div className="admin-card">
            <p className="admin-empty-row">
              You haven&apos;t ordered yet — <Link to="/design">design your first garment</Link>.
            </p>
          </div>
        ) : (
          orders.map((order) => {
            const index = STAGES.indexOf(order.status);
            // Cancellable only while `received`: once the cloth is cut it can't
            // go back on the roll, which is the same rule the server enforces.
            const cancellable = order.status === 'received';
            return (
              <div className="admin-card" style={{ marginBottom: 20 }} key={order.order_number}>
                <div className="admin-card-title">
                  <span>
                    {order.cloth_type_name} · {order.order_number}
                    <span style={{ color: 'var(--taupe)', marginLeft: 10, letterSpacing: '.06em' }}>
                      {order.material_name}
                      {order.color_name ? ` · ${order.color_name}` : ''}
                    </span>
                  </span>
                  <span className="row-actions">
                    <span className={`status-badge ${statusClass(order.status)}`}>
                      {STATUS_LABELS[order.status] ?? order.status}
                    </span>
                    <span className={`status-badge status-${order.payment_status}`}>
                      {order.payment_status}
                    </span>
                    <Link to={`/track/${order.order_number}`} className="oa-btn">
                      Track
                    </Link>
                    {cancellable && (
                      <button
                        type="button"
                        className="oa-btn"
                        onClick={() => {
                          setCancelling(order);
                          setReason('');
                        }}
                      >
                        Cancel order
                      </button>
                    )}
                  </span>
                </div>

                {order.status !== 'cancelled' && (
                  <div className="track-strip">
                    {STAGES.map((stage, position) => (
                      <div
                        className={`track-pip ${position <= index ? 'done' : ''} ${
                          position === index ? 'current' : ''
                        }`}
                        key={stage}
                      >
                        <span className="track-pip-dot" />
                        <span className="track-pip-label">{STATUS_LABELS[stage]}</span>
                      </div>
                    ))}
                  </div>
                )}

                <div className="order-meta" style={{ marginTop: 12 }}>
                  <span className="order-date">Ordered {shortDate(order.created_at)}</span>
                  <span style={{ marginLeft: 'auto', fontFamily: 'var(--serif)', fontSize: 16 }}>
                    {moneyExact(order.price_total)}
                  </span>
                </div>
              </div>
            );
          })
        )}

        {cancelling && (
          <Modal
            title={`Cancel ${cancelling.order_number}?`}
            subtitle="This cannot be undone"
            onClose={() => setCancelling(null)}
          >
            <p className="form-label-hint" style={{ marginBottom: 14 }}>
              Your {cancelling.cloth_type_name.toLowerCase()} hasn&apos;t been cut yet, so we can
              cancel it and return the fabric to stock. Once cutting starts this option disappears.
            </p>
            <div className="field">
              <label htmlFor="cancel-reason">Reason (optional)</label>
              <input
                id="cancel-reason"
                value={reason}
                placeholder="Ordered the wrong size"
                onChange={(e) => setReason(e.target.value)}
              />
            </div>
            <div className="row-actions" style={{ justifyContent: 'flex-start' }}>
              <button
                type="button"
                className="btn-sm btn-dark"
                disabled={busy}
                onClick={confirmCancel}
              >
                {busy ? 'Cancelling…' : 'Yes, cancel this order'}
              </button>
              <button
                type="button"
                className="btn-sm btn-light"
                onClick={() => setCancelling(null)}
              >
                Keep it
              </button>
            </div>
          </Modal>
        )}
      </div>
    </>
  );
}
