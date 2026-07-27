import { http } from "./http";

// Fase 1A — auto-borrador. Devuelve { draft } o 403 (customer / plan sin IA).
export async function draftReply(ticketId) {
  const res = await http.post(`/api/ai/tickets/${ticketId}/draft/`);
  return res.data;
}
