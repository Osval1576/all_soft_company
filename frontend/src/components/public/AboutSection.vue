<template>
  <section id="about" ref="root" class="about">
    <h2 class="title">{{ $t("nav.about") }}</h2>
    <div class="mv">
      <div class="card">
        <h3>Misión</h3>
        <p>{{ pick(about, "mission") }}</p>
      </div>
      <div class="card">
        <h3>Visión</h3>
        <p>{{ pick(about, "vision") }}</p>
      </div>
    </div>
    <div v-if="team.length" class="team">
      <article v-for="m in team" :key="m.id" class="member">
        <img v-if="m.photo" :src="m.photo" :alt="m.name" />
        <div v-else class="avatar">{{ initials(m.name) }}</div>
        <p class="name">{{ m.name }}</p>
        <p class="role">{{ pick(m, "role") }}</p>
      </article>
    </div>
  </section>
</template>

<script setup>
import { ref } from "vue";
import { usePick } from "../../composables/usePick";
import { useScrollReveal } from "../../composables/useScrollReveal";

defineProps({
  about: { type: Object, default: null },
  team: { type: Array, default: () => [] },
});

const { pick } = usePick();
const root = ref(null);
useScrollReveal(() => root.value);

function initials(name = "") {
  return name.split(/\s+/).slice(0, 2).map(s => s[0] || "").join("").toUpperCase();
}
</script>

<style scoped>
.about { padding: 64px 0; }
.title { text-align: center; font-size: 32px; margin: 0 0 36px; }
.mv { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 18px; margin-bottom: 48px; }
.card { padding: 28px; border-radius: var(--r-lg); background: var(--surface); border: 1px solid var(--border); }
.card h3 { margin: 0 0 10px; font-size: 16px; }
.card p { color: var(--text-2); margin: 0; line-height: 1.6; }
.team { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 16px; }
.member { text-align: center; }
.member img, .member .avatar { width: 72px; height: 72px; border-radius: 50%; margin: 0 auto 8px; display: block; object-fit: cover; }
.member .avatar { background: var(--surface-2); display: grid; place-items: center; font-weight: 600; color: var(--text-2); }
.name { font-weight: 600; margin: 0; font-size: 14px; }
.role { color: var(--text-3); margin: 2px 0 0; font-size: 12px; }
</style>
