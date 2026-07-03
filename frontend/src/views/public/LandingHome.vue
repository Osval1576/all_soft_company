<template>
  <div class="landing">
    <section v-if="!store.loaded" class="skeleton" aria-hidden="true">
      <div class="sk sk-hero"></div>
      <div class="sk sk-about"></div>
      <div class="sk sk-map"></div>
    </section>

    <template v-else>
      <HeroSection :hero="store.hero" />
      <AboutSection :about="store.about" :team="store.team" />
      <LocationsSection :locations="store.locations" :settings="store.settings" />
      <ContactSection />
    </template>
  </div>
</template>

<script setup>
import { onMounted } from "vue";
import { useLandingStore } from "../../stores/landing.store";

import HeroSection from "../../components/public/HeroSection.vue";
import AboutSection from "../../components/public/AboutSection.vue";
import LocationsSection from "../../components/public/LocationsSection.vue";
import ContactSection from "../../components/public/ContactSection.vue";

const store = useLandingStore();
onMounted(() => { if (!store.loaded) store.loadAll(); });
</script>

<style scoped>
.landing { min-height: 100vh; }

.skeleton {
  max-width: 1240px;
  margin: 0 auto;
  padding: 48px 32px;
  display: flex;
  flex-direction: column;
  gap: 24px;
}
.sk {
  border-radius: var(--r-lg);
  background: linear-gradient(90deg, var(--surface-2), var(--surface), var(--surface-2));
  background-size: 200% 100%;
  animation: sk-shimmer 1.6s linear infinite;
}
.sk-hero { height: 420px; }
.sk-about { height: 260px; }
.sk-map { height: 380px; }
@keyframes sk-shimmer {
  0% { background-position: 100% 0; }
  100% { background-position: -100% 0; }
}
@media (prefers-reduced-motion: reduce) {
  .sk { animation: none; }
}
</style>
