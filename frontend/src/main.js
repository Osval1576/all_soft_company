import { createApp } from "vue";
import "./style.css";
import App from "./App.vue";

import { createPinia } from "pinia";
import router from "./router";
import { i18n } from "./i18n";
import VueApexCharts from "vue3-apexcharts";
import { ensureCsrf } from "./api/http";

// Trae la cookie csrftoken antes de cualquier mutación (CN-005).
ensureCsrf();

createApp(App)
  .use(createPinia())
  .use(router)
  .use(i18n)
  .use(VueApexCharts)
  .mount("#app");
