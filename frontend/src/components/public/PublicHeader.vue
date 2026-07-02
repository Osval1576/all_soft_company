<template>
  <header class="ph">
    <div class="ph-inner">
      <router-link to="/" class="brand" aria-label="AllSafe">
        <span class="mark">AS</span>
        <span class="name">AllSafe</span>
      </router-link>

      <LocalTimeStrip :locations="locations" />

      <div class="actions">
        <button class="lang" @click="toggleLocale" aria-label="switch language">
          <span :class="{ on: locale === 'es' }">ES</span>
          <span class="dot">·</span>
          <span :class="{ on: locale === 'en' }">EN</span>
        </button>
        <button class="theme" @click="toggle" :aria-label="isDark ? 'switch to light' : 'switch to dark'">
          <i :class="isDark ? 'ti ti-sun' : 'ti ti-moon'" aria-hidden="true"></i>
        </button>
        <router-link to="/login" class="btn-enter">
          <span>{{ $t("nav.signin") }}</span>
        </router-link>
      </div>
    </div>
  </header>
</template>

<script setup>
import { computed } from "vue";
import { storeToRefs } from "pinia";
import { useLocaleStore } from "../../stores/locale.store";
import { useLandingStore } from "../../stores/landing.store";
import { useTheme } from "../../composables/useTheme";
import LocalTimeStrip from "./LocalTimeStrip.vue";

const localeStore = useLocaleStore();
const { locale } = storeToRefs(localeStore);
const { isDark, toggle } = useTheme();

const landingStore = useLandingStore();
const locations = computed(() => landingStore.locations || []);

function toggleLocale() {
  localeStore.setLocale(locale.value === "es" ? "en" : "es");
}
</script>

<style scoped>
.ph {
  position: sticky;
  top: 0;
  z-index: 50;
  background: color-mix(in srgb, var(--bg) 85%, transparent);
  backdrop-filter: saturate(140%) blur(10px);
  -webkit-backdrop-filter: saturate(140%) blur(10px);
  border-bottom: 0.5px solid var(--border);
}
.ph-inner {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 24px;
  max-width: 1240px;
  margin: 0 auto;
  padding: 16px 32px;
}
.brand {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  color: var(--text);
  text-decoration: none;
}
.mark {
  width: 24px;
  height: 24px;
  background: var(--accent);
  color: var(--accent-fg);
  border-radius: 5px;
  display: grid;
  place-items: center;
  font-family: var(--font-display);
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.5px;
}
.name {
  font-family: var(--font-display);
  font-size: 15px;
  font-weight: 600;
  letter-spacing: -0.01em;
}
.actions {
  display: inline-flex;
  align-items: center;
  gap: 12px;
}
.lang {
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 1px;
  color: var(--text-3);
  padding: 6px 4px;
  background: transparent;
  border: none;
  cursor: pointer;
}
.lang .on { color: var(--text); }
.lang .dot { margin: 0 4px; color: var(--border); }
.theme {
  width: 32px;
  height: 32px;
  border: 0.5px solid var(--border);
  border-radius: 6px;
  display: grid;
  place-items: center;
  color: var(--text-2);
  background: transparent;
  cursor: pointer;
  transition: background .15s, color .15s, border-color .15s;
}
.theme:hover { background: var(--surface-2); color: var(--text); border-color: var(--text-3); }
.theme i { font-size: 14px; }
.btn-enter {
  position: relative;
  overflow: hidden;
  background: var(--accent);
  color: var(--accent-fg);
  padding: 9px 20px;
  border-radius: 6px;
  font-family: var(--font-display);
  font-size: 13px;
  font-weight: 500;
  letter-spacing: 0.2px;
  text-decoration: none;
  box-shadow: 0 6px 20px -8px var(--accent-glow);
  transition: transform .12s, box-shadow .15s;
}
.btn-enter:hover { transform: translateY(-1px); box-shadow: 0 10px 26px -8px var(--accent-glow); }
.btn-enter:active { transform: translateY(0); }
.btn-enter::before {
  content: "";
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.25), transparent);
  transform: translateX(-100%);
  animation: sweep 4s ease-in-out infinite;
  animation-delay: 1.5s;
}
@keyframes sweep {
  0% { transform: translateX(-100%); }
  40%, 100% { transform: translateX(200%); }
}
@media (prefers-reduced-motion: reduce) {
  .btn-enter::before { animation: none; }
}
@media (max-width: 700px) {
  .ph-inner { grid-template-columns: auto auto; }
  .actions { justify-content: flex-end; }
}
</style>
