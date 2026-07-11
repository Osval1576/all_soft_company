<!-- frontend/src/components/metrics/SlaGauge.vue -->
<template>
  <div class="gauge">
    <span class="gauge-label">{{ label }}</span>
    <apexchart v-if="value !== null" type="radialBar" height="180" :options="opts" :series="[Math.round(value * 100)]" />
    <div v-else class="gauge-empty">—</div>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { baseOptions, chartColors } from "../../theme/apexTheme.js";

const props = defineProps({ label: String, value: { type: Number, default: null } });

const opts = computed(() => {
  const c = chartColors();
  const color = props.value >= 0.9 ? c.good : props.value >= 0.75 ? c.warn : c.bad;
  return {
    ...baseOptions(),
    colors: [color],
    plotOptions: { radialBar: {
      hollow: { size: "58%" },
      track: { background: c.grid },
      dataLabels: { name: { show: false },
        value: { fontFamily: "JetBrains Mono, monospace", fontSize: "22px", color: c.text,
                 formatter: (v) => `${v}%` } },
    } },
  };
});
</script>

<style scoped>
.gauge { background: var(--surface); border: 0.5px solid var(--border); border-radius: var(--r);
         padding: 14px; display: flex; flex-direction: column; align-items: center; }
.gauge-label { font-family: var(--font-mono); font-size: 11px; text-transform: uppercase;
               letter-spacing: 1px; color: var(--text-3); margin-bottom: 4px; }
.gauge-empty { font-family: var(--font-display); font-size: 32px; color: var(--text-3); padding: 60px 0; }
</style>
