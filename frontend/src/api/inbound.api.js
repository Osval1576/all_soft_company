import { http } from "./http";

// Fase 5.1 — cuentas de canal omnicanal (WhatsApp / email / widget / Messenger /
// Instagram) por tenant. Mapean el identificador del webhook a la org. Solo ADMIN.
const BASE = "/api/admin/inbound/accounts/";

export async function listChannelAccounts() {
  return (await http.get(BASE)).data;
}

export async function createChannelAccount(data) {
  return (await http.post(BASE, data)).data;
}

export async function updateChannelAccount(id, data) {
  return (await http.patch(`${BASE}${id}/`, data)).data;
}

export async function deleteChannelAccount(id) {
  await http.delete(`${BASE}${id}/`);
}
