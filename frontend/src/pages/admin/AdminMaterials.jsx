import { useCallback, useEffect, useState } from 'react';
import { AdminHeader } from './AdminLayout';
import { admin } from '../../api';
import { moneyExact } from '../../lib/adminFormat';

const EMPTY_MATERIAL = {
  slug: '',
  name: '',
  cost_per_metre: '',
  swatch_css: '',
  ai_prompt_term: '',
  care_notes: '',
};

const EMPTY_COLOUR = {
  name: '',
  hex_code: '#C4A882',
  ai_prompt_term: '',
  surcharge: '0',
};

export default function AdminMaterials() {
  const [materials, setMaterials] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState(null);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState(EMPTY_MATERIAL);
  const [expanded, setExpanded] = useState(null);
  const [colourForm, setColourForm] = useState(EMPTY_COLOUR);
  const [editing, setEditing] = useState(null);
  const [priceDraft, setPriceDraft] = useState('');

  const load = useCallback(async () => {
    try {
      setMaterials(await admin.adminMaterials());
    } catch (err) {
      setError(err.message || 'Could not load materials.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
  }, [load]);

  async function run(action, message) {
    setError(null);
    try {
      await action();
      setNotice(message);
      await load();
      return true;
    } catch (err) {
      setError(err.message || 'That did not work.');
      return false;
    }
  }

  if (loading) return <div className="admin-content wizard-loading">Loading materials…</div>;

  return (
    <>
      <AdminHeader title="Materials" subtitle={`${materials.length} fabrics`}>
        <button type="button" className="btn-sm btn-dark" onClick={() => setCreating(!creating)}>
          {creating ? 'Cancel' : '+ New material'}
        </button>
      </AdminHeader>

      <div className="admin-content">
        {notice && <div className="admin-alert">{notice}</div>}
        {error && <div className="wizard-error">{error}</div>}

        {creating && (
          <div className="admin-card" style={{ marginBottom: 20 }}>
            <div className="admin-card-title">New material</div>
            <form
              className="admin-form"
              onSubmit={async (e) => {
                e.preventDefault();
                const ok = await run(
                  () => admin.createMaterial(form),
                  `"${form.name}" added — it's live in the wizard now.`,
                );
                if (ok) {
                  setForm(EMPTY_MATERIAL);
                  setCreating(false);
                }
              }}
            >
              <div className="field-row">
                <div className="field">
                  <label htmlFor="m-name">Name</label>
                  <input
                    id="m-name"
                    required
                    value={form.name}
                    placeholder="Tweed"
                    onChange={(e) =>
                      setForm({
                        ...form,
                        name: e.target.value,
                        slug: e.target.value
                          .toLowerCase()
                          .trim()
                          .replace(/[^a-z0-9]+/g, '-'),
                        ai_prompt_term: form.ai_prompt_term || e.target.value.toLowerCase(),
                      })
                    }
                  />
                </div>
                <div className="field">
                  <label htmlFor="m-cost">Cost per metre (LKR)</label>
                  <input
                    id="m-cost"
                    type="number"
                    min="0"
                    required
                    value={form.cost_per_metre}
                    onChange={(e) => setForm({ ...form, cost_per_metre: e.target.value })}
                  />
                </div>
              </div>
              <div className="field">
                <label htmlFor="m-prompt">AI prompt term</label>
                <input
                  id="m-prompt"
                  required
                  value={form.ai_prompt_term}
                  placeholder="woven wool tweed"
                  onChange={(e) => setForm({ ...form, ai_prompt_term: e.target.value })}
                />
                <p className="form-label-hint">
                  How this fabric is described to the image model — kept separate from the display
                  name so prompt wording can be tuned without renaming the product.
                </p>
              </div>
              <button type="submit" className="btn-sm btn-dark">
                Create material
              </button>
            </form>
          </div>
        )}

        {materials.map((material) => (
          <div className="admin-card" style={{ marginBottom: 20 }} key={material.id}>
            <div className="admin-card-title">
              <span>
                {material.name}
                {!material.is_active && (
                  <span className="status-badge status-cancelled">Inactive</span>
                )}
              </span>
              <span>
                {editing === material.id ? (
                  <>
                    <input
                      type="number"
                      min="0"
                      className="inline-input"
                      value={priceDraft}
                      autoFocus
                      onChange={(e) => setPriceDraft(e.target.value)}
                    />
                    <button
                      type="button"
                      className="oa-btn"
                      onClick={async () => {
                        const ok = await run(
                          () =>
                            admin.updateMaterial(material.id, {
                              cost_per_metre: priceDraft,
                            }),
                          `${material.name} repriced. Existing orders keep the price they were placed at.`,
                        );
                        if (ok) setEditing(null);
                      }}
                    >
                      Save
                    </button>
                    <button type="button" className="oa-btn" onClick={() => setEditing(null)}>
                      Cancel
                    </button>
                  </>
                ) : (
                  <>
                    <span style={{ color: 'var(--taupe)', marginRight: 10 }}>
                      {moneyExact(material.cost_per_metre)}/m
                    </span>
                    <button
                      type="button"
                      className="oa-btn"
                      onClick={() => {
                        setEditing(material.id);
                        setPriceDraft(String(material.cost_per_metre));
                      }}
                    >
                      Reprice
                    </button>
                    <button
                      type="button"
                      className="oa-btn"
                      onClick={() => setExpanded(expanded === material.id ? null : material.id)}
                    >
                      {expanded === material.id ? 'Close' : 'Colours'}
                    </button>
                    <button
                      type="button"
                      className="oa-btn"
                      onClick={() => {
                        if (window.confirm(`Deactivate ${material.name}?`)) {
                          run(
                            () => admin.deactivateMaterial(material.id),
                            `${material.name} deactivated — hidden from customers, kept for past orders.`,
                          );
                        }
                      }}
                    >
                      Deactivate
                    </button>
                  </>
                )}
              </span>
            </div>

            <div className="tags-wrap">
              {(material.colors || []).map((colour) => (
                <span className="field-chip" key={colour.id}>
                  <span className="colour-dot" style={{ background: colour.hex_code }} />
                  <strong>{colour.name}</strong>
                  <span>{Number(colour.stock_metres).toFixed(1)}m</span>
                  {Number(colour.surcharge) > 0 && <em>+{moneyExact(colour.surcharge)}/m</em>}
                  <button
                    type="button"
                    aria-label={`Withdraw ${colour.name}`}
                    onClick={() =>
                      run(
                        () => admin.removeColour(colour.id),
                        `${colour.name} withdrawn from ${material.name}.`,
                      )
                    }
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>

            {expanded === material.id && (
              <form
                className="admin-form inline"
                onSubmit={async (e) => {
                  e.preventDefault();
                  const ok = await run(
                    () => admin.addColour(material.id, colourForm),
                    `${colourForm.name} added to ${material.name}. Set its stock in Inventory.`,
                  );
                  if (ok) setColourForm(EMPTY_COLOUR);
                }}
              >
                <div className="field-row">
                  <div className="field">
                    <label htmlFor={`c-name-${material.id}`}>Colour name</label>
                    <input
                      id={`c-name-${material.id}`}
                      required
                      value={colourForm.name}
                      placeholder="Forest green"
                      onChange={(e) =>
                        setColourForm({
                          ...colourForm,
                          name: e.target.value,
                          ai_prompt_term: colourForm.ai_prompt_term || e.target.value.toLowerCase(),
                        })
                      }
                    />
                  </div>
                  <div className="field">
                    <label htmlFor={`c-hex-${material.id}`}>Swatch</label>
                    <input
                      id={`c-hex-${material.id}`}
                      type="color"
                      value={colourForm.hex_code}
                      onChange={(e) =>
                        setColourForm({
                          ...colourForm,
                          hex_code: e.target.value,
                        })
                      }
                    />
                  </div>
                </div>
                <div className="field-row">
                  <div className="field">
                    <label htmlFor={`c-prompt-${material.id}`}>AI prompt term</label>
                    <input
                      id={`c-prompt-${material.id}`}
                      required
                      value={colourForm.ai_prompt_term}
                      onChange={(e) =>
                        setColourForm({
                          ...colourForm,
                          ai_prompt_term: e.target.value,
                        })
                      }
                    />
                  </div>
                  <div className="field">
                    <label htmlFor={`c-sur-${material.id}`}>Surcharge per metre</label>
                    <input
                      id={`c-sur-${material.id}`}
                      type="number"
                      min="0"
                      value={colourForm.surcharge}
                      onChange={(e) =>
                        setColourForm({
                          ...colourForm,
                          surcharge: e.target.value,
                        })
                      }
                    />
                  </div>
                </div>
                <button type="submit" className="btn-sm btn-light">
                  + Add colourway
                </button>
              </form>
            )}
          </div>
        ))}
      </div>
    </>
  );
}
