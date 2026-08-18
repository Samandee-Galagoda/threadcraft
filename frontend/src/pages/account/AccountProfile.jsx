import { useEffect, useState } from 'react';
import { AdminHeader } from '../admin/AdminLayout';
import { auth } from '../../api';
import { useAuth } from '../../context/AuthContext';

export default function AccountProfile() {
  const { user, refreshUser, logout } = useAuth();
  const [profile, setProfile] = useState({ first_name: '', last_name: '', email: '' });
  const [passwords, setPasswords] = useState({
    current_password: '',
    new_password: '',
    confirm: '',
  });
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setProfile({
      first_name: user?.first_name ?? '',
      last_name: user?.last_name ?? '',
      email: user?.email ?? '',
    });
  }, [user]);

  const emailChanged = profile.email !== (user?.email ?? '');
  const changingPassword = Boolean(passwords.new_password);
  const needsCurrent = emailChanged || changingPassword;

  async function save(event) {
    event.preventDefault();
    setNotice(null);
    setError(null);

    if (changingPassword && passwords.new_password !== passwords.confirm) {
      setError('The two new passwords do not match.');
      return;
    }

    setSaving(true);
    try {
      const payload = { ...profile };
      if (needsCurrent) payload.current_password = passwords.current_password;
      if (changingPassword) payload.new_password = passwords.new_password;

      const updated = await auth.updateProfile(payload);
      refreshUser(updated);
      setPasswords({ current_password: '', new_password: '', confirm: '' });
      setNotice(
        changingPassword
          ? 'Saved. Your new password is active — use it next time you sign in.'
          : 'Profile saved.',
      );
    } catch (err) {
      setError(err.message || 'Could not save your profile.');
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <AdminHeader title="My profile" subtitle="Your details, sign-in email and password" />

      <div className="admin-content">
        {notice && <div className="admin-alert">{notice}</div>}
        {error && <div className="wizard-error">{error}</div>}

        <div className="admin-grid-2">
          <div className="admin-card">
            <div className="admin-card-title">Your details</div>
            <form
              className="admin-form"
              style={{ borderTop: 'none', marginTop: 0 }}
              onSubmit={save}
            >
              <div className="field-row">
                <div className="field">
                  <label htmlFor="c-first">First name</label>
                  <input
                    id="c-first"
                    value={profile.first_name}
                    onChange={(e) => setProfile({ ...profile, first_name: e.target.value })}
                  />
                </div>
                <div className="field">
                  <label htmlFor="c-last">Last name</label>
                  <input
                    id="c-last"
                    value={profile.last_name}
                    onChange={(e) => setProfile({ ...profile, last_name: e.target.value })}
                  />
                </div>
              </div>

              <div className="field">
                <label htmlFor="c-email">Email address</label>
                <input
                  id="c-email"
                  type="email"
                  value={profile.email}
                  onChange={(e) => setProfile({ ...profile, email: e.target.value })}
                />
                <p className="form-label-hint">
                  This is your sign-in username, and where order confirmations are sent.
                </p>
              </div>

              <div className="field-row">
                <div className="field">
                  <label htmlFor="c-new">New password</label>
                  <input
                    id="c-new"
                    type="password"
                    autoComplete="new-password"
                    placeholder="Leave blank to keep your current one"
                    value={passwords.new_password}
                    onChange={(e) => setPasswords({ ...passwords, new_password: e.target.value })}
                  />
                </div>
                <div className="field">
                  <label htmlFor="c-confirm">Confirm new password</label>
                  <input
                    id="c-confirm"
                    type="password"
                    autoComplete="new-password"
                    disabled={!changingPassword}
                    value={passwords.confirm}
                    onChange={(e) => setPasswords({ ...passwords, confirm: e.target.value })}
                  />
                </div>
              </div>

              {needsCurrent && (
                <div className="field">
                  <label htmlFor="c-current">Current password</label>
                  <input
                    id="c-current"
                    type="password"
                    autoComplete="current-password"
                    required
                    value={passwords.current_password}
                    onChange={(e) =>
                      setPasswords({ ...passwords, current_password: e.target.value })
                    }
                  />
                  {/* Asked for only when a credential actually changes. Renaming
                      yourself shouldn't require re-authenticating; changing the
                      address or password must, or a session left open on a
                      shared machine could lock you out of your own account. */}
                  <p className="form-label-hint">
                    Required to change your email address or password.
                  </p>
                </div>
              )}

              <button type="submit" className="btn-sm btn-dark" disabled={saving}>
                {saving ? 'Saving…' : 'Save changes'}
              </button>
            </form>
          </div>

          <div className="admin-card">
            <div className="admin-card-title">Account</div>
            <div className="mini-stat">
              <span className="mini-stat-label">Signed in as</span>
              <span className="mini-stat-val" style={{ fontSize: 13 }}>
                {user?.email}
              </span>
            </div>
            <div className="mini-stat">
              <span className="mini-stat-label">Account type</span>
              <span className="mini-stat-val" style={{ fontSize: 13 }}>
                {user?.role === 'admin' ? 'Administrator' : 'Customer'}
              </span>
            </div>
            <p className="form-label-hint" style={{ margin: '16px 0' }}>
              Your measurements and saved designs stay with this account, so anything you save is
              waiting for you next time.
            </p>
            <button type="button" className="btn-sm btn-light" onClick={logout}>
              Sign out
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
