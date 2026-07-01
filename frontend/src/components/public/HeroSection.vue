<template>
  <section ref="root" class="hero">
    <h1 class="title">{{ pick(hero, "title") || "AllSafe" }}</h1>
    <p class="subtitle">{{ pick(hero, "subtitle") }}</p>
    <div class="ctas">
      <a :href="hero?.primary_cta_url || '/login'" class="cta primary">
        {{ pick(hero, "primary_cta_label") || $t("nav.signin") }}
      </a>
      <a :href="hero?.secondary_cta_url || '#contacto'" class="cta ghost">
        {{ pick(hero, "secondary_cta_label") }}
      </a>
    </div>
  </section>
</template>

<script setup>
import { ref } from "vue";
import { usePick } from "../../composables/usePick";
import { useScrollReveal } from "../../composables/useScrollReveal";

defineProps({ hero: { type: Object, default: null } });

const { pick } = usePick();
const root = ref(null);
useScrollReveal(() => root.value);
</script>

<style scoped>
.hero { padding: 96px 0 64px; text-align: center; }
.title { font-size: clamp(36px, 6vw, 64px); font-weight: 700; letter-spacing: -0.02em; margin: 0 0 16px; }
.subtitle { font-size: 18px; color: var(--text-2); max-width: 640px; margin: 0 auto 28px; }
.ctas { display: flex; justify-content: center; gap: 12px; }
.cta { padding: 12px 22px; border-radius: var(--r); font-weight: 600; font-size: 14px; text-decoration: none; transition: opacity .15s; }
.cta.primary { background: var(--accent); color: var(--accent-fg); }
.cta.ghost { border: 1px solid var(--border); color: var(--text); }
.cta:hover { opacity: .9; }
</style>
