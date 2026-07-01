<template>
  <section id="features" ref="root" class="features">
    <h2 class="title">{{ $t("nav.features") }}</h2>
    <div class="grid">
      <article v-for="f in features" :key="f.id" class="card">
        <i :class="`ti ti-${f.icon || 'sparkles'}`" aria-hidden="true"></i>
        <h3>{{ pick(f, "title") }}</h3>
        <p>{{ pick(f, "description") }}</p>
      </article>
      <p v-if="!features.length" class="empty">{{ $t("loading") }}</p>
    </div>
  </section>
</template>

<script setup>
import { ref } from "vue";
import { usePick } from "../../composables/usePick";
import { useScrollReveal } from "../../composables/useScrollReveal";

defineProps({ features: { type: Array, default: () => [] } });
const { pick } = usePick();
const root = ref(null);
useScrollReveal(() => root.value);
</script>

<style scoped>
.features { padding: 64px 0; }
.title { text-align: center; font-size: 32px; margin: 0 0 36px; }
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 18px; }
.card { padding: 24px; border: 1px solid var(--border); border-radius: var(--r-lg); background: var(--surface); }
.card i { font-size: 24px; color: var(--accent); }
.card h3 { font-size: 16px; margin: 12px 0 6px; }
.card p { color: var(--text-2); font-size: 14px; margin: 0; }
.empty { text-align: center; color: var(--text-3); grid-column: 1/-1; }
</style>
