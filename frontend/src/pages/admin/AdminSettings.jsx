import { useCallback, useEffect, useState } from 'react';
import { admin, ml, mockup } from '../../api';

/** Groups the pricing knobs so the page reads as "money" then "fit maths"
 *  rather than one alphabetical list of opaque keys. */
const GROUPS = [
  { title: 'Delivery', keys: ['delivery_fee', 'free_delivery_threshold'] },
  { title: 'Fit scaling', keys: ['size_factor_k', 'size_factor_min', 'size_factor_max'] },
];

function Health({ label, ok, detail, warn }) {
  return (
    <div className="health-row">
      <span className={`health-dot ${ok ? 'ok' : warn ? 'warn' : 'off'}`} />
      <div>
        <strong>{label}</strong>
        <div className="order-detail">{detail}</div>
      </div>
    </div>
  );
}

export default function AdminSettings() {
  const [settings, setSettings] = useState([]);
  const [drafts, setDrafts] = useState({});
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState(null);
  const [saving, setSaving] = useState(null);

  const load = useCallback(async () => {
    try {
      const rows = await admin.settings();
      setSettings(rows);
      setDrafts(Object.fromEntries(rows.map((r) => [r.key, r.value])));
    } catch (err) {
      setError(err.message || 'Could not load settings.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
    // Health is best-effort: a failing probe must not blank the settings form,
    // so each promise resolves to null rather than rejecting the batch.
    Promise.all([
      admin.emailStatus().catch(() => null),
      mockup.status().catch(() => null),
      ml.status().catch(() => null),
    ]).then(([email, image, models]) => setHealth({ email, image, models }));
  }, [load]);

  async function save(key) {
    setSaving(key);
    setError(null);
    setNotice(null);
    try {
      const updated = await admin.updateSetting(key, String(drafts[key]));
      setSettings((rows) => rows.map((r) => (r.key === key ? updated : r)));
      setNotice(`${updated.label || key} saved — new quotes use it immediately.`);
    } catch (err) {
      setError(err.message || 'Could not save that setting.');
    } finally {
      setSaving(null);
    }
  }

  if (loading) return <div className="wizard-loading">Loading settings…</div>;

  const byKey = Object.fromEntries(settings.map((s) => [s.key, s]));
  const grouped = new Set(GROUPS.flatMap((g) => g.keys));
  const others = settings.filter((s) => !grouped.has(s.key));

  return (
    <>
      <div className="portal-header">
        <h1>Settings</h1>
        <p>Pricing rules and system health</p>
      </div>

      {notice && <div className="admin-alert">{notice}</div>}
      {error && <div className="wizard-error">{error}</div>}

      {[...GROUPS, { title: 'Other', keys: others.map((s) => s.key) }]
        .filter((group) => group.keys.some((k) => byKey[k]))
        .map((group) => (
          <div className="card" key={group.title}>
            <div className="card-head">
              <div className="card-title">{group.title}</div>
            </div>
            {group.keys
              .filter((k) => byKey[k])
              .map((key) => {
                const setting = byKey[key];
                const dirty = String(drafts[key]) !== String(setting.value);
                return (
                  <div className="setting-row" key={key}>
                    <div className="setting-meta">
                      <label htmlFor={`set-${key}`}>{setting.label || key}</label>
                      {setting.description && (
                        <p className="form-label-hint">{setting.description}</p>
                      )}
                    </div>
                    <div className="setting-control">
                      <input
                        id={`set-${key}`}
                        className="inline-input"
                        value={drafts[key] ?? ''}
                        inputMode={setting.value_type === 'number' ? 'decimal' : 'text'}
                        onChange={(e) => setDrafts({ ...drafts, [key]: e.target.value })}
                        onKeyDown={(e) => e.key === 'Enter' && dirty && save(key)}
                      />
                      <button
                        type="button"
                        className="oa-btn"
                        disabled={!dirty || saving === key}
                        onClick={() => save(key)}
                      >
                        {saving === key ? 'Saving…' : 'Save'}
                      </button>
                    </div>
                  </div>
                );
              })}
          </div>
        ))}

      <div className="card">
        <div className="card-head">
          <div className="card-title">System health</div>
        </div>
        <p className="form-label-hint">
          Every integration degrades to a working fallback rather than failing, which means a
          missing key is invisible from the customer UI. Check this page before a demo.
        </p>

        {!health ? (
          <p className="admin-empty">Checking…</p>
        ) : (
          <>
            <Health
              label="Image generation"
              ok={health.image && !health.image.will_use_fallback}
              warn={Boolean(health.image?.will_use_fallback)}
              detail={
                !health.image
                  ? 'Status endpoint unreachable.'
                  : health.image.will_use_fallback
                    ? 'No provider key — mockups use the deterministic placeholder.'
                    : `${health.image.cloudflare_configured ? 'Cloudflare Workers AI' : 'Hugging Face'} · storage: ${health.image.storage_backend}`
              }
            />
            <Health
              label="Transactional email"
              ok={Boolean(health.email?.configured)}
              warn={Boolean(health.email) && !health.email.configured}
              detail={
                !health.email
                  ? 'Status endpoint unreachable.'
                  : `${health.email.mode} · from ${health.email.from_address}`
              }
            />
            <Health
              label="ML models"
              ok={Boolean(health.models?.ml_enabled) && health.models.models.some((m) => m.loaded)}
              warn={Boolean(health.models) && !health.models.ml_enabled}
              detail={
                !health.models
                  ? 'Status endpoint unreachable.'
                  : !health.models.ml_enabled
                    ? 'ML disabled — size and measurement assistance is hidden in the wizard.'
                    : health.models.models
                        .map((m) => `${m.name}: ${m.loaded ? 'loaded' : m.error || 'not loaded'}`)
                        .join(' · ')
              }
            />
          </>
        )}
      </div>
    </>
  );
}
