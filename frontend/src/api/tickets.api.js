import { http } from "./http";

export async function listMyAssignedTickets() {
  const res = await http.get("/api/tickets_t/");
  return res.data;
}

export async function getTicketMessages(ticketId) {
  const res = await http.get(`/api/tickets_t/${ticketId}/messages/`);
  return res.data;
}