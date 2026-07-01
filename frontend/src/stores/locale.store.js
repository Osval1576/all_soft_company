import { defineStore } from "pinia";
import { i18n } from "../i18n";

export const useLocaleStore = defineStore("locale", {
  state: () => ({ locale: i18n.global.locale.value }),
  actions: {
    setLocale(code) {
      if (code !== "es" && code !== "en") return;
      this.locale = code;
      i18n.global.locale.value = code;
      try { localStorage.setItem("locale", code); } catch (_) {}
    },
  },
});
