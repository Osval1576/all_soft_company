<template>
  <header class="ph">
    <div class="ph-inner">
      <a href="#top" class="brand">
        <span class="mark">AS</span>
        <span class="name">AllSafe</span>
      </a>
      <nav class="nav">
        <a href="#features">{{ $t("nav.features") }}</a>
        <a href="#about">{{ $t("nav.about") }}</a>
        <a href="#locations">{{ $t("nav.locations") }}</a>
        <a href="#contacto">{{ $t("nav.contact") }}</a>
      </nav>
      <div class="actions">
        <button class="lang" @click="toggle">{{ locale === "es" ? "ES" : "EN" }}</button>
        <router-link to="/login" class="btn-signin">{{ $t("nav.signin") }}</router-link>
      </div>
    </div>
  </header>
</template>

<script setup>
import { useLocaleStore } from "../../stores/locale.store";
import { storeToRefs } from "pinia";
const store = useLocaleStore();
const { locale } = storeToRefs(store);
function toggle() { store.setLocale(locale.value === "es" ? "en" : "es"); }
</script>

<style scoped>
.ph { position: sticky; top: 0; background: var(--surface); border-bottom: 1px solid var(--border); z-index: 50; }
.ph-inner { max-width: 1180px; margin: 0 auto; padding: 14px 24px; display: flex; align-items: center; justify-content: space-between; }
.brand { display: flex; align-items: center; gap: 10px; text-decoration: none; color: var(--text); }
.mark { width: 32px; height: 32px; background: var(--accent); color: var(--accent-fg); border-radius: 8px; display: grid; place-items: center; font-weight: 700; font-size: 12px; }
.name { font-weight: 600; font-size: 15px; }
.nav { display: flex; gap: 28px; }
.nav a { color: var(--text-2); text-decoration: none; font-size: 14px; }
.nav a:hover { color: var(--text); }
.actions { display: flex; align-items: center; gap: 12px; }
.lang { border: 1px solid var(--border); padding: 6px 10px; border-radius: var(--r-sm); background: transparent; color: var(--text-2); font-size: 12px; }
.btn-signin { background: var(--accent); color: var(--accent-fg); padding: 8px 16px; border-radius: var(--r); font-size: 13px; font-weight: 600; text-decoration: none; }
</style>
