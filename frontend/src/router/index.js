import { createRouter, createWebHistory } from "vue-router";

import LoginView from "../views/LoginView.vue";
import ClientDashboard from "../views/dashboards/ClientDashboard.vue";
import TechnicianDashboard from "../views/dashboards/TechnicianDashboard.vue";
import AdminDashboard from "../views/dashboards/AdminDashboard.vue";
import TechnicianInboxView from "../views/dashboards/TechnicianInboxView.vue";

import { useAuthStore } from "../stores/auth.store";

const routes = [
  { path: "/login", name: "login", component: LoginView },

  // CUSTOMER: usuario normal (no staff, no superuser)
  { path: "/cliente", name: "cliente", component: ClientDashboard, meta: { role: "CUSTOMER" } },

  // AGENT: staff (soporte/técnico)
  { path: "/tecnico", name: "tecnico", component: TechnicianDashboard, meta: { role: "AGENT" } },
  { path: "/tecnico/inbox", name: "tecnico-inbox", component: TechnicianInboxView, meta: { role: "AGENT" } },

  // ADMIN: superuser
  { path: "/admin", name: "admin", component: AdminDashboard, meta: { role: "ADMIN" } },

  { path: "/", redirect: "/login" },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.beforeEach(async (to) => {
  const auth = useAuthStore();

  if (to.name === "login") return true;

  if (!auth.loaded) {
    await auth.loadMe();
  }

  if (!auth.user) return { name: "login" };

  const required = to.meta?.role;

  if (required === "ADMIN" && !auth.user.is_superuser) return auth.redirectByRole();
  if (required === "AGENT" && !auth.user.is_staff) return auth.redirectByRole();
  if (required === "CUSTOMER" && (auth.user.is_staff || auth.user.is_superuser)) {
    return auth.redirectByRole();
  }

  return true;
});

export default router;