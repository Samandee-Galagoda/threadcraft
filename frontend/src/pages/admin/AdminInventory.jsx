import { useCallback, useEffect, useState } from 'react';
import { AdminHeader } from './AdminLayout';
import { admin } from '../../api';
import { moneyExact } from '../../lib/adminFormat';

/** Stock is held per colourway, so this screen edits colours rather than
 *  materials: a tailor runs out of burgundy silk, not of silk. */
export default function AdminInventory() {
  const [materials, setMaterials] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState(null);
  const [editing, setEditing] = useState(null);
  const [draft, setDraft] = useState('');

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

  async function save(colour) {
    const value = Number(draft);
    if (Number.isNaN(value) || value < 0) {
      setError('Stock must be a number of metres, zero or more.');
      return;
    }
    setError(null);
    try {
      await admin.updateColourStock(colour.id, value);
      setNotice(`${colour.name} stock set to ${value} m.`);
      setEditing(null);
      await load();
    } catch (err) {
      setError(err.message || 'Could not update stock.');
    }
  }

  if (loading) return <div className="admin-content wizard-loading">Loading inventory…</div>;

  const lowColours = materials.flatMap((m) => (m.colors || []).filter((c) => c.is_low_stock));

  return (
    <>
      <AdminHeader
        title="Inventory"
        subtitle={`${materials.length} materials · ${lowColours.length} colourway${
          lowColours.length === 1 ? '' : 's'
        } at or below threshold`}
      />

      <div className="admin-content">
        {notice && <div className="admin-alert">{notice}</div>}
        {error && <div className="wizard-error">{error}</div>}

        {lowColours.length > 0 && (
          <div className="admin-alert warn">
            Running low: {lowColours.map((c) => c.name).join(', ')}. Stock decrements automatically
            as orders are placed, and a colourway at zero is refused at checkout.
          </div>
        )}

        {materials.map((material) => {
          const total = (material.colors || []).reduce((sum, c) => sum + Number(c.stock_metres), 0);
          return (
            <div className="admin-card" style={{ marginBottom: 20 }} key={material.id}>
              <div className="admin-card-title">
                <span>
                  {material.name}
                  {!material.is_active && ' · inactive'}
                </span>
                <span style={{ color: 'var(--taupe)', letterSpacing: '.06em' }}>
                  {total.toFixed(1)} m total · {moneyExact(material.cost_per_metre)}/m
                </span>
              </div>

              {(material.colors || []).length === 0 ? (
                <p className="admin-empty-row">
                  No colourways — this material&apos;s stock is tracked as a single pool.
                </p>
              ) : (
                material.colors.map((colour) => {
                  const stock = Number(colour.stock_metres);
                  const threshold = Number(colour.low_stock_threshold);
                  const level =
                    stock <= threshold / 2 ? 'critical' : stock <= threshold ? 'low' : '';
                  // Relative to 4x the threshold so "at threshold" sits a
                  // quarter of the way along rather than looking nearly full.
                  const pct = Math.max(2, Math.min(100, (stock / (threshold * 4 || 1)) * 100));
                  return (
                    <div className="inv-item" key={colour.id}>
                      <div className="inv-row">
                        <span className="inv-name">
                          <span className="colour-dot" style={{ background: colour.hex_code }} />
                          {colour.name}
                          {Number(colour.surcharge) > 0 && (
                            <em style={{ fontSize: 10, color: 'var(--taupe)' }}>
                              +{moneyExact(colour.surcharge)}/m
                            </em>
                          )}
                        </span>
                        {editing === colour.id ? (
                          <span style={{ display: 'flex', gap: 6 }}>
                            <input
                              type="number"
                              step="0.1"
                              min="0"
                              className="inline-input"
                              value={draft}
                              autoFocus
                              onChange={(e) => setDraft(e.target.value)}
                              onKeyDown={(e) => {
                                if (e.key === 'Enter') save(colour);
                                if (e.key === 'Escape') setEditing(null);
                              }}
                            />
                            <button type="button" className="oa-btn" onClick={() => save(colour)}>
                              Save
                            </button>
                            <button
                              type="button"
                              className="oa-btn"
                              onClick={() => setEditing(null)}
                            >
                              Cancel
                            </button>
                          </span>
                        ) : (
                          <span
                            style={{
                              display: 'flex',
                              alignItems: 'center',
                              gap: 10,
                            }}
                          >
                            <span className={`inv-stock ${level}`}>
                              {stock.toFixed(1)} m left{level ? ' ⚠' : ''}
                            </span>
                            <button
                              type="button"
                              className="oa-btn"
                              onClick={() => {
                                setEditing(colour.id);
                                setDraft(String(stock));
                              }}
                            >
                              Edit
                            </button>
                          </span>
                        )}
                      </div>
                      <div className="inv-bar">
                        <div className={`inv-fill ${level}`} style={{ width: `${pct}%` }} />
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          );
        })}
      </div>
    </>
  );
}
