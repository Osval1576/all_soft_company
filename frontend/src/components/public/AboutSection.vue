<template>
  <section id="about" ref="root" class="about">
    <div class="about-inner">
      <p class="eyebrow">{{ $t("nav.about") }}</p>

      <div class="about-grid">
        <div>
          <h2 class="lead">
            <span>Estamos para tu equipo</span>
            <span class="lead-accent"> cuando algo se rompe.</span>
            <br />
            <span>Y también antes.</span>
          </h2>
          <p v-if="pick(about, 'mission')" class="body">
            {{ pick(about, "mission") }}
          </p>
        </div>

        <div class="pillars">
          <article v-if="pick(about, 'mission')" class="pillar">
            <span class="pillar-label">Misión</span>
            <p class="pillar-body">{{ pick(about, "mission") }}</p>
          </article>
          <article v-if="pick(about, 'vision')" class="pillar">
            <span class="pillar-label">Visión</span>
            <p class="pillar-body">{{ pick(about, "vision") }}</p>
          </article>
          <article v-if="pick(about, 'values')" class="pillar">
            <span class="pillar-label">Valores</span>
            <p class="pillar-body">{{ pick(about, "values") }}</p>
          </article>
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
.about {
  border-top: 0.5px solid var(--border);
  padding: 96px 32px 80px;
}
.about-inner { max-width: 1240px; margin: 0 auto; }

.eyebrow {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: var(--text-3);
  margin: 0 0 40px;
}

.about-grid {
  display: grid;
  grid-template-columns: 1.3fr 1fr;
  gap: 80px;
  align-items: start;
  margin-bottom: 72px;
}

.lead {
  font-family: var(--font-display);
  font-weight: 500;
  font-size: clamp(28px, 4vw, 48px);
  line-height: 1.08;
  letter-spacing: -0.02em;
  margin: 0;
  color: var(--text);
}
.lead-accent { color: var(--accent); }
[data-theme="dark"] .lead-accent { color: var(--accent-2); }

.body {
  margin: 24px 0 0;
  font-size: 16px;
  color: var(--text-2);
  line-height: 1.7;
  max-width: 500px;
}

.pillars { display: flex; flex-direction: column; gap: 4px; }
.pillar {
  border-top: 0.5px solid var(--border);
  padding: 18px 0 6px;
}
.pillar:last-child { border-bottom: 0.5px solid var(--border); padding-bottom: 20px; }

.pillar-label {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: var(--accent);
  display: inline-block;
  margin-bottom: 8px;
}
[data-theme="dark"] .pillar-label { color: var(--accent-2); }

.pillar-body {
  font-size: 14px;
  color: var(--text-2);
  line-height: 1.6;
  margin: 0;
}

.team {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 24px;
  padding-top: 40px;
  border-top: 0.5px solid var(--border);
}
.member { text-align: left; }
.member img, .member .avatar {
  width: 68px;
  height: 68px;
  border-radius: 4px;
  margin: 0 0 10px;
  display: block;
  object-fit: cover;
}
.member .avatar {
  background: var(--surface-2);
  display: grid;
  place-items: center;
  font-family: var(--font-display);
  font-weight: 500;
  font-size: 20px;
  color: var(--text-2);
  letter-spacing: -0.02em;
}
.name {
  font-family: var(--font-display);
  font-weight: 500;
  font-size: 14px;
  color: var(--text);
  margin: 0;
}
.role {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: var(--text-3);
  margin: 4px 0 0;
}

@media (max-width: 800px) {
  .about { padding: 56px 20px 48px; }
  .about-grid { grid-template-columns: 1fr; gap: 32px; }
  .team { grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 16px; }
}
</style>
