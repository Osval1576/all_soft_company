import { http } from "./http";

export async function listMyTickets() {
  const res = await http.get("/api/tickets_t/");
  return res.data;
}

export async function createTicket(data) {
  const res = await http.post("/api/tickets_t/", data);
  return res.data;
}

export async function updateTicket(id, data) {
  const res = await http.patch(`/api/tickets_t/${id}/`, data);
  return res.data;
}

export async function getTicketMessages(ticketId) {
  const res = await http.get(`/api/tickets_t/${ticketId}/messages/`);
  return res.data;
}

export async function listUsers() {
  const res = await http.get("/api/users/users/");
  return res.data;
}

export async function createUser(data) {
  const res = await http.post("/api/users/users/", data);
  return res.data;
}

export async function deleteUser(id) {
  await http.delete(`/api/users/users/${id}/`);
}

export async function getPool() {
  const res = await http.get("/api/tickets_t/pool/");
  return res.data;
}

export async function takeTicket(id) {
  const res = await http.post(`/api/tickets_t/${id}/take/`);
  return res.data;
}

export async function getTicketEvents(id) {
  const res = await http.get(`/api/tickets_t/${id}/events/`);
  return res.data;
}

export async function uploadAttachment(ticketId, file, caption) {
  const form = new FormData();
  form.append("file", file);
  if (caption) form.append("content", caption);
  const res = await http.post(`/api/tickets_t/${ticketId}/attachments/`, form);
  return res.data;
}

export async function fetchAttachmentBlob(url) {
  const res = await http.get(url, { responseType: "blob" });
  return res.data;
}