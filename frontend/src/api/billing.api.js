import { http } from "./http";

export async function getSubscription() {
  return (await http.get("/api/billing/subscription/")).data;
}
export async function startCheckout(planKey) {
  return (await http.post("/api/billing/checkout/", { plan_key: planKey })).data;
}
export async function openPortal() {
  return (await http.post("/api/billing/portal/", {})).data;
}
