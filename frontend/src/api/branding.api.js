import { http } from "./http";

export async function getBranding() {
  return (await http.get("/api/branding/")).data;
}

export async function saveBranding(payload) {
  // payload: FormData (con logo) o objeto plano
  return (await http.put("/api/branding/", payload)).data;
}

export async function getPublicBranding(slug) {
  return (await http.get(`/api/public/branding/${slug}/`)).data;
}
