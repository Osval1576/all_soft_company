<template>
  <div v-if="sla" class="sla" :class="{ 'sla--compact': compact }">
    <span class="sla-clock" :title="`Primera respuesta: ${labelFor(sla.first_response)}`">
      <span class="sla-dot" :class="`sla-dot--${sla.first_response.level}`"></span>
      <span v-if="!compact" class="sla-txt">1ª resp</span>
    </span>
    <span class="sla-clock" :title="`Resolución: ${labelFor(sla.resolution)}`">
      <span class="sla-dot" :class="`sla-dot--${sla.resolution.level}`"></span>
      <span v-if="!compact" class="sla-txt">Resol</span>
    </span>
  </div>
</template>

<script setup>
const props = defineProps({
  sla: { type: Object, default: null },
  compact: { type: Boolean, default: false },
});

const LABELS = { ok: "en tiempo", at_risk: "en riesgo", breached: "vencido", met: "cumplido" };

function labelFor(clock) {
  if (!clock) return "—";
  const base = LABELS[clock.level] || clock.level;
  if (clock.level === "met" || !clock.due_at) return base;
  const due = new Date(clock.due_at);
  const now = new Date();
  const mins = Math.round((due - now) / 60000);
  if (clock.level === "breached") return `${base}`;
  const h = Math.floor(Math.abs(mins) / 60);
  const m = Math.abs(mins) % 60;
  return `${base} · vence en ${h}h ${m}m`;
}
</script>

<style scoped>
.sla { display: inline-flex; gap: 10px; align-items: center; }
.sla-clock { display: inline-flex; align-items: center; gap: 5px; }
.sla-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--text-3); }
.sla-dot--ok { background: var(--c-resolved, #10B981); }
.sla-dot--at_risk { background: var(--c-open, #F59E0B); }
.sla-dot--breached { background: var(--c-urgent, #EF4444); }
.sla-dot--met { background: var(--text-3); }
.sla-txt {
  font-family: var(--font-mono); font-size: 9px; letter-spacing: 1px;
  text-transform: uppercase; color: var(--text-3);
}
</style>
