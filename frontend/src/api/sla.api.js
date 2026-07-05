import { http } from "./http";

export async function getSlaConfig() { return (await http.get("/api/admin/sla/config/")).data; }
export async function updateSlaConfig(data) { return (await http.patch("/api/admin/sla/config/", data)).data; }
export async function getSlaPolicies() { return (await http.get("/api/admin/sla/policies/")).data; }
export async function updateSlaPolicies(list) { return (await http.patch("/api/admin/sla/policies/", list)).data; }
export async function getHolidays() { return (await http.get("/api/admin/sla/holidays/")).data; }
export async function createHoliday(data) { return (await http.post("/api/admin/sla/holidays/", data)).data; }
export async function deleteHoliday(id) { await http.delete(`/api/admin/sla/holidays/${id}/`); }
