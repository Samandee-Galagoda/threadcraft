import { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { AdminHeader } from '../admin/AdminLayout';
import { designs as designsApi, mediaUrl, orders as ordersApi } from '../../api';
import { useWizard } from '../../context/WizardContext';
import { money, shortDate } from '../../lib/adminFormat';

export default function AccountDesigns() {
  const navigate = useNavigate();
  const { dispatch } = useWizard();
  const [designs, setDesigns] = useState([]);
  const [pastOrders, setPastOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState(null);

  const load = useCallback(async () => {
    try {
      const [saved, orders] = await Promise.all([designsApi.list(), ordersApi.mine()]);
      setDesigns(saved);
      setPastOrders(orders);
    } catch (err) {
      setError(err.message || 'Could not load your designs.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
  }, [load]);

  /** Load a previous design back into the wizard.
   *
   *  Only the selections are restored, never the price: the catalogue may have
   *  been repriced since, and the wizard re-quotes from the live catalogue on
   *  the next step. Showing the old total would promise a price we no longer
   *  offer.
   */
  function reorder(payload, label) {
    dispatch({ type: 'RESET' });
    if (payload.cloth_type_id) {
      dispatch({
        type: 'SELECT_CLOTH_TYPE',
        id: payload.cloth_type_id,
        slug: payload.cloth_type_slug,
      });
    }
    if (payload.material_id) {
      dispatch({
        type: 'SELECT_MATERIAL',
        id: payload.material_id,
        colorId: payload.material_color_id ?? null,
      });
    }
    if (payload.material_color_id) {
      dispatch({ type: 'SELECT_COLOR', id: payload.material_color_id });
    }
    for (const optionId of payload.design_option_ids || []) {
      dispatch({ type: 'TOGGLE_OPTION', id: optionId });
    }
    if (payload.measurements && Object.keys(payload.measurements).length) {
      dispatch({ type: 'SET_MEASUREMENTS', values: payload.measurements });
    }
    setNotice(`"${label}" loaded into the design wizard.`);
    navigate('/design');
  }

  /** Past orders are re-resolved by the server against the live catalogue —
   *  a garment or fabric may have been withdrawn since. */
  async function reorderPastOrder(order) {
    setError(null);
    try {
      const plan = await ordersApi.reorderPlan(order.order_number);
      if (!plan.cloth_type_id || !plan.material_id) {
        setError(
          `We can no longer make that exact order — ${plan.unavailable.join(', ')} ${
            plan.unavailable.length === 1 ? 'is' : 'are'
          } discontinued. Start a new design instead.`,
        );
        return;
      }
      reorder(plan, order.cloth_type_name);
      if (plan.unavailable.length) {
        setNotice(
          `Loaded, but ${plan.unavailable.join(', ')} ${
            plan.unavailable.length === 1 ? 'is' : 'are'
          } no longer available — pick a replacement in the wizard.`,
        );
      }
    } catch (err) {
      setError(err.message || 'Could not reorder that.');
    }
  }

  async function remove(design) {
    if (!window.confirm(`Delete "${design.name}"?`)) return;
    try {
      await designsApi.remove(design.id);
      setNotice(`"${design.name}" deleted.`);
      await load();
    } catch (err) {
      setError(err.message || 'Could not delete that design.');
    }
  }

  if (loading) return <div className="admin-content wizard-loading">Loading your designs…</div>;

  return (
    <>
      <AdminHeader
        title="Saved designs"
        subtitle={`${designs.length} saved · ${pastOrders.length} past order${
          pastOrders.length === 1 ? '' : 's'
        } you can reorder`}
      >
        <button type="button" className="btn-sm btn-dark" onClick={() => navigate('/design')}>
          + Start a new design
        </button>
      </AdminHeader>

      <div className="admin-content">
        {notice && <div className="admin-alert">{notice}</div>}
        {error && <div className="wizard-error">{error}</div>}

        <div className="admin-card" style={{ marginBottom: 20 }}>
          <div className="admin-card-title">Designs you saved</div>
          {designs.length === 0 ? (
            <p className="admin-empty-row">
              Nothing saved yet. Save a design from the wizard and it appears here.
            </p>
          ) : (
            <table className="orders-table">
              <thead>
                <tr>
                  <th>Design</th>
                  <th>Estimated</th>
                  <th>Saved</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {designs.map((design) => (
                  <tr key={design.id}>
                    <td>{design.name}</td>
                    <td>{design.estimated_total ? money(design.estimated_total) : '—'}</td>
                    <td>{shortDate(design.created_at)}</td>
                    <td>
                      <span className="row-actions">
                        <button
                          type="button"
                          className="oa-btn"
                          onClick={() => reorder(design.payload || {}, design.name)}
                        >
                          Open in wizard
                        </button>
                        <button type="button" className="oa-btn" onClick={() => remove(design)}>
                          Delete
                        </button>
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <div className="admin-card">
          <div className="admin-card-title">Order it again</div>
          {pastOrders.length === 0 ? (
            <p className="admin-empty-row">
              No past orders yet — <Link to="/design">design something</Link>.
            </p>
          ) : (
            pastOrders.map((order) => (
              <div className="order-item" key={order.order_number}>
                {order.mockup_url && (
                  <img
                    src={mediaUrl(order.mockup_url)}
                    alt=""
                    style={{
                      width: 46,
                      height: 46,
                      objectFit: 'cover',
                      border: '.5px solid var(--sand)',
                    }}
                  />
                )}
                <div className="order-info">
                  <div className="order-name">{order.cloth_type_name}</div>
                  <div className="order-detail">
                    {order.material_name}
                    {order.color_name ? ` · ${order.color_name}` : ''} ·{' '}
                    {(order.design_options_snapshot || []).map((o) => o.label).join(', ') ||
                      'no options'}
                  </div>
                  <div className="order-meta">
                    <span className="order-date">
                      {order.order_number} · {shortDate(order.created_at)}
                    </span>
                  </div>
                </div>
                <div className="order-price">{money(order.price_total)}</div>
                <div className="order-actions">
                  <button type="button" className="oa-btn" onClick={() => reorderPastOrder(order)}>
                    Order again
                  </button>
                </div>
              </div>
            ))
          )}
          <p className="form-label-hint" style={{ marginTop: 12 }}>
            Reordering copies the garment, fabric and measurements into the wizard. The price is
            re-quoted from the current catalogue rather than carried over.
          </p>
        </div>
      </div>
    </>
  );
}
