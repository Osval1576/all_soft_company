// frontend/src/api/metrics.api.js
import { http } from "./http";

export async function getAdminMetrics(window = 30) {
  return (await http.get(`/api/metrics/admin/?window=${window}`)).data;
}

export async function getMyMetrics(window = 30) {
  return (await http.get(`/api/metrics/me/?window=${window}`)).data;
}
