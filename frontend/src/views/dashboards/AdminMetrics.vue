<!-- frontend/src/views/dashboards/AdminMetrics.vue -->
<template>
  <div class="page">
    <AppTopBar title="Métricas del equipo" />
    <div class="wrap">
      <div class="bar">
        <router-link to="/admin" class="back">← Panel</router-link>
        <WindowSelector v-model="window" />
      </div>

      <div v-if="error" class="state err">
        No se pudieron cargar las métricas. <button class="retry" @click="load">Reintentar</button>
      </div>
      <div v-else-if="loading" class="state">Cargando…</div>

      <template v-else-if="data">
        <div class="tiles">
          <MetricTile label="Tickets" :value="fmtNum(data.totals.total)" :hint="`${data.totals.open} abiertos`" />
          <MetricTile label="SLA 1ª respuesta" :value="fmtPct(data.compliance.first_response)" />
          <MetricTile label="SLA resolución" :value="fmtPct(data.compliance.resolution)" />
          <MetricTile label="CSAT promedio" :value="data.csat.average === null ? '—' : data.csat.average.toFixed(1)" :hint="`${data.csat.count} respuestas`" />
          <MetricTile label="T. medio resolución" :value="fmtMin(data.avg_times.resolution_min)" />
        </div>

        <div class="gauges">
          <SlaGauge label="1ª respuesta" :value="data.compliance.first_response" />
          <SlaGauge label="Resolución" :value="data.compliance.resolution" />
        </div>

        <TrendLine :series="data.trend" />
        <CsatBars :distribution="data.csat.distribution" :average="data.csat.average" />
        <TechRankingTable :rows="data.ranking" />
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from "vue";
import AppTopBar from "../../components/AppTopBar.vue";
import WindowSelector from "../../components/metrics/WindowSelector.vue";
import MetricTile from "../../components/metrics/MetricTile.vue";
import SlaGauge from "../../components/metrics/SlaGauge.vue";
import TrendLine from "../../components/metrics/TrendLine.vue";
import CsatBars from "../../components/metrics/CsatBars.vue";
import TechRankingTable from "../../components/metrics/TechRankingTable.vue";
import { getAdminMetrics } from "../../api/metrics.api.js";
import { fmtPct, fmtMin, fmtNum } from "../../utils/metricsFormat.js";

const window = ref(30);
const data = ref(null);
const loading = ref(true);
const error = ref(false);

async function load() {
  loading.value = true; error.value = false;
  try { data.value = await getAdminMetrics(window.value); }
  catch (e) { error.value = true; }
  finally { loading.value = false; }
}

watch(window, load);
onMounted(load);
</script>

<style scoped>
.wrap { max-width: 1000px; margin: 0 auto; padding: 24px 20px; display: flex; flex-direction: column; gap: 18px; }
.bar { display: flex; justify-content: space-between; align-items: center; }
.back { font-size: 13px; color: var(--text-2); }
.state { color: var(--text-3); padding: 40px 0; text-align: center; }
.state.err { color: var(--c-urgent); }
.retry { color: var(--accent); text-decoration: underline; margin-left: 6px; }
.tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; }
.gauges { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
</style>
