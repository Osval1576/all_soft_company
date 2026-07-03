<template>
  <section class="tet">
    <header class="tet-head" @click="open = !open" role="button" :aria-expanded="open">
      <span class="tet-title">Historial</span>
      <span class="tet-count">{{ events.length }} eventos</span>
      <i :class="open ? 'ti ti-chevron-up' : 'ti ti-chevron-down'" aria-hidden="true"></i>
    </header>

    <ol v-if="open" class="tet-list">
      <li v-for="e in events" :key="e.id" class="tet-item">
        <span class="tet-icon"><i :class="iconFor(e.kind)" aria-hidden="true"></i></span>
        <div class="tet-body">
          <p class="tet-text">{{ label(e) }}</p>
          <p class="tet-time">{{ relativeTime(e.created_at) }}</p>
        </div>
      </li>
      <li v-if="!events.length" class="tet-empty">Sin eventos.</li>
    </ol>
  </section>
</template>

<script setup>
import { ref } from "vue";

defineProps({
  events: { type: Array, default: () => [] },
});

const open = ref(false);

const ICON = {
  created: "ti ti-star",
  assigned: "ti ti-user-check",
  unassigned: "ti ti-user-x",
  status_changed: "ti ti-arrow-right",
  reopened: "ti ti-refresh",
  priority_changed: "ti ti-flag",
};

function iconFor(kind) { return ICON[kind] || "ti ti-circle"; }

function label(e) {
  const who = e.actor_username || "Sistema";
  const p = e.payload || {};
  switch (e.kind) {
    case "created": return `${who} creó el ticket`;
    case "assigned": return `${who} asignó el ticket${p.self_take ? " (se lo tomó)" : ""}`;
    case "unassigned": return `${who} desasignó el ticket`;
    case "status_changed": return `${who} cambió estado: ${p.from} → ${p.to}`;
    case "reopened": return `${who} reabrió el ticket`;
    case "priority_changed": return `${who} cambió prioridad: ${p.from} → ${p.to}`;
    default: return `${who} · ${e.kind}`;
  }
}

function relativeTime(iso) {
  try {
    const then = new Date(iso).getTime();
    const now = Date.now();
    const diff = Math.max(0, now - then);
    const s = Math.floor(diff / 1000);
    if (s < 60) return "hace un momento";
    const m = Math.floor(s / 60);
    if (m < 60) return `hace ${m} min`;
    const h = Math.floor(m / 60);
    if (h < 24) return `hace ${h} h`;
    const d = Math.floor(h / 24);
    return `hace ${d} d`;
  } catch { return iso; }
}
</script>

<style scoped>
.tet {
  border-top: 0.5px solid var(--border);
  padding: 12px 16px 16px;
  background: var(--bg);
}
.tet-head {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: var(--text-3);
  padding: 6px 0;
}
.tet-title { color: var(--text-2); }
.tet-count { color: var(--text-3); }
.tet-head i { margin-left: auto; font-size: 14px; }

.tet-list { list-style: none; margin: 12px 0 0; padding: 0; display: flex; flex-direction: column; gap: 10px; }
.tet-item { display: flex; gap: 10px; align-items: flex-start; }
.tet-icon {
  width: 22px; height: 22px;
  border-radius: 4px;
  background: var(--surface-2);
  color: var(--accent);
  display: grid; place-items: center;
  flex-shrink: 0;
}
[data-theme="dark"] .tet-icon { color: var(--accent-2); }
.tet-icon i { font-size: 12px; }
.tet-body { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.tet-text {
  margin: 0;
  font-family: var(--font-body);
  font-size: 13px;
  color: var(--text);
  line-height: 1.4;
}
.tet-time {
  margin: 0;
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 1px;
  color: var(--text-3);
}
.tet-empty {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 1px;
  color: var(--text-3);
  text-transform: uppercase;
}
</style>
