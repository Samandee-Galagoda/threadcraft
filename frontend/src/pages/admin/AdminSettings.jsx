import { useEffect, useState } from 'react';
import { AdminHeader } from './AdminLayout';
import { auth, ml, mockup, payments } from '../../api';
import { useAuth } from '../../context/AuthContext';

function Health({ label, ok, warn, detail }) {
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
  const { user, refreshUser } = useAuth();
  const [profile, setProfile] = useState({
    first_name: '',
    last_name: '',
    email: '',
  });
  const [passwords, setPasswords] = useState({
    current_password: '',
    new_password: '',
  });
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState(null);
  const [error, setError] = useState(null);
  const [health, setHealth] = useState(null);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setProfile({
      first_name: user?.first_name ?? '',
      last_name: user?.last_name ?? '',
      email: user?.email ?? '',
    });
    Promise.all([
      mockup.status().catch(() => null),
      ml.status().catch(() => null),
      payments.status().catch(() => null),
    ]).then(([image, models, pay]) => setHealth({ image, models, pay }));
  }, [user]);

  const emailChanged = profile.email !== (user?.email ?? '');
  const changingCredentials = emailChanged || Boolean(passwords.new_password);

  async function save(event) {
    event.preventDefault();
    setSaving(true);
    setNotice(null);
    setError(null);
    try {
      const payload = { ...profile };
      if (changingCredentials) payload.current_password = passwords.current_password;
      if (passwords.new_password) payload.new_password = passwords.new_password;
      const updated = await auth.updateProfile(payload);
      refreshUser(updated);
      setPasswords({ current_password: '', new_password: '' });
      setNotice('Profile saved.');
    } catch (err) {
      setError(err.message || 'Could not save your profile.');
    } finally {
      setSaving(false);
    }
  }

  const modelByName = Object.fromEntries((health?.models?.models ?? []).map((m) => [m.name, m]));
  const measurement = modelByName.measurement_predictor;
  const classifier = modelByName.garment_classifier;

  return (
    <>
      <AdminHeader title="Settings" subtitle="Your administrator profile and system health" />

      <div className="admin-content">
        {notice && <div className="admin-alert">{notice}</div>}
        {error && <div className="wizard-error">{error}</div>}

        <div className="admin-grid-2">
          <div className="admin-card">
            <div className="admin-card-title">Administrator profile</div>
            <form
              className="admin-form"
              onSubmit={save}
              style={{ borderTop: 'none', marginTop: 0 }}
            >
              <div className="field-row">
                <div className="field">
                  <label htmlFor="p-first">First name</label>
                  <input
                    id="p-first"
                    value={profile.first_name}
                    onChange={(e) => setProfile({ ...profile, first_name: e.target.value })}
                  />
                </div>
                <div className="field">
                  <label htmlFor="p-last">Last name</label>
                  <input
                    id="p-last"
                    value={profile.last_name}
                    onChange={(e) => setProfile({ ...profile, last_name: e.target.value })}
                  />
                </div>
              </div>
              <div className="field">
                <label htmlFor="p-email">Email address</label>
                <input
                  id="p-email"
                  type="email"
                  value={profile.email}
                  onChange={(e) => setProfile({ ...profile, email: e.target.value })}
                />
                <p className="form-label-hint">This is also your sign-in username.</p>
              </div>
              <div className="field">
                <label htmlFor="p-new">New password</label>
                <input
                  id="p-new"
                  type="password"
                  autoComplete="new-password"
                  placeholder="Leave blank to keep your current password"
                  value={passwords.new_password}
                  onChange={(e) => setPasswords({ ...passwords, new_password: e.target.value })}
                />
              </div>
              {changingCredentials && (
                <div className="field">
                  <label htmlFor="p-current">Current password</label>
                  <input
                    id="p-current"
                    type="password"
                    autoComplete="current-password"
                    required
                    value={passwords.current_password}
                    onChange={(e) =>
                      setPasswords({
                        ...passwords,
                        current_password: e.target.value,
                      })
                    }
                  />
                  {/* Only demanded when a credential actually moves — renaming
                      yourself shouldn't require re-authenticating, but changing
                      the address or password must, or a stolen session could
                      lock the real owner out. */}
                  <p className="form-label-hint">
                    Required to change your email address or password.
                  </p>
                </div>
              )}
              <button type="submit" className="btn-sm btn-dark" disabled={saving}>
                {saving ? 'Saving…' : 'Save profile'}
              </button>
            </form>
          </div>

          <div className="admin-card">
            <div className="admin-card-title">System health</div>
            <p className="form-label-hint" style={{ marginBottom: 12 }}>
              Every integration degrades to a working fallback rather than failing, so a missing key
              is invisible from the customer UI. Check here before a demo.
            </p>
            {!health ? (
              <p className="admin-empty-row">Checking…</p>
            ) : (
              <>
                <Health
                  label="AI mockups"
                  ok={health.image && !health.image.will_use_fallback}
                  warn={Boolean(health.image?.will_use_fallback)}
                  detail={
                    !health.image
                      ? 'Status endpoint unreachable.'
                      : health.image.will_use_fallback
                        ? 'No provider key — previews use a deterministic placeholder.'
                        : `${health.image.cloudflare_configured ? 'Cloudflare Workers AI' : 'Hugging Face'} · storage: ${health.image.storage_backend}`
                  }
                />
                <Health
                  label="Payments"
                  ok={Boolean(health.pay?.configured)}
                  warn={Boolean(health.pay) && !health.pay.configured}
                  detail={
                    !health.pay
                      ? 'Status endpoint unreachable.'
                      : health.pay.configured
                        ? 'Stripe test mode — card 4242 4242 4242 4242.'
                        : 'Simulated — orders are marked paid without a charge.'
                  }
                />
                <Health
                  label="Measurement assistance"
                  ok={Boolean(measurement?.loaded)}
                  warn={!measurement?.repo}
                  detail={
                    !measurement?.repo
                      ? 'Not configured on this deployment.'
                      : measurement.loaded
                        ? 'Loaded — Step 4 estimates measurements and flags inconsistencies.'
                        : measurement.error || 'Configured; loads on first use.'
                  }
                />
                <Health
                  label="Garment recogniser"
                  ok={Boolean(classifier?.loaded)}
                  warn={!classifier?.repo}
                  detail={
                    !classifier?.repo
                      ? 'Off here — the ViT needs ~1.15 GB against a 512 MB instance. Runs locally.'
                      : classifier.loaded
                        ? 'Loaded — Step 2 suggests a garment type from a photo.'
                        : classifier.error || 'Configured; loads on first use.'
                  }
                />
              </>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
