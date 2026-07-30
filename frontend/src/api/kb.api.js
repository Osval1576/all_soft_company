import { http } from "./http";

// Fase 3A — administración de la base de conocimiento del tenant (solo ADMIN).
const BASE = "/api/admin/kb/articles/";

export async function listArticles() {
  const res = await http.get(BASE);
  return res.data;
}

export async function createArticle(data) {
  const res = await http.post(BASE, data);
  return res.data;
}

export async function updateArticle(id, data) {
  const res = await http.patch(`${BASE}${id}/`, data);
  return res.data;
}

export async function deleteArticle(id) {
  await http.delete(`${BASE}${id}/`);
}

// Fase 3B — deflección: intenta resolver la consulta con la KB antes de abrir
// ticket. Devuelve { available, resolved, answer, sources }.
export async function deflect(query) {
  const res = await http.post("/api/kb/deflect/", { query });
  return res.data;
}

// Fase 5.2 — cola de sugerencias de KB (generadas por IA al resolver tickets).
const SUG = "/api/admin/kb/suggestions/";

export async function listSuggestions(status = "pending") {
  const res = await http.get(`${SUG}?status=${status}`);
  return res.data;
}

export async function updateSuggestion(id, data) {
  const res = await http.patch(`${SUG}${id}/`, data);
  return res.data;
}

export async function acceptSuggestion(id) {
  const res = await http.post(`${SUG}${id}/accept/`);
  return res.data;
}

export async function dismissSuggestion(id) {
  const res = await http.post(`${SUG}${id}/dismiss/`);
  return res.data;
}
