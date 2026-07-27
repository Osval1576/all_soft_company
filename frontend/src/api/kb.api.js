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
