import { createRouter, createWebHistory } from "vue-router";
import LoginView from "../views/LoginView.vue";
import ClientDashboard from "../views/dashboards/ClientDashboard.vue";
import TechnicianDashboard from "../views/dashboards/TechnicianDashboard.vue";
import AdminDashboard from "../views/dashboards/AdminDashboard.vue";
import { useAuthStore } from "../stores/auth.store";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/login", name: "login", component: LoginView },

    { path: "/cliente", name: "cliente", component: ClientDashboard, meta: { role: "CUSTOMER" } },
    { path: "/tecnico", name: "tecnico", component: TechnicianDashboard, meta: { role: "AGENT" } },
    { path: "/admin", name: "admin", component: AdminDashboard, meta: { role: "ADMIN" } },

    { path: "/", redirect: "/login" },
  ],
});

router.beforeEach(async (to) => {
  const auth = useAuthStore();

  if (to.name === "login") return true;

  if (!auth.loaded) {
    await auth.loadMe(); // llama /api/me/ usando cookie
  }

  if (!auth.user) return { name: "login" };

  if (to.meta?.role && auth.user.role !== to.meta.role) {
    // redirige al dashboard correcto
    return auth.redirectByRole();
  }

  return true;
});

export default router;