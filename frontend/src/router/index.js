import { createRouter, createWebHistory } from "vue-router";

import PublicLayout from "../layouts/PublicLayout.vue";
import AdminLayout from "../layouts/AdminLayout.vue";

import LoginView from "../views/LoginView.vue";
import LandingHome from "../views/public/LandingHome.vue";

import ClientDashboard from "../views/dashboards/ClientDashboard.vue";
import TechnicianDashboard from "../views/dashboards/TechnicianDashboard.vue";
import AdminDashboard from "../views/dashboards/AdminDashboard.vue";
import TechnicianInboxView from "../views/dashboards/TechnicianInboxView.vue";

import AdminContent from "../views/admin/site/AdminContent.vue";
import AdminTeam from "../views/admin/site/AdminTeam.vue";
import AdminLocations from "../views/admin/site/AdminLocations.vue";
import NotificationSettings from "../views/settings/NotificationSettings.vue";

import { useAuthStore } from "../stores/auth.store";

const routes = [
  {
    path: "/",
    component: PublicLayout,
    children: [
      { path: "", name: "landing", component: LandingHome, meta: { public: true } },
      { path: "login", name: "login", component: LoginView, meta: { public: true } },
    ],
  },
  { path: "/cliente", name: "cliente", component: ClientDashboard, meta: { role: "CUSTOMER" } },
  { path: "/tecnico", name: "tecnico", component: TechnicianDashboard, meta: { role: "AGENT" } },
  { path: "/tecnico/inbox", name: "tecnico-inbox", component: TechnicianInboxView, meta: { role: "AGENT" } },
  { path: "/admin", name: "admin", component: AdminDashboard, meta: { role: "ADMIN" } },
  { path: "/ajustes/notificaciones", name: "notif-settings", component: NotificationSettings, meta: { authed: true } },
  {
    path: "/admin/sitio",
    component: AdminLayout,
    children: [
      { path: "contenido", name: "admin-content", component: AdminContent, meta: { role: "ADMIN" } },
      { path: "equipo", name: "admin-team", component: AdminTeam, meta: { role: "ADMIN" } },
      { path: "ubicaciones", name: "admin-locations", component: AdminLocations, meta: { role: "ADMIN" } },
    ],
  },
];

const router = createRouter({ history: createWebHistory(), routes });

router.beforeEach(async (to) => {
  const auth = useAuthStore();
  if (to.meta?.public) return true;
  if (to.name === "login") return true;

  if (!auth.loaded) await auth.loadMe();
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
