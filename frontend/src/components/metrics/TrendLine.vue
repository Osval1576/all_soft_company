<!-- frontend/src/components/metrics/TrendLine.vue -->
<template>
  <div class="card">
    <span class="card-title">Creados vs resueltos</span>
    <div v-if="series.length === 0" class="empty">Sin datos en este período.</div>
    <apexchart v-else :key="themeKey" type="line" height="240" :options="opts" :series="chartSeries" />
  </div>
</template>

<script setup>
import { computed } from "vue";
import { baseOptions, chartColors } from "../../theme/apexTheme.js";
import { useTheme } from "../../composables/useTheme.js";

const props = defineProps({ series: { type: Array, default: () => [] } });

const { isDark } = useTheme();
const themeKey = computed(() => (isDark.value ? "dark" : "light"));

const chartSeries = computed(() => [
  { name: "Creados", data: props.series.map((p) => p.created) },
  { name: "Resueltos", data: props.series.map((p) => p.resolved) },
]);

const opts = computed(() => {
  void themeKey.value; // dependencia reactiva: recomputa colores al togglear el tema
  const c = chartColors();
  return {
    ...baseOptions(),
    colors: [c.accent, c.good],
    xaxis: { ...baseOptions().xaxis,
      categories: props.series.map((p) => p.date.slice(5)),
      tickAmount: Math.min(props.series.length, 8) },
    yaxis: { ...baseOptions().yaxis, min: 0, forceNiceScale: true,
             labels: { ...baseOptions().yaxis.labels, formatter: (v) => String(Math.round(v)) } },
  };
});
</script>

<style scoped>
.card { background: var(--surface); border: 0.5px solid var(--border); border-radius: var(--r); padding: 16px; }
.card-title { font-family: var(--font-display); font-size: 14px; font-weight: 600; color: var(--text); }
.empty {
  min-height: 240px;
  display: grid;
  place-items: center;
  color: var(--text-3);
  font-size: 13px;
  text-align: center;
}
</style>
