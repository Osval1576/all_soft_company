import { createApp } from "vue";
import "./style.css";
import App from "./App.vue";

import { createPinia } from "pinia";
import router from "./router";
import { i18n } from "./i18n";
import VueApexCharts from "vue3-apexcharts";

createApp(App)
  .use(createPinia())
  .use(router)
  .use(i18n)
  .use(VueApexCharts)
  .mount("#app");
