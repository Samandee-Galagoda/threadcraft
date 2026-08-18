import { useCallback, useEffect, useState } from 'react';
import { AdminHeader } from './AdminLayout';
import { admin, mediaUrl } from '../../api';

const STAGES = ['received', 'fabric_cut', 'stitching', 'qc', 'dispatched'];
const LABELS = {
  received: 'Received',
  fabric_cut: 'Fabric cut',
  stitching: 'Stitching',
  qc: 'QC check',
  dispatched: 'Dispatched',
  cancelled: 'Cancelled',
};

/** Mirrors the server's forward-only workflow so the UI only offers legal moves.
 *  The server still validates — this just avoids showing buttons that 409. */
function nextStatuses(current) {
  if (current === 'dispatched' || current === 'cancelled') return [];
  const index = STAGES.indexOf(current);
  const options = [];
  if (index >= 0 && index + 1 < STAGES.length) options.push(STAGES[index + 1]);
  options.push('cancelled');
  return options;
}

const money = (v) => `LKR ${Number(v).toLocaleString(undefined, { minimumFractionDigits: 2 })}`;

export default function AdminOrders() {
  const [orders, setOrders] = useState([]);
  const [filter, setFilter] = useState('');
  const [selected, setSelected] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      setOrders(await admin.orders(filter || undefined));
    } catch (err) {
      setError(err.message || 'Could not load orders.');
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
  }, [load]);

  async function advance(order, status) {
    setBusy(true);
    setNotice(null);
    try {
      const updated = await admin.updateOrderStatus(order.id, status);
      setNotice(`${order.order_number} → ${LABELS[status]}. Customer notified by email.`);
      setSelected(null);
      await load();
      return updated;
    } catch (err) {
      setError(err.message || 'Could not update the order.');
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <div className="wizard-loading">Loading orders…</div>;

  return (
    <>
      <AdminHeader
        title="Orders"
        subtitle={`${orders.length} order${orders.length === 1 ? '' : 's'}`}
      />
      <div className="admin-content">
        {notice && <div className="admin-alert">{notice}</div>}
        {error && <div className="wizard-error">{error}</div>}

        <div className="filter-chips">
          <button
            type="button"
            className={filter === '' ? 'active' : ''}
            onClick={() => setFilter('')}
          >
            All
          </button>
          {[...STAGES, 'cancelled'].map((stage) => (
            <button
              type="button"
              key={stage}
              className={filter === stage ? 'active' : ''}
              onClick={() => setFilter(stage)}
            >
              {LABELS[stage]}
            </button>
          ))}
        </div>

        <div className="card">
          {orders.length === 0 ? (
            <p className="admin-empty">No orders match this filter.</p>
          ) : (
            orders.map((order) => (
              <div className="order-item" key={order.id}>
                <div className="order-info">
                  <div className="order-name">{order.cloth_type_name}</div>
                  <div className="order-detail">
                    {order.order_number} · {order.material_name}
                    {order.color_name ? ` · ${order.color_name}` : ''}
                  </div>
                  <div className="order-meta">
                    <span className="order-date">
                      {new Date(order.created_at).toLocaleDateString('en-GB', {
                        day: 'numeric',
                        month: 'short',
                        year: 'numeric',
                      })}
                    </span>
                    <span className={`status-pill sp-${order.status.replace('_', '-')}`}>
                      {LABELS[order.status] ?? order.status}
                    </span>
                    <span className={`status-pill sp-${order.payment_status}`}>
                      {order.payment_status}
                    </span>
                  </div>
                </div>
                <div className="order-price">{money(order.price_total)}</div>
                <div className="order-actions">
                  <button type="button" className="oa-btn" onClick={() => setSelected(order)}>
                    Details
                  </button>
                </div>
              </div>
            ))
          )}
        </div>

        {selected && (
          <OrderDrawer
            order={selected}
            busy={busy}
            onClose={() => setSelected(null)}
            onAdvance={advance}
          />
        )}
      </div>
    </>
  );
}

function OrderDrawer({ order, busy, onClose, onAdvance }) {
  const options = order.design_options_snapshot || [];
  const measurements = order.measurements_snapshot || {};
  const moves = nextStatuses(order.status);

  return (
    <div className="drawer-backdrop" role="dialog" aria-modal="true" onClick={onClose}>
      <div className="drawer" onClick={(e) => e.stopPropagation()}>
        <div className="drawer-head">
          <div>
            <div className="order-num">{order.order_number}</div>
            <p className="track-sub">
              {order.cloth_type_name} · {order.material_name}
            </p>
          </div>
          <button type="button" className="drawer-close" onClick={onClose} aria-label="Close">
            ×
          </button>
        </div>

        {order.mockup_url && (
          <div className="drawer-mockup">
            <img src={mediaUrl(order.mockup_url)} alt="Customer's design preview" />
            <span>AI preview at time of order</span>
          </div>
        )}

        <div className="drawer-section">
          <h4>Design</h4>
          {options.length === 0 ? (
            <p className="admin-empty">No design options selected.</p>
          ) : (
            <div className="tags-wrap">
              {options.map((o) => (
                <span className="tag-btn active" key={o.code}>
                  {o.label}
                </span>
              ))}
            </div>
          )}
        </div>

        <div className="drawer-section">
          <h4>Measurements</h4>
          {Object.keys(measurements).length === 0 ? (
            <p className="admin-empty">None supplied.</p>
          ) : (
            <div className="meas-grid">
              {Object.entries(measurements).map(([key, value]) => (
                <div className="meas-item" key={key}>
                  <span className="meas-label">{key.replace('_', ' ')}</span>
                  <span className="meas-val">
                    {value}
                    <span className="meas-unit">cm</span>
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="drawer-section">
          <h4>Price</h4>
          {(order.price_breakdown || []).map((line, i) => (
            <div className="pr" key={`${line.label}-${i}`}>
              <span>{line.label}</span>
              <span>{money(line.amount)}</span>
            </div>
          ))}
          <div className="pr-total">
            <span className="k">Total</span>
            <span className="v">{money(order.price_total)}</span>
          </div>
        </div>

        <div className="drawer-section">
          <h4>Advance production</h4>
          {moves.length === 0 ? (
            <p className="admin-empty">
              This order is {LABELS[order.status]?.toLowerCase()} — no further changes.
            </p>
          ) : (
            <>
              <p className="form-label-hint">
                Only the next legal stage is offered; the server rejects anything else.
              </p>
              <div className="drawer-actions">
                {moves.map((status) => (
                  <button
                    type="button"
                    key={status}
                    disabled={busy}
                    className={status === 'cancelled' ? 'btn-secondary' : 'btn-primary'}
                    onClick={() => onAdvance(order, status)}
                  >
                    {status === 'cancelled' ? 'Cancel order' : `Mark ${LABELS[status]}`}
                  </button>
                ))}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
