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
