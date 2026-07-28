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
        <section class="insights">
          <div class="insights-head">
            <span class="insights-title">✨ Análisis con IA</span>
            <button class="insights-btn" :disabled="insightsLoading" @click="loadInsights">
              {{ insightsLoading ? "Analizando…" : (insights ? "Regenerar" : "Analizar período") }}
            </button>
          </div>
          <div v-if="insightsError" class="insights-error">{{ insightsError }}</div>
          <p v-else-if="insights" class="insights-body">{{ insights }}</p>
          <p v-else class="insights-hint">
            Generá un resumen ejecutivo con tendencias, temas recurrentes y acciones recomendadas para este período.
          </p>
        </section>

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
import { getInsights } from "../../api/ai.api.js";
import { fmtPct, fmtMin, fmtNum } from "../../utils/metricsFormat.js";

const window = ref(30);
const data = ref(null);
const loading = ref(true);
const error = ref(false);

// Fase 4: análisis con IA del período.
const insights = ref("");
const insightsLoading = ref(false);
const insightsError = ref("");

async function load() {
  loading.value = true; error.value = false;
  try { data.value = await getAdminMetrics(window.value); }
  catch (e) { error.value = true; }
  finally { loading.value = false; }
}

async function loadInsights() {
  if (insightsLoading.value) return;
  insightsLoading.value = true;
  insightsError.value = "";
  try {
    const res = await getInsights(window.value);
    insights.value = res.insights || "";
  } catch (e) {
    const d = e?.response?.data;
    insightsError.value = d?.upsell
      ? "El análisis con IA está disponible en los planes Pro y Business."
      : d?.detail || "No se pudo generar el análisis.";
  } finally {
    insightsLoading.value = false;
  }
}

watch(window, () => { insights.value = ""; insightsError.value = ""; load(); });
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

.insights {
  background: var(--surface);
  border: 0.5px solid var(--border);
  border-left: 3px solid var(--accent);
  border-radius: var(--r);
  padding: 16px 18px;
}
.insights-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.insights-title {
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: var(--accent);
}
[data-theme="dark"] .insights-title { color: var(--accent-2); }
.insights-btn {
  padding: 7px 14px;
  border-radius: var(--r-sm);
  background: var(--accent);
  color: var(--accent-fg);
  font-family: var(--font-display);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: background .15s, opacity .15s;
}
.insights-btn:hover:not(:disabled) { background: var(--accent-hover); }
.insights-btn:disabled { opacity: .55; cursor: not-allowed; }
.insights-body {
  margin: 12px 0 0;
  font-size: 13px;
  line-height: 1.6;
  color: var(--text);
  white-space: pre-wrap;
}
.insights-hint { margin: 10px 0 0; font-size: 12px; color: var(--text-3); line-height: 1.5; }
.insights-error {
  margin: 12px 0 0;
  padding: 9px 12px;
  border-radius: var(--r-sm);
  background: var(--c-urgent-bg);
  color: var(--c-urgent);
  font-size: 12px;
}
</style>
