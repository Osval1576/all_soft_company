import { http } from "./http";

export async function login(username, password) {
  // OJO: esto solo funcionará si tu backend setea cookies en login
  const res = await http.post("/api/auth/login/", { username, password });
  return res.data;
}

export async function me() {
  const res = await http.get("/api/me/");
  return res.data;
}

export async function logout() {
  // Idealmente tendrás /api/auth/logout/ que borre cookies
  const res = await http.post("/api/auth/logout/");
  return res.data;
}