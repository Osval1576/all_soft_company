<template>
  <section ref="root" class="hero" @mousemove="onMove" @mouseleave="onLeave">
    <div class="hero-grid" aria-hidden="true"></div>
    <div class="hero-spot" aria-hidden="true"></div>

    <div class="hero-body">
      <div class="hero-copy">
        <h1 class="title">
          <template v-if="parts.length">
            <span v-for="(line, i) in parts.slice(0, -1)" :key="i" class="line">{{ line }}<br /></span>
            <span class="line accent">{{ parts[parts.length - 1] }}</span>
          </template>
          <template v-else>
            <span class="line">Pasá.</span><br />
            <span class="line">El tablero</span><br />
            <span class="line accent">está adentro.</span>
          </template>
        </h1>
        <p class="subtitle">
          {{ pick(hero, "subtitle") || "Tu equipo también. Iniciá sesión y seguimos donde quedamos." }}
        </p>
      </div>

      <div class="hero-ctas">
        <router-link :to="{ path: hero?.primary_cta_url || '/login' }" class="cta primary">
          <span>{{ pick(hero, "primary_cta_label") || $t("nav.signin") }}</span>
          <span class="arrow" aria-hidden="true">→</span>
        </router-link>
        <a :href="hero?.secondary_cta_url || '#contacto'" class="cta ghost">
          {{ pick(hero, "secondary_cta_label") || "o hablanos primero" }}
        </a>
      </div>
    </div>

    <div class="hero-scroll">
      <span>scroll ↓ nosotros · dónde estamos · contacto</span>
      <span class="mono-mark">hecho con calma</span>
    </div>
  </section>
</template>

<script setup>
import { computed, ref } from "vue";
import { usePick } from "../../composables/usePick";
import { useScrollReveal } from "../../composables/useScrollReveal";

const props = defineProps({ hero: { type: Object, default: null } });

const { pick } = usePick();
const root = ref(null);
useScrollReveal(() => root.value);

const reduced = typeof window !== "undefined" &&
  window.matchMedia("(prefers-reduced-motion: reduce)").matches;

function onMove(e) {
  if (reduced || !root.value) return;
  const r = root.value.getBoundingClientRect();
  const x = ((e.clientX - r.left) / r.width) * 100;
  const y = ((e.clientY - r.top) / r.height) * 100;
  root.value.style.setProperty("--mx", `${x}%`);
  root.value.style.setProperty("--my", `${y}%`);
}
function onLeave() {
  if (!root.value) return;
  root.value.style.setProperty("--mx", "50%");
  root.value.style.setProperty("--my", "20%");
}

const parts = computed(() => {
  const title = pick(props.hero, "title") || "";
  if (!title.trim()) return [];
  return title.split(/\n|<br\s*\/?>/i).map(s => s.trim()).filter(Boolean);
});
</script>

<style scoped>
.hero {
  position: relative;
  overflow: hidden;
  padding: 96px 32px 72px;
  --mx: 50%;
  --my: 20%;
}

.hero-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(var(--accent-light) 0.5px, transparent 0.5px),
    linear-gradient(90deg, var(--accent-light) 0.5px, transparent 0.5px);
  background-size: 40px 40px;
  mask-image: radial-gradient(ellipse at 50% 30%, black 40%, transparent 80%);
  -webkit-mask-image: radial-gradient(ellipse at 50% 30%, black 40%, transparent 80%);
  pointer-events: none;
  z-index: 0;
}

.hero-spot {
  position: absolute;
  inset: 0;
  background: radial-gradient(
    600px circle at var(--mx) var(--my),
    var(--accent-glow),
    transparent 55%
  );
  opacity: 0.6;
  pointer-events: none;
  z-index: 1;
  transition: background .18s ease-out;
}
[data-theme="dark"] .hero-spot { opacity: 0.85; }

.hero-body {
  position: relative;
  z-index: 2;
  max-width: 1240px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 1.5fr 1fr;
  gap: 40px;
  align-items: end;
  padding-top: 64px;
  padding-bottom: 40px;
}

.title {
  font-family: var(--font-display);
  font-weight: 500;
  font-size: clamp(48px, 9vw, 116px);
  line-height: 0.92;
  letter-spacing: -0.045em;
  color: var(--text);
  margin: 0;
}
.title .line { display: inline; }
.title .accent { color: var(--accent); }
[data-theme="dark"] .title .accent { color: var(--accent-2); }

.subtitle {
  font-family: var(--font-body);
  font-size: clamp(16px, 1.6vw, 20px);
  color: var(--text-2);
  line-height: 1.55;
  max-width: 480px;
  margin: 28px 0 0;
}

.hero-ctas {
  display: flex;
  flex-direction: column;
  gap: 16px;
  align-items: flex-end;
}

.cta {
  font-family: var(--font-display);
  text-decoration: none;
  font-weight: 500;
  transition: transform .12s ease-out, box-shadow .15s;
}

.cta.primary {
  position: relative;
  overflow: hidden;
  display: inline-flex;
  align-items: center;
  gap: 10px;
  background: var(--accent);
  color: var(--accent-fg);
  padding: 15px 26px;
  border-radius: 6px;
  font-size: 15px;
  letter-spacing: 0.2px;
  box-shadow: 0 12px 32px -12px var(--accent-glow);
}
.cta.primary:hover { transform: translateY(-1px); box-shadow: 0 16px 36px -10px var(--accent-glow); }
.cta.primary .arrow { transition: transform .18s; }
.cta.primary:hover .arrow { transform: translateX(3px); }
.cta.primary::before {
  content: "";
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.28), transparent);
  transform: translateX(-100%);
  animation: hero-sweep 4s ease-in-out infinite;
  animation-delay: 2s;
}
@keyframes hero-sweep {
  0% { transform: translateX(-100%); }
  35%, 100% { transform: translateX(220%); }
}

.cta.ghost {
  position: relative;
  color: var(--accent);
  font-size: 13px;
  padding: 4px 2px 6px;
}
[data-theme="dark"] .cta.ghost { color: var(--accent-2); }
.cta.ghost::after {
  content: "";
  position: absolute;
  left: 2px;
  right: 2px;
  bottom: 0;
  height: 1px;
  background: linear-gradient(90deg, currentColor 50%, transparent 50%);
  background-size: 200% 100%;
  background-position: 100% 0;
  animation: ghost-underline 2.4s ease-in-out infinite;
}
@keyframes ghost-underline {
  0%, 100% { background-position: 100% 0; }
  50% { background-position: 0 0; }
}

.hero-scroll {
  position: relative;
  z-index: 2;
  max-width: 1240px;
  margin: 32px auto 0;
  padding: 20px 0 4px;
  border-top: 0.5px solid var(--border);
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: var(--text-3);
  display: flex;
  justify-content: space-between;
  gap: 16px;
}
.mono-mark { color: var(--text-2); }

@media (prefers-reduced-motion: reduce) {
  .cta.primary::before { animation: none; }
  .cta.ghost::after { animation: none; background: currentColor; }
  .hero-spot { transition: none; }
}

@media (max-width: 800px) {
  .hero-body { grid-template-columns: 1fr; gap: 32px; align-items: start; padding-top: 24px; }
  .hero-ctas { align-items: flex-start; }
  .hero-scroll { padding-top: 16px; font-size: 9px; letter-spacing: 1.5px; flex-wrap: wrap; }
  .hero { padding: 48px 20px 40px; }
}
</style>
