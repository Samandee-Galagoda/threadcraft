import { useCallback, useEffect, useState } from 'react';
import { admin } from '../../api';

const EMPTY_CLOTH = {
  slug: '',
  name: '',
  base_price: '',
  base_stitching_cost: '0',
  base_fabric_metres: '',
  reference_body_cm: '90',
  ai_prompt_noun: '',
  production_days: 7,
};

const EMPTY_FIELD = {
  field_key: '',
  label: '',
  letter: '',
  min_value: '',
  max_value: '',
  affects_fabric: false,
  instructions: '',
};

/**
 * This screen is the proof of the proposal's "add a garment category without
 * modifying the code" requirement. Adding a cloth type here makes it appear in
 * the customer wizard immediately — no deploy, no code change.
 */
export default function AdminCatalogue() {
  const [clothTypes, setClothTypes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState(null);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState(EMPTY_CLOTH);
  const [expanded, setExpanded] = useState(null);
  const [fieldForm, setFieldForm] = useState(EMPTY_FIELD);

  const load = useCallback(async () => {
    try {
      setClothTypes(await admin.clothTypes());
    } catch (err) {
      setError(err.message || 'Could not load the catalogue.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
  }, [load]);

  async function createClothType(event) {
    event.preventDefault();
    setError(null);
    try {
      const created = await admin.createClothType({
        ...form,
        production_days: Number(form.production_days),
      });
      setNotice(`"${created.name}" created — it is now live in the customer wizard.`);
      setForm(EMPTY_CLOTH);
      setCreating(false);
      setExpanded(created.id);
      await load();
    } catch (err) {
      setError(err.message || 'Could not create the cloth type.');
    }
  }

  async function addField(clothTypeId, event) {
    event.preventDefault();
    setError(null);
    try {
      await admin.addMeasurementField(clothTypeId, {
        ...fieldForm,
        letter: fieldForm.letter || null,
        instructions: fieldForm.instructions || null,
      });
      setFieldForm(EMPTY_FIELD);
      setNotice('Measurement field added.');
      await load();
    } catch (err) {
      setError(err.message || 'Could not add the measurement field.');
    }
  }

  async function removeField(fieldId) {
    try {
      await admin.deleteMeasurementField(fieldId);
      await load();
    } catch (err) {
      setError(err.message || 'Could not remove the field.');
    }
  }

  async function deactivate(clothType) {
    if (!window.confirm(`Deactivate "${clothType.name}"? It will disappear from the wizard.`)) {
      return;
    }
    try {
      await admin.deactivateClothType(clothType.id);
      setNotice(`"${clothType.name}" deactivated.`);
      await load();
    } catch (err) {
      setError(err.message || 'Could not deactivate.');
    }
  }

  if (loading) return <div className="wizard-loading">Loading catalogue…</div>;

  return (
    <>
      <div className="portal-header">
        <h1>Catalogue</h1>
        <p>{clothTypes.length} garment types</p>
      </div>

      {notice && <div className="admin-alert">{notice}</div>}
      {error && <div className="wizard-error">{error}</div>}

      <div className="card">
        <div className="card-head">
          <div className="card-title">Garment types</div>
          <button type="button" className="oa-btn" onClick={() => setCreating(!creating)}>
            {creating ? 'Cancel' : '+ Add garment type'}
          </button>
        </div>

        {creating && (
          <form className="admin-form" onSubmit={createClothType}>
            <p className="form-label-hint">
              Adding a garment here makes it appear in the customer wizard immediately — no code
              change or redeploy.
            </p>
            <div className="field-row">
              <div className="field">
                <label htmlFor="ct-name">Name</label>
                <input
                  id="ct-name"
                  required
                  value={form.name}
                  placeholder="Waistcoat"
                  onChange={(e) =>
                    setForm({
                      ...form,
                      name: e.target.value,
                      // Slug is derived rather than asked for — it's a URL
                      // detail nobody running a tailoring shop should type.
                      slug: e.target.value.toLowerCase().trim().replace(/[^a-z0-9]+/g, '-'),
                      ai_prompt_noun: form.ai_prompt_noun || e.target.value.toLowerCase(),
                    })
                  }
                />
              </div>
              <div className="field">
                <label htmlFor="ct-slug">Slug</label>
                <input
                  id="ct-slug"
                  required
                  value={form.slug}
                  onChange={(e) => setForm({ ...form, slug: e.target.value })}
                />
              </div>
            </div>
            <div className="field-row">
              <div className="field">
                <label htmlFor="ct-price">Base price (LKR)</label>
                <input
                  id="ct-price"
                  type="number"
                  required
                  value={form.base_price}
                  onChange={(e) => setForm({ ...form, base_price: e.target.value })}
                />
              </div>
              <div className="field">
                <label htmlFor="ct-stitch">Base stitching (LKR)</label>
                <input
                  id="ct-stitch"
                  type="number"
                  value={form.base_stitching_cost}
                  onChange={(e) => setForm({ ...form, base_stitching_cost: e.target.value })}
                />
              </div>
            </div>
            <div className="field-row">
              <div className="field">
                <label htmlFor="ct-metres">Base fabric (metres)</label>
                <input
                  id="ct-metres"
                  type="number"
                  step="0.1"
                  required
                  value={form.base_fabric_metres}
                  onChange={(e) => setForm({ ...form, base_fabric_metres: e.target.value })}
                />
              </div>
              <div className="field">
                <label htmlFor="ct-ref">Reference body (cm)</label>
                <input
                  id="ct-ref"
                  type="number"
                  value={form.reference_body_cm}
                  onChange={(e) => setForm({ ...form, reference_body_cm: e.target.value })}
                />
              </div>
            </div>
            <div className="field">
              <label htmlFor="ct-prompt">AI prompt noun</label>
              <input
                id="ct-prompt"
                required
                value={form.ai_prompt_noun}
                placeholder="waistcoat"
                onChange={(e) => setForm({ ...form, ai_prompt_noun: e.target.value })}
              />
              <p className="form-label-hint">
                How this garment is described to the image model. Kept separate from the display
                name so the prompt vocabulary can be tuned without renaming the product.
              </p>
            </div>
            <button type="submit" className="btn-primary">
              Create garment type
            </button>
          </form>
        )}

        {clothTypes.map((clothType) => (
          <div className="catalogue-row" key={clothType.id}>
            <div className="order-item">
              <div className="order-info">
                <div className="order-name">
                  {clothType.name}
                  {!clothType.is_active && <span className="status-pill sp-out">Inactive</span>}
                </div>
                <div className="order-detail">
                  LKR {Number(clothType.base_price).toLocaleString()} ·{' '}
                  {clothType.measurement_fields.length} measurement field
                  {clothType.measurement_fields.length === 1 ? '' : 's'} ·{' '}
                  {clothType.option_groups.length} option groups
                </div>
                {clothType.measurement_fields.length === 0 && (
                  <div className="meas-warning">
                    ⚠ No measurement fields — Step 4 of the wizard will be empty for this garment.
                  </div>
                )}
              </div>
              <div className="order-actions">
                <button
                  type="button"
                  className="oa-btn"
                  onClick={() => setExpanded(expanded === clothType.id ? null : clothType.id)}
                >
                  {expanded === clothType.id ? 'Close' : 'Measurements'}
                </button>
                <button type="button" className="oa-btn" onClick={() => deactivate(clothType)}>
                  Deactivate
                </button>
              </div>
            </div>

            {expanded === clothType.id && (
              <div className="catalogue-fields">
                {clothType.measurement_fields.map((field) => (
                  <div className="field-chip" key={field.id}>
                    {field.letter && <span className="letter-badge">{field.letter}</span>}
                    <strong>{field.label}</strong>
                    <span>
                      {Number(field.min_value)}–{Number(field.max_value)} {field.unit}
                    </span>
                    {field.affects_fabric && <em>drives fabric</em>}
                    <button type="button" onClick={() => removeField(field.id)} aria-label="Remove">
                      ×
                    </button>
                  </div>
                ))}

                <form className="admin-form inline" onSubmit={(e) => addField(clothType.id, e)}>
                  <div className="field-row">
                    <div className="field">
                      <label htmlFor={`f-label-${clothType.id}`}>Label</label>
                      <input
                        id={`f-label-${clothType.id}`}
                        required
                        placeholder="Chest circumference"
                        value={fieldForm.label}
                        onChange={(e) =>
                          setFieldForm({
                            ...fieldForm,
                            label: e.target.value,
                            field_key:
                              fieldForm.field_key ||
                              e.target.value.toLowerCase().trim().replace(/[^a-z0-9]+/g, '_'),
                          })
                        }
                      />
                    </div>
                    <div className="field">
                      <label htmlFor={`f-key-${clothType.id}`}>Key</label>
                      <input
                        id={`f-key-${clothType.id}`}
                        required
                        value={fieldForm.field_key}
                        onChange={(e) =>
                          setFieldForm({ ...fieldForm, field_key: e.target.value })
                        }
                      />
                    </div>
                  </div>
                  <div className="field-row">
                    <div className="field">
                      <label htmlFor={`f-min-${clothType.id}`}>Min (cm)</label>
                      <input
                        id={`f-min-${clothType.id}`}
                        type="number"
                        required
                        value={fieldForm.min_value}
                        onChange={(e) =>
                          setFieldForm({ ...fieldForm, min_value: e.target.value })
                        }
                      />
                    </div>
                    <div className="field">
                      <label htmlFor={`f-max-${clothType.id}`}>Max (cm)</label>
                      <input
                        id={`f-max-${clothType.id}`}
                        type="number"
                        required
                        value={fieldForm.max_value}
                        onChange={(e) =>
                          setFieldForm({ ...fieldForm, max_value: e.target.value })
                        }
                      />
                    </div>
                  </div>
                  <label className="checkbox-row">
                    <input
                      type="checkbox"
                      checked={fieldForm.affects_fabric}
                      onChange={(e) =>
                        setFieldForm({ ...fieldForm, affects_fabric: e.target.checked })
                      }
                    />
                    This measurement drives the fabric estimate
                  </label>
                  <button type="submit" className="btn-outline-sm">
                    + Add measurement field
                  </button>
                </form>
              </div>
            )}
          </div>
        ))}
      </div>
    </>
  );
}
