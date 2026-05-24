import { defineStore } from "pinia";
import { http } from "../api/http";
import router from "../router";

export const useAuthStore = defineStore("auth", {
  state: () => ({
    user: null,
    loaded: false,
  }),

  actions: {
    async loadMe() {
  try {
    const res = await http.get("/api/me/");
    this.user = res.data;
  } catch (e) {
    this.user = null;   // importante
  } finally {
    this.loaded = true; // importante
  }
},

redirectByRole() {
  if (this.user?.is_superuser) return { name: "admin" };
  if (this.user?.is_staff) return { name: "tecnico-inbox" };
  return { name: "cliente" };
},

    async login(username, password) {
      await http.post("/api/auth/login-cookie/", { username, password });
      this.loaded = false;
      await this.loadMe();
      return router.push(this.redirectByRole());
    },

    async logout() {
      try {
        await http.post("/api/auth/logout/");
      } finally {
        this.user = null;
        this.loaded = true;
        router.push({ name: "login" });
      }
    },
  },
});