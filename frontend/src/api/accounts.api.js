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
export async function listInvitations() {
  return (await http.get("/api/invitations/")).data;
}
export async function createInvitation(email, role) {
  return (await http.post("/api/invitations/", { email, role })).data;
}
export async function revokeInvitation(id) {
  await http.delete(`/api/invitations/${id}/`);
}
export async function listMembers() {
  return (await http.get("/api/users/users/")).data;
}
export async function updateMember(id, patch) {
  return (await http.patch(`/api/users/users/${id}/`, patch)).data;
}
