/**
 * Single place that talks to the API.
 *
 * VITE_API_URL is empty in development, so requests go to /api/... and Vite's
 * dev proxy forwards them to the backend — no CORS involved locally. In
 * production it is the deployed API origin.
 *
 * NOTE: Vite inlines VITE_* variables at BUILD time. Changing VITE_API_URL in
 * the Vercel dashboard does nothing until you redeploy.
 */
const BASE = import.meta.env.VITE_API_URL ?? '';

export class ApiError extends Error {
  constructor(message, status, detail) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

export function getToken() {
  return localStorage.getItem('tc_token');
}

export function getStoredUser() {
  try {
    return JSON.parse(localStorage.getItem('tc_user'));
  } catch {
    return null;
  }
}

export function setSession(token, user) {
  localStorage.setItem('tc_token', token);
  localStorage.setItem('tc_user', JSON.stringify(user));
}

export function clearSession() {
  localStorage.removeItem('tc_token');
  localStorage.removeItem('tc_user');
}

async function extractDetail(response) {
  try {
    const body = await response.json();
    if (typeof body.detail === 'string') return body.detail;
    // FastAPI validation errors come back as a list of objects.
    if (Array.isArray(body.detail)) {
      return body.detail.map((d) => d.msg || JSON.stringify(d)).join('; ');
    }
    return response.statusText;
  } catch {
    return response.statusText || 'Request failed';
  }
}

async function request(path, { method = 'GET', body, auth = true, headers = {}, signal } = {}) {
  const token = auth ? getToken() : null;
  const isFormData = body instanceof FormData;

  const response = await fetch(`${BASE}${path}`, {
    method,
    headers: {
      ...(isFormData ? {} : body ? { 'Content-Type': 'application/json' } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...headers,
    },
    body: isFormData ? body : body ? JSON.stringify(body) : undefined,
    signal,
  });

  // An expired token should bounce the user to sign-in rather than surfacing a
  // confusing 401 in the middle of the wizard.
  if (response.status === 401 && auth && token) {
    clearSession();
    if (!window.location.pathname.startsWith('/auth')) {
      window.location.assign('/auth?expired=1');
    }
  }

  if (!response.ok) {
    throw new ApiError(await extractDetail(response), response.status);
  }
  return response.status === 204 ? null : response.json();
}

export const api = {
  get: (path, opts) => request(path, { ...opts, method: 'GET' }),
  post: (path, body, opts) => request(path, { ...opts, method: 'POST', body }),
  put: (path, body, opts) => request(path, { ...opts, method: 'PUT', body }),
  patch: (path, body, opts) => request(path, { ...opts, method: 'PATCH', body }),
  del: (path, opts) => request(path, { ...opts, method: 'DELETE' }),
};

/** Absolute URL for an image path returned by the API. */
export function mediaUrl(path) {
  if (!path) return null;
  if (path.startsWith('http://') || path.startsWith('https://')) return path;
  return `${BASE}${path}`;
}
