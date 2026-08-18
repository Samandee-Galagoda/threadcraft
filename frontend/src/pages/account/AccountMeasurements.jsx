import { useCallback, useEffect, useMemo, useState } from 'react';
import { AdminHeader } from '../admin/AdminLayout';
import { catalog, measurements as measurementsApi } from '../../api';

/** Every measurement field the catalogue defines, grouped by garment.
 *
 *  Driven entirely by the cloth-type configuration rather than a hardcoded
 *  list: a measurement an admin adds through the catalogue screen appears here
 *  the moment it exists, which is also why the values are stored as a map.
 */
export default function AccountMeasurements() {
  const [clothTypes, setClothTypes] = useState([]);
  const [values, setValues] = useState({});
  const [draft, setDraft] = useState({});
  const [updatedAt, setUpdatedAt] = useState(null);
  const [editing, setEditing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState(null);

  const load = useCallback(async () => {
    try {
      const [types, saved] = await Promise.all([catalog.clothTypes(), measurementsApi.load()]);
      setClothTypes(types);
      setValues(saved.values || {});
      setDraft(saved.values || {});
      setUpdatedAt(saved.updated_at);
    } catch (err) {
      setError(err.message || 'Could not load your measurements.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
  }, [load]);

  // The same key appears on several garments (chest is on shirts and kurtas),
  // so it is stored once and shown wherever it applies.
  const fieldsByKey = useMemo(() => {
    const map = {};
    for (const type of clothTypes) {
      for (const field of type.measurement_fields) {
        if (!map[field.field_key]) map[field.field_key] = { ...field, garments: [] };
        map[field.field_key].garments.push(type.name);
      }
    }
    return map;
  }, [clothTypes]);

  const totalFields = Object.keys(fieldsByKey).length;
  const filled = Object.keys(values).length;

  async function save() {
    setSaving(true);
    setError(null);
    try {
      const cleaned = {};
      for (const [key, value] of Object.entries(draft)) {
        if (value !== '' && value != null && Number(value) > 0) cleaned[key] = Number(value);
      }
      const saved = await measurementsApi.save(cleaned);
      setValues(saved.values || {});
      setDraft(saved.values || {});
      setUpdatedAt(saved.updated_at);
      setEditing(false);
      setNotice('Measurements saved — the design wizard will pre-fill them from now on.');
    } catch (err) {
      setError(err.message || 'Could not save your measurements.');
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <div className="admin-content wizard-loading">Loading measurements…</div>;

  return (
    <>
      <AdminHeader
        title="My measurements"
        subtitle={
          updatedAt
            ? `${filled} of ${totalFields} saved · last updated ${new Date(updatedAt).toLocaleDateString('en-GB')}`
            : `${filled} of ${totalFields} saved`
        }
      >
        {editing ? (
          <>
            <button
              type="button"
              className="btn-sm btn-light"
              onClick={() => {
                setDraft(values);
                setEditing(false);
              }}
            >
              Cancel
            </button>
            <button type="button" className="btn-sm btn-dark" disabled={saving} onClick={save}>
              {saving ? 'Saving…' : 'Save measurements'}
            </button>
          </>
        ) : (
          <button type="button" className="btn-sm btn-dark" onClick={() => setEditing(true)}>
            Edit measurements
          </button>
        )}
      </AdminHeader>

      <div className="admin-content">
        {notice && <div className="admin-alert">{notice}</div>}
        {error && <div className="wizard-error">{error}</div>}

        <div className="admin-alert">
          Saved once, reused everywhere: the design wizard pre-fills whichever of these a garment
          needs, so you only measure yourself once. All values in centimetres.
        </div>

        {clothTypes.map((type) => (
          <div className="admin-card" style={{ marginBottom: 20 }} key={type.id}>
            <div className="admin-card-title">
              <span>{type.name}</span>
              <span style={{ color: 'var(--taupe)', letterSpacing: '.06em' }}>
                {type.measurement_fields.filter((f) => values[f.field_key]).length} /{' '}
                {type.measurement_fields.length} saved
              </span>
            </div>

            {type.measurement_fields.length === 0 ? (
              <p className="admin-empty-row">No measurements configured for this garment.</p>
            ) : (
              <div className="meas-grid">
                {type.measurement_fields.map((field) => {
                  const value = editing ? (draft[field.field_key] ?? '') : values[field.field_key];
                  return (
                    <div className="meas-item" key={field.field_key}>
                      <span className="meas-label">
                        {field.letter && <span className="letter-badge">{field.letter}</span>}
                        {field.label}
                      </span>
                      {editing ? (
                        <input
                          type="number"
                          className="inline-input"
                          min={field.min_value}
                          max={field.max_value}
                          step="0.5"
                          value={value}
                          placeholder={`${Number(field.min_value)}–${Number(field.max_value)}`}
                          onChange={(e) =>
                            setDraft({ ...draft, [field.field_key]: e.target.value })
                          }
                        />
                      ) : (
                        <span className="meas-val">
                          {value ? (
                            <>
                              {value}
                              <span className="meas-unit">{field.unit}</span>
                            </>
                          ) : (
                            <span style={{ color: 'var(--taupe)', fontSize: 12 }}>not set</span>
                          )}
                        </span>
                      )}
                      {editing && field.instructions && (
                        <p className="meas-help">{field.instructions}</p>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        ))}
      </div>
    </>
  );
}
