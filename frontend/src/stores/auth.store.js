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
      } catch {
        this.user = null;
      } finally {
        this.loaded = true;
      }
    },

    redirectByRole() {
      const r = this.user?.role;
      if (r === "ADMIN") return { name: "admin" };
      if (r === "AGENT") return { name: "tecnico-inbox" };
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