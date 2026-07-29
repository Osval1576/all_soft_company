import { http } from "./http";

// Fase 1A — auto-borrador. Devuelve { draft } o 403 (customer / plan sin IA).
export async function draftReply(ticketId) {
  const res = await http.post(`/api/ai/tickets/${ticketId}/draft/`);
  return res.data;
}

// Fase 2A — resumen del hilo. Devuelve { summary } o 403 (customer / plan sin IA).
export async function summarizeTicket(ticketId) {
  const res = await http.post(`/api/ai/tickets/${ticketId}/summary/`);
  return res.data;
}

// Fase 4 — insights de negocio sobre métricas. Devuelve { insights, snapshot }.
export async function getInsights(window) {
  const res = await http.post(`/api/ai/insights/?window=${window || 30}`);
  return res.data;
}

// Fase 5.3 — traducción. Devuelve { translated } o 403 (customer / plan sin IA).
export async function translate(text, targetLang) {
  const res = await http.post("/api/ai/translate/", { text, target_lang: targetLang });
  return res.data;
}

// Fase 0 — guardrails por tenant (opt-in + rate limits + presupuesto). Solo ADMIN.
export async function getAiSettings() {
  return (await http.get("/api/admin/ai/settings/")).data;
}
export async function updateAiSettings(data) {
  return (await http.patch("/api/admin/ai/settings/", data)).data;
}
