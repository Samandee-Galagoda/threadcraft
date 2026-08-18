import { createContext, useCallback, useContext, useMemo, useState } from 'react';
import { auth as authApi } from '../api';
import { getStoredUser, getToken } from '../api/client';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  // Initialised synchronously from localStorage rather than in a useEffect.
  // Doing it in an effect causes a one-frame flash of the signed-out navbar on
  // every page load, and trips react-hooks/set-state-in-effect.
  const [user, setUser] = useState(() => (getToken() ? getStoredUser() : null));

  const login = useCallback(async (credentials) => {
    const signedIn = await authApi.login(credentials);
    setUser(signedIn);
    return signedIn;
  }, []);

  const register = useCallback(async (details) => {
    const created = await authApi.register(details);
    setUser(created);
    return created;
  }, []);

  /** Replace the cached user after a profile edit, so the admin sidebar and
   *  navbar reflect a renamed or re-addressed account without a re-login. */
  const refreshUser = useCallback((updated) => {
    setUser(updated);
    localStorage.setItem('tc_user', JSON.stringify(updated));
  }, []);

  const logout = useCallback(() => {
    authApi.logout();
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({
      user,
      isAuthenticated: Boolean(user),
      isAdmin: user?.role === 'admin',
      login,
      register,
      logout,
      refreshUser,
    }),
    [user, login, register, logout, refreshUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used inside an AuthProvider');
  return context;
}
