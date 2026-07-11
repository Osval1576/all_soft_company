<!-- frontend/src/components/metrics/MetricTile.vue -->
<template>
  <div class="tile">
    <span class="tile-label">{{ label }}</span>
    <span class="tile-value">{{ value }}</span>
    <span v-if="hint" class="tile-hint">{{ hint }}</span>
  </div>
</template>

<script setup>
defineProps({ label: String, value: [String, Number], hint: String });
</script>

<style scoped>
.tile { background: var(--surface); border: 0.5px solid var(--border); border-radius: var(--r);
        padding: 16px 18px; display: flex; flex-direction: column; gap: 4px; }
.tile-label { font-family: var(--font-mono); font-size: 11px; text-transform: uppercase;
              letter-spacing: 1px; color: var(--text-3); }
.tile-value { font-family: var(--font-display); font-size: 28px; font-weight: 600; color: var(--text); }
.tile-hint { font-size: 12px; color: var(--text-2); }
</style>
