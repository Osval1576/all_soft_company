import { createApp } from "vue";
import "./style.css";
import App from "./App.vue";

import { createPinia } from "pinia";
import router from "./router";
import { i18n } from "./i18n";

createApp(App)
  .use(createPinia())
  .use(router)
  .use(i18n)
  .mount("#app");
  