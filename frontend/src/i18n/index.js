import { createI18n } from "vue-i18n";
import es from "./locales/es.json";
import en from "./locales/en.json";

const saved = typeof localStorage !== "undefined" ? localStorage.getItem("locale") : null;

export const i18n = createI18n({
  legacy: false,
  locale: saved || "es",
  fallbackLocale: "es",
  messages: { es, en },
});
