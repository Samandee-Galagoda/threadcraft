import { createContext, useContext, useEffect, useMemo, useReducer } from 'react';
import {
  STORAGE_KEY,
  createInitialState,
  hydrate,
  wizardReducer,
} from '../lib/wizardReducer';

const WizardContext = createContext(null);

function newDraftId() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) return crypto.randomUUID();
  // Fallback for older browsers — the backend only requires a valid UUID shape.
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    return (c === 'x' ? r : (r & 0x3) | 0x8).toString(16);
  });
}

function init() {
  const stored = sessionStorage.getItem(STORAGE_KEY);
  const hydrated = hydrate(stored, newDraftId());
  if (!hydrated.draftId) hydrated.draftId = newDraftId();
  return hydrated;
}

export function WizardProvider({ children }) {
  const [state, dispatch] = useReducer(wizardReducer, undefined, init);

  // sessionStorage, not localStorage: an abandoned design shouldn't resurrect a
  // week later, and it avoids a stale-catalogue-id class of bug.
  useEffect(() => {
    try {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch {
      // Private browsing / quota — persistence is a convenience, not a requirement.
    }
  }, [state]);

  const value = useMemo(() => ({ state, dispatch }), [state]);
  return <WizardContext.Provider value={value}>{children}</WizardContext.Provider>;
}

export function useWizard() {
  const context = useContext(WizardContext);
  if (!context) throw new Error('useWizard must be used inside a WizardProvider');
  return context;
}

export function resetWizard() {
  sessionStorage.removeItem(STORAGE_KEY);
}

export { createInitialState };
