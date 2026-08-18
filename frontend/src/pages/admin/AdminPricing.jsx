import { useCallback, useEffect, useState } from 'react';
import { AdminHeader } from './AdminLayout';
import { admin } from '../../api';
import { moneyExact } from '../../lib/adminFormat';

const EMPTY_OPTION = {
  code: '',
  label: '',
  ai_prompt_term: '',
  stitching_premium: '0',
  fabric_multiplier: '1.000',
};

/** Pricing config: the global rules, plus the per-option premiums.
 *
 *  A design option carries three effects at once — a stitching line item, a
 *  fabric multiplier, and the wording handed to the image model — so they are
 *  edited together here rather than split across screens.
 */
export default function AdminPricing() {
  const [groups, setGroups] = useState([]);
  const [settings, setSettings] = useState([]);
  const [drafts, setDrafts] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState(null);
  const [adding, setAdding] = useState(null);
  const [optionForm, setOptionForm] = useState(EMPTY_OPTION);
  const [editing, setEditing] = useState(null);
  const [optionDraft, setOptionDraft] = useState({});

  const load = useCallback(async () => {
    try {
      const [groupList, settingList] = await Promise.all([admin.optionGroups(), admin.settings()]);
      setGroups(groupList);
      setSettings(settingList);
      setDrafts(Object.fromEntries(settingList.map((s) => [s.key, s.value])));
    } catch (err) {
      setError(err.message || 'Could not load pricing configuration.');
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

  if (loading) return <div className="admin-content wizard-loading">Loading pricing…</div>;

  return (
    <>
      <AdminHeader
        title="Pricing config"
        subtitle="Delivery rules, fit scaling, and the premium on every design option"
      />

      <div className="admin-content">
        {notice && <div className="admin-alert">{notice}</div>}
        {error && <div className="wizard-error">{error}</div>}

        <div className="admin-card" style={{ marginBottom: 20 }}>
          <div className="admin-card-title">Global rules</div>
          <p className="form-label-hint" style={{ marginBottom: 14 }}>
            These feed the pricing engine directly — a change here moves every quote from the next
            request onward. Orders already placed keep the price they were quoted.
          </p>
          {settings.map((setting) => {
            const dirty = String(drafts[setting.key]) !== String(setting.value);
            return (
              <div className="setting-row" key={setting.key}>
                <div className="setting-meta">
                  <label htmlFor={`s-${setting.key}`}>{setting.label || setting.key}</label>
                  {setting.description && <p className="form-label-hint">{setting.description}</p>}
                </div>
                <div className="setting-control">
                  <input
                    id={`s-${setting.key}`}
                    className="inline-input"
                    value={drafts[setting.key] ?? ''}
                    inputMode={setting.value_type === 'number' ? 'decimal' : 'text'}
                    onChange={(e) => setDrafts({ ...drafts, [setting.key]: e.target.value })}
                  />
                  <button
                    type="button"
                    className="oa-btn"
                    disabled={!dirty}
                    onClick={() =>
                      run(
                        () => admin.updateSetting(setting.key, String(drafts[setting.key])),
                        `${setting.label || setting.key} saved.`,
                      )
                    }
                  >
                    Save
                  </button>
                </div>
              </div>
            );
          })}
        </div>

        {groups.map((group) => (
          <div className="admin-card" style={{ marginBottom: 20 }} key={group.id}>
            <div className="admin-card-title">
              <span>
                {group.label}
                <span
                  style={{
                    color: 'var(--taupe)',
                    marginLeft: 8,
                    letterSpacing: '.06em',
                  }}
                >
                  {group.cloth_type_id ? 'garment-specific' : 'all garments'}
                </span>
              </span>
              <button
                type="button"
                className="linkish"
                onClick={() => {
                  setAdding(adding === group.id ? null : group.id);
                  setOptionForm(EMPTY_OPTION);
                }}
              >
                {adding === group.id ? 'Cancel' : '+ Add option'}
              </button>
            </div>

            <table className="orders-table">
              <thead>
                <tr>
                  <th>Option</th>
                  <th>Stitching premium</th>
                  <th>Fabric multiplier</th>
                  <th>Prompt term</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {group.options.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="admin-empty-row">
                      No options in this group yet.
                    </td>
                  </tr>
                ) : (
                  group.options.map((option) => {
                    const isEditing = editing === option.id;
                    return (
                      <tr key={option.id} style={{ opacity: option.is_active ? 1 : 0.45 }}>
                        <td>
                          {option.label}
                          {!option.is_active && ' · inactive'}
                        </td>
                        <td>
                          {isEditing ? (
                            <input
                              type="number"
                              min="0"
                              className="inline-input"
                              value={optionDraft.stitching_premium}
                              onChange={(e) =>
                                setOptionDraft({
                                  ...optionDraft,
                                  stitching_premium: e.target.value,
                                })
                              }
                            />
                          ) : (
                            moneyExact(option.stitching_premium)
                          )}
                        </td>
                        <td>
                          {isEditing ? (
                            <input
                              type="number"
                              step="0.001"
                              min="0.001"
                              max="3"
                              className="inline-input"
                              value={optionDraft.fabric_multiplier}
                              onChange={(e) =>
                                setOptionDraft({
                                  ...optionDraft,
                                  fabric_multiplier: e.target.value,
                                })
                              }
                            />
                          ) : (
                            `×${Number(option.fabric_multiplier).toFixed(3)}`
                          )}
                        </td>
                        <td style={{ color: 'var(--taupe)' }}>{option.ai_prompt_term}</td>
                        <td>
                          <span className="row-actions">
                            {isEditing ? (
                              <>
                                <button
                                  type="button"
                                  className="oa-btn"
                                  onClick={async () => {
                                    const ok = await run(
                                      () => admin.updateOption(option.id, optionDraft),
                                      `${option.label} updated — new quotes use it immediately.`,
                                    );
                                    if (ok) setEditing(null);
                                  }}
                                >
                                  Save
                                </button>
                                <button
                                  type="button"
                                  className="oa-btn"
                                  onClick={() => setEditing(null)}
                                >
                                  Cancel
                                </button>
                              </>
                            ) : (
                              <>
                                <button
                                  type="button"
                                  className="oa-btn"
                                  onClick={() => {
                                    setEditing(option.id);
                                    setOptionDraft({
                                      stitching_premium: String(option.stitching_premium),
                                      fabric_multiplier: String(option.fabric_multiplier),
                                    });
                                  }}
                                >
                                  Edit
                                </button>
                                <button
                                  type="button"
                                  className="oa-btn"
                                  onClick={() =>
                                    run(
                                      () => admin.deactivateOption(option.id),
                                      `${option.label} withdrawn from the wizard.`,
                                    )
                                  }
                                >
                                  Remove
                                </button>
                              </>
                            )}
                          </span>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>

            {adding === group.id && (
              <form
                className="admin-form inline"
                onSubmit={async (e) => {
                  e.preventDefault();
                  const ok = await run(
                    () => admin.createOption(group.id, optionForm),
                    `"${optionForm.label}" added to ${group.label}.`,
                  );
                  if (ok) {
                    setOptionForm(EMPTY_OPTION);
                    setAdding(null);
                  }
                }}
              >
                <div className="field-row">
                  <div className="field">
                    <label htmlFor={`o-label-${group.id}`}>Label</label>
                    <input
                      id={`o-label-${group.id}`}
                      required
                      value={optionForm.label}
                      placeholder="Mandarin collar"
                      onChange={(e) =>
                        setOptionForm({
                          ...optionForm,
                          label: e.target.value,
                          code:
                            optionForm.code ||
                            e.target.value
                              .toLowerCase()
                              .trim()
                              .replace(/[^a-z0-9]+/g, '_'),
                          ai_prompt_term: optionForm.ai_prompt_term || e.target.value.toLowerCase(),
                        })
                      }
                    />
                  </div>
                  <div className="field">
                    <label htmlFor={`o-prompt-${group.id}`}>AI prompt term</label>
                    <input
                      id={`o-prompt-${group.id}`}
                      required
                      value={optionForm.ai_prompt_term}
                      onChange={(e) =>
                        setOptionForm({
                          ...optionForm,
                          ai_prompt_term: e.target.value,
                        })
                      }
                    />
                  </div>
                </div>
                <div className="field-row">
                  <div className="field">
                    <label htmlFor={`o-prem-${group.id}`}>Stitching premium (LKR)</label>
                    <input
                      id={`o-prem-${group.id}`}
                      type="number"
                      min="0"
                      value={optionForm.stitching_premium}
                      onChange={(e) =>
                        setOptionForm({
                          ...optionForm,
                          stitching_premium: e.target.value,
                        })
                      }
                    />
                  </div>
                  <div className="field">
                    <label htmlFor={`o-mult-${group.id}`}>Fabric multiplier</label>
                    <input
                      id={`o-mult-${group.id}`}
                      type="number"
                      step="0.001"
                      min="0.001"
                      max="3"
                      value={optionForm.fabric_multiplier}
                      onChange={(e) =>
                        setOptionForm({
                          ...optionForm,
                          fabric_multiplier: e.target.value,
                        })
                      }
                    />
                    <p className="form-label-hint">
                      Capped at 3. A typo of 12 instead of 1.2 would quote twelve times the cloth.
                    </p>
                  </div>
                </div>
                <button type="submit" className="btn-sm btn-light">
                  + Add option
                </button>
              </form>
            )}
          </div>
        ))}
      </div>
    </>
  );
}
