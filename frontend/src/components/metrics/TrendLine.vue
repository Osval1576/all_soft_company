<!-- frontend/src/components/metrics/TrendLine.vue -->
<template>
  <div class="card">
    <span class="card-title">Creados vs resueltos</span>
    <apexchart type="line" height="240" :options="opts" :series="series" />
  </div>
</template>

<script setup>
import { computed } from "vue";
import { baseOptions, chartColors } from "../../theme/apexTheme.js";

const props = defineProps({ series: { type: Array, default: () => [] } });

const chartSeries = computed(() => [
  { name: "Creados", data: props.series.map((p) => p.created) },
  { name: "Resueltos", data: props.series.map((p) => p.resolved) },
]);
const series = chartSeries;

const opts = computed(() => {
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
</style>
