<template>
  <div class="landing">
    <section v-if="!store.loaded" class="skeleton">
      <div class="sk" style="height:360px"></div>
      <div class="sk" style="height:200px"></div>
      <div class="sk" style="height:300px"></div>
    </section>

    <template v-else>
      <HeroSection :hero="store.hero" />
      <FeaturesSection :features="store.features" />
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
import FeaturesSection from "../../components/public/FeaturesSection.vue";
import AboutSection from "../../components/public/AboutSection.vue";
import LocationsSection from "../../components/public/LocationsSection.vue";
import ContactSection from "../../components/public/ContactSection.vue";

const store = useLandingStore();
onMounted(() => { if (!store.loaded) store.loadAll(); });
</script>

<style scoped>
.landing { max-width: 1180px; margin: 0 auto; padding: 32px 24px; }
.skeleton { display: flex; flex-direction: column; gap: 24px; }
.sk { background: var(--surface-2); border-radius: var(--r-lg); }
</style>
