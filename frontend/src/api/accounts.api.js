import { http } from "./http";

export async function registerOrg(payload) {
  return (await http.post("/api/auth/register/", payload)).data;
}
export async function verifyEmail(token) {
  return (await http.post("/api/auth/verify-email/", { token })).data;
}
export async function resendVerification(email) {
  return (await http.post("/api/auth/resend-verification/", { email })).data;
}
export async function getInvitation(token) {
  return (await http.get(`/api/auth/invitation/${token}/`)).data;
}
export async function acceptInvitation(token, payload) {
  return (await http.post(`/api/auth/invitation/${token}/accept/`, payload)).data;
}
