<template>
  <ul class="pl">
    <li v-for="t in tickets" :key="t.id" class="pl-card">
      <div class="pl-top">
        <PriorityDot :priority="t.prioridad" />
        <span class="pl-ref">{{ t.reference }}</span>
        <span class="pl-time">{{ relativeTime(t.created_at) }}</span>
      </div>
      <p class="pl-title">{{ t.titulo }}</p>
      <p class="pl-desc">{{ (t.descripcion || "").slice(0, 140) }}{{ (t.descripcion || "").length > 140 ? "…" : "" }}</p>
      <div class="pl-actions">
        <button class="btn-take" @click="$emit('take', t)">Tomar</button>
      </div>
    </li>
    <li v-if="!tickets.length" class="pl-empty">
      No hay tickets sin asignar.
    </li>
  </ul>
</template>

<script setup>
import PriorityDot from "../PriorityDot.vue";

defineProps({
  tickets: { type: Array, default: () => [] },
});
defineEmits(["take"]);

function relativeTime(iso) {
  try {
    const then = new Date(iso).getTime();
    const now = Date.now();
    const diff = Math.max(0, now - then);
    const s = Math.floor(diff / 1000);
    if (s < 60) return "ahora";
    const m = Math.floor(s / 60);
    if (m < 60) return `${m}m`;
    const h = Math.floor(m / 60);
    if (h < 24) return `${h}h`;
    const d = Math.floor(h / 24);
    return `${d}d`;
  } catch { return iso; }
}
</script>

<style scoped>
.pl { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 8px; }
.pl-card {
  background: var(--surface);
  border: 0.5px solid var(--border);
  border-radius: var(--r);
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  transition: border-color .15s;
}
.pl-card:hover { border-color: var(--accent); }
.pl-top { display: flex; align-items: center; gap: 8px; }
.pl-ref {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 1px;
  color: var(--text-2);
}
.pl-time {
  margin-left: auto;
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 1px;
  color: var(--text-3);
}
.pl-title {
  margin: 0;
  font-family: var(--font-display);
  font-weight: 500;
  font-size: 14px;
  color: var(--text);
}
.pl-desc {
  margin: 0;
  font-size: 12px;
  color: var(--text-2);
  line-height: 1.5;
}
.pl-actions { display: flex; justify-content: flex-end; }
.btn-take {
  padding: 6px 14px;
  border-radius: 4px;
  background: var(--accent);
  color: var(--accent-fg);
  font-family: var(--font-display);
  font-size: 12px;
  font-weight: 500;
  border: none;
  cursor: pointer;
}
.btn-take:hover { background: var(--accent-hover); }
.pl-empty {
  padding: 32px 12px;
  text-align: center;
  color: var(--text-3);
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 1px;
  text-transform: uppercase;
}
</style>
