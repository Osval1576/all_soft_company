<!-- frontend/src/components/metrics/CsatBars.vue -->
<template>
  <div class="card">
    <div class="card-head">
      <span class="card-title">Distribución CSAT</span>
      <span class="avg">{{ average === null ? "—" : average.toFixed(1) }} ★</span>
    </div>
    <apexchart :key="themeKey" type="bar" height="200" :options="opts" :series="series" />
  </div>
</template>

<script setup>
import { computed } from "vue";
import { baseOptions, chartColors } from "../../theme/apexTheme.js";
import { useTheme } from "../../composables/useTheme.js";

const props = defineProps({ distribution: Object, average: { type: Number, default: null } });

const { isDark } = useTheme();
const themeKey = computed(() => (isDark.value ? "dark" : "light"));

const series = computed(() => [{ name: "Respuestas",
  data: [1, 2, 3, 4, 5].map((s) => (props.distribution?.[s] ?? props.distribution?.[String(s)] ?? 0)) }]);

const opts = computed(() => {
  void themeKey.value; // dependencia reactiva: recomputa colores al togglear el tema
  const c = chartColors();
  return {
    ...baseOptions(),
    colors: [c.accent],
    plotOptions: { bar: { borderRadius: 4, columnWidth: "45%" } },
    xaxis: { ...baseOptions().xaxis, categories: ["1★", "2★", "3★", "4★", "5★"] },
  };
});
</script>

<style scoped>
.card { background: var(--surface); border: 0.5px solid var(--border); border-radius: var(--r); padding: 16px; }
.card-head { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 8px; }
.card-title { font-family: var(--font-display); font-size: 14px; font-weight: 600; color: var(--text); }
.avg { font-family: var(--font-mono); font-size: 15px; color: var(--accent); }
</style>
