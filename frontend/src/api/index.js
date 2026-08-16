import { api, clearSession, setSession } from './client';

// ── Auth ──────────────────────────────────────────────────────────────────
export const auth = {
  async register({ firstName, lastName, email, password }) {
    const data = await api.post(
      '/api/auth/register',
      { first_name: firstName, last_name: lastName, email, password },
      { auth: false },
    );
    setSession(data.access_token, data.user);
    return data.user;
  },

  async login({ email, password }) {
    const data = await api.post('/api/auth/login', { email, password }, { auth: false });
    setSession(data.access_token, data.user);
    return data.user;
  },

  logout() {
    clearSession();
  },

  me: () => api.get('/api/auth/me'),
};

// ── Catalogue ─────────────────────────────────────────────────────────────
export const catalog = {
  clothTypes: () => api.get('/api/catalog/cloth-types', { auth: false }),
  clothType: (slug) => api.get(`/api/catalog/cloth-types/${slug}`, { auth: false }),
  materials: () => api.get('/api/catalog/materials', { auth: false }),
};

// ── Pricing ───────────────────────────────────────────────────────────────
export const pricing = {
  quote: (payload, opts) => api.post('/api/quote', payload, { auth: false, ...opts }),
};

// ── Orders ────────────────────────────────────────────────────────────────
export const orders = {
  create: (payload) => api.post('/api/orders', payload),
  track: (orderNumber) => api.get(`/api/orders/track/${orderNumber}`, { auth: false }),
  mine: () => api.get('/api/orders/me'),
};

// ── Dashboard / measurements / designs ────────────────────────────────────
export const dashboard = {
  load: () => api.get('/api/dashboard'),
};

export const measurements = {
  save: (payload) => api.put('/api/measurements', payload),
};

export const designs = {
  list: () => api.get('/api/designs'),
  save: (payload) => api.post('/api/designs', payload),
};

// ── AI mockup ─────────────────────────────────────────────────────────────
export const mockup = {
  generate: (payload) => api.post('/api/mockup', payload, { auth: false }),
  status: () => api.get('/api/mockup/status', { auth: false }),
};

// ── Uploads ───────────────────────────────────────────────────────────────
export const uploads = {
  reference(draftId, file) {
    const form = new FormData();
    form.append('draft_id', draftId);
    form.append('file', file);
    return api.post('/api/uploads/reference', form, { auth: false });
  },
  list: (draftId) => api.get(`/api/uploads/reference/${draftId}`, { auth: false }),
  remove: (imageId) => api.del(`/api/uploads/reference/${imageId}`, { auth: false }),
};

// ── ML-backed assistance ──────────────────────────────────────────────────
// Every one of these is advisory. Callers must treat `available: false` as a
// normal outcome and carry on — none of it may block the ordering flow.
export const ml = {
  suggestMeasurements: (profile) =>
    api.post('/api/ml/measurements/suggest', profile, { auth: false }),
  validateMeasurements: (profile) =>
    api.post('/api/ml/measurements/validate', profile, { auth: false }),
  recommendSize: (profile) => api.post('/api/ml/recommend-size', profile, { auth: false }),
  classifyGarment(file) {
    const form = new FormData();
    form.append('file', file);
    return api.post('/api/ml/classify-garment', form, { auth: false });
  },
  status: () => api.get('/api/ml/status', { auth: false }),
};

// ── Admin ─────────────────────────────────────────────────────────────────
export const admin = {
  analytics: (days = 30) => api.get(`/api/admin/analytics?days=${days}`),
  revenue: (days = 30) => api.get(`/api/admin/analytics/revenue?days=${days}`),

  orders: (status) =>
    api.get(`/api/admin/orders${status ? `?status=${encodeURIComponent(status)}` : ''}`),
  updateOrderStatus: (orderId, status, note) =>
    api.patch(`/api/admin/orders/${orderId}/status`, { status, note }),
  emailStatus: () => api.get('/api/admin/orders/email-status'),

  materials: () => api.get('/api/admin/inventory/materials'),
  lowStock: () => api.get('/api/admin/inventory/low-stock'),
  updateStock: (materialId, stockMetres) =>
    api.patch(`/api/admin/inventory/materials/${materialId}/stock`, {
      stock_metres: stockMetres,
    }),

  clothTypes: () => api.get('/api/admin/catalog/cloth-types'),
  createClothType: (payload) => api.post('/api/admin/catalog/cloth-types', payload),
  updateClothType: (id, payload) => api.patch(`/api/admin/catalog/cloth-types/${id}`, payload),
  deactivateClothType: (id) => api.del(`/api/admin/catalog/cloth-types/${id}`),
  addMeasurementField: (clothTypeId, payload) =>
    api.post(`/api/admin/catalog/cloth-types/${clothTypeId}/measurement-fields`, payload),
  deleteMeasurementField: (fieldId) =>
    api.del(`/api/admin/catalog/measurement-fields/${fieldId}`),

  settings: () => api.get('/api/admin/settings'),
  updateSetting: (key, value) => api.put(`/api/admin/settings/${key}`, { value }),
};

export { ApiError, mediaUrl } from './client';
