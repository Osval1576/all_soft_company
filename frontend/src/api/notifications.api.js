import { http } from "./http";

export async function listNotifications() {
  const res = await http.get("/api/notifications/");
  return res.data;
}

export async function markRead(id) {
  const res = await http.post(`/api/notifications/${id}/read/`);
  return res.data;
}

export async function markAllRead() {
  await http.post("/api/notifications/read-all/");
}

export async function getNotifPreferences() {
  const res = await http.get("/api/notifications/preferences/");
  return res.data;
}

export async function updateNotifPreferences(data) {
  const res = await http.patch("/api/notifications/preferences/", data);
  return res.data;
}
