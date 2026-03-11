import { defineStore } from "pinia";
import { me } from "../api/auth.api";
import router from "../router";

export const useAuthStore = defineStore("auth", {
  state: () => ({
    user: null,
    loaded: false,
  }),
  actions: {
    async loadMe() {
      try {
        this.user = await me();
      } catch {
        this.user = null;
      } finally {
        this.loaded = true;
      }
    },
    redirectByRole() {
      const role = this.user?.role;
      if (role === "ADMIN") return { name: "admin" };
      if (role === "AGENT") return { name: "tecnico" };
      return { name: "cliente" };
    },
  },
});