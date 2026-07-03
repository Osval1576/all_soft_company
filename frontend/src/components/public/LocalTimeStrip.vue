<template>
  <div class="lts" :aria-label="$t('nav.locations')">
    <template v-for="(loc, i) in items" :key="loc.id || i">
      <span v-if="i > 0" class="lts-sep">·</span>
      <span class="lts-item">
        <span class="lts-dot" aria-hidden="true"></span>
        <span class="lts-city">{{ loc.short }}</span>
        <span class="lts-time">{{ loc.time }}</span>
      </span>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, onBeforeUnmount, ref } from "vue";

const props = defineProps({
  locations: { type: Array, default: () => [] },
});

const now = ref(new Date());
let tick;

onMounted(() => { tick = setInterval(() => (now.value = new Date()), 30_000); });
onBeforeUnmount(() => tick && clearInterval(tick));

function shortLabel(name = "") {
  const s = name.trim();
  if (s.length <= 4) return s.toUpperCase();
  const parts = s.split(/[\s·,]+/).filter(Boolean);
  if (parts.length >= 2) return parts.map(p => p[0]).join("").slice(0, 3).toUpperCase();
  const stripped = s.replace(/[aeiouáéíóú\s]/gi, "");
  return stripped.slice(0, 4).toUpperCase() || s.slice(0, 4).toUpperCase();
}

function timezoneFor(loc) {
  const explicit = loc.timezone || loc.tz;
  if (explicit) return explicit;
  const lng = Number(loc.lng);
  if (!Number.isFinite(lng)) return undefined;
  if (lng <= -100) return "America/Tijuana";
  if (lng <= -95)  return "America/Mexico_City";
  if (lng <= -80)  return "America/Bogota";
  return undefined;
}

const items = computed(() =>
  props.locations
    .filter(l => l && l.name)
    .slice(0, 3)
    .map(l => {
      const tz = timezoneFor(l);
      const time = new Intl.DateTimeFormat("es-MX", {
        hour: "2-digit", minute: "2-digit", hour12: false,
        timeZone: tz,
      }).format(now.value);
      return { id: l.id, short: shortLabel(l.name), time };
    })
);
</script>

<style scoped>
.lts { display: inline-flex; align-items: center; gap: 14px; font-family: var(--font-mono); font-size: 10px; letter-spacing: 1.5px; text-transform: uppercase; color: var(--text-2); }
.lts-item { display: inline-flex; align-items: center; gap: 8px; }
.lts-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--accent); position: relative; box-shadow: 0 0 0 0 var(--accent-glow); animation: lts-pulse 2.4s ease-in-out infinite; }
[data-theme="dark"] .lts-dot { box-shadow: 0 0 8px var(--accent-glow); }
.lts-city { color: var(--text); font-weight: 500; }
.lts-time { color: var(--text-2); font-weight: 400; letter-spacing: 1px; }
.lts-sep { color: var(--border); }
@keyframes lts-pulse { 0%, 100% { box-shadow: 0 0 0 0 var(--accent-glow); } 50% { box-shadow: 0 0 0 6px transparent; } }
@media (prefers-reduced-motion: reduce) { .lts-dot { animation: none; } }
@media (max-width: 900px) { .lts { display: none; } }
</style>