import { http } from "./http";

const P = "/api/public";

export const landingApi = {
  getHero: () => http.get(`${P}/landing/hero/`).then(r => r.data),
  getAbout: () => http.get(`${P}/landing/about/`).then(r => r.data),
  getFeatures: () => http.get(`${P}/landing/features/`).then(r => r.data),
  getTeam: () => http.get(`${P}/landing/team/`).then(r => r.data),
  getLocations: () => http.get(`${P}/landing/locations/`).then(r => r.data),
  getSiteSettings: () => http.get(`${P}/site-settings/`).then(r => r.data),
  postContact: (payload) => http.post(`${P}/contact/`, payload).then(r => r.data),
};

const A = "/api/admin";

export const landingAdminApi = {
  // singletons
  getHero: () => http.get(`${A}/landing/hero/`).then(r => r.data),
  putHero: (data) => http.put(`${A}/landing/hero/`, data).then(r => r.data),
  getAbout: () => http.get(`${A}/landing/about/`).then(r => r.data),
  putAbout: (data) => http.put(`${A}/landing/about/`, data).then(r => r.data),
  getSettings: () => http.get(`${A}/site-settings/`).then(r => r.data),
  putSettings: (formData) => http.put(`${A}/site-settings/`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  }).then(r => r.data),
  // features
  listFeatures: () => http.get(`${A}/landing/features/`).then(r => r.data),
  createFeature: (data) => http.post(`${A}/landing/features/`, data).then(r => r.data),
  updateFeature: (id, data) => http.put(`${A}/landing/features/${id}/`, data).then(r => r.data),
  deleteFeature: (id) => http.delete(`${A}/landing/features/${id}/`),
  reorderFeatures: (ids) => http.post(`${A}/landing/features/reorder/`, { ids }),
  // team
  listTeam: () => http.get(`${A}/landing/team/`).then(r => r.data),
  createTeam: (formData) => http.post(`${A}/landing/team/`, formData, { headers: { "Content-Type": "multipart/form-data" } }).then(r => r.data),
  updateTeam: (id, formData) => http.put(`${A}/landing/team/${id}/`, formData, { headers: { "Content-Type": "multipart/form-data" } }).then(r => r.data),
  deleteTeam: (id) => http.delete(`${A}/landing/team/${id}/`),
  reorderTeam: (ids) => http.post(`${A}/landing/team/reorder/`, { ids }),
  // locations
  listLocations: () => http.get(`${A}/landing/locations/`).then(r => r.data),
  createLocation: (formData) => http.post(`${A}/landing/locations/`, formData, { headers: { "Content-Type": "multipart/form-data" } }).then(r => r.data),
  updateLocation: (id, formData) => http.put(`${A}/landing/locations/${id}/`, formData, { headers: { "Content-Type": "multipart/form-data" } }).then(r => r.data),
  deleteLocation: (id) => http.delete(`${A}/landing/locations/${id}/`),
  reorderLocations: (ids) => http.post(`${A}/landing/locations/reorder/`, { ids }),
};
