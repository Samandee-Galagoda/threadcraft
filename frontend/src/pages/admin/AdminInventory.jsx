import { useCallback, useEffect, useState } from 'react';
import { admin } from '../../api';

export default function AdminInventory() {
  const [materials, setMaterials] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [editing, setEditing] = useState(null);
  const [draft, setDraft] = useState('');
  const [notice, setNotice] = useState(null);

  const load = useCallback(async () => {
    try {
      setMaterials(await admin.materials());
    } catch (err) {
      setError(err.message || 'Could not load inventory.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
  }, [load]);

  async function save(material) {
    const value = Number(draft);
    if (Number.isNaN(value) || value < 0) {
      setError('Stock must be a number of metres, zero or more.');
      return;
    }
    setError(null);
    try {
      await admin.updateStock(material.id, value);
      setNotice(`${material.name} stock set to ${value} m.`);
      setEditing(null);
      await load();
    } catch (err) {
      setError(err.message || 'Could not update stock.');
    }
  }

  if (loading) return <div className="wizard-loading">Loading inventory…</div>;

  const lowCount = materials.filter((m) => m.is_low_stock).length;

  return (
    <>
      <div className="portal-header">
        <h1>Inventory</h1>
        <p>
          {materials.length} materials · {lowCount} at or below threshold
        </p>
      </div>

      {notice && <div className="admin-alert">{notice}</div>}
      {error && <div className="wizard-error">{error}</div>}

      <div className="card">
        <table className="admin-table">
          <thead>
            <tr>
              <th>Material</th>
              <th>Cost / m</th>
              <th>In stock</th>
              <th>Threshold</th>
              <th>Status</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {materials.map((material) => {
              const stock = Number(material.stock_metres);
              const threshold = Number(material.low_stock_threshold);
              // Bar is relative to twice the threshold, so "at threshold" sits
              // visually at the halfway point rather than looking full or empty.
              const pct = Math.max(0, Math.min(100, (stock / (threshold * 2 || 1)) * 100));
              return (
                <tr key={material.id}>
                  <td>
                    <div className="table-material">
                      <span
                        className="mat-dot"
                        style={{ background: material.swatch_css || '#E8D5C0' }}
                      />
                      {material.name}
                    </div>
                  </td>
                  <td>LKR {Number(material.cost_per_metre).toLocaleString()}</td>
                  <td>
                    {editing === material.id ? (
                      <input
                        type="number"
                        step="0.1"
                        min="0"
                        className="inline-input"
                        value={draft}
                        autoFocus
                        onChange={(e) => setDraft(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') save(material);
                          if (e.key === 'Escape') setEditing(null);
                        }}
                      />
                    ) : (
                      <>
                        <div className="stock-bar">
                          <span
                            style={{ width: `${pct}%` }}
                            className={
                              stock <= 0 ? 'out' : material.is_low_stock ? 'low' : 'ok'
                            }
                          />
                        </div>
                        {stock.toFixed(1)} m
                      </>
                    )}
                  </td>
                  <td>{threshold.toFixed(1)} m</td>
                  <td>
                    {stock <= 0 ? (
                      <span className="status-pill sp-out">Out of stock</span>
                    ) : material.is_low_stock ? (
                      <span className="status-pill sp-low">Low</span>
                    ) : (
                      <span className="status-pill sp-dispatched">OK</span>
                    )}
                  </td>
                  <td>
                    {editing === material.id ? (
                      <>
                        <button type="button" className="oa-btn" onClick={() => save(material)}>
                          Save
                        </button>
                        <button type="button" className="oa-btn" onClick={() => setEditing(null)}>
                          Cancel
                        </button>
                      </>
                    ) : (
                      <button
                        type="button"
                        className="oa-btn"
                        onClick={() => {
                          setEditing(material.id);
                          setDraft(String(stock));
                        }}
                      >
                        Edit stock
                      </button>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <p className="admin-footnote">
        Stock decrements automatically when an order is placed. A material at zero is disabled in
        the customer wizard.
      </p>
    </>
  );
}
