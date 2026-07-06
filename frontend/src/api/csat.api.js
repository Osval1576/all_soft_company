import { http } from "./http";

export async function submitCsat(ticketId, { score, comment }) {
  const res = await http.post(`/api/csat/${ticketId}/`, { score, comment });
  return res.data;
}
