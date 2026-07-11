<!-- frontend/src/components/metrics/TechRankingTable.vue -->
<template>
  <div class="card">
    <span class="card-title">Ranking por técnico</span>
    <table class="tbl">
      <thead>
        <tr><th>Técnico</th><th>Resueltos</th><th>Cumpl. SLA</th><th>CSAT</th><th>T. medio</th></tr>
      </thead>
      <tbody>
        <tr v-for="r in rows" :key="r.technician_id">
          <td>{{ r.name }}</td>
          <td class="num">{{ r.resolved }}</td>
          <td class="num">{{ fmtPct(r.sla_pct) }}</td>
          <td class="num">{{ r.csat_avg === null ? "—" : r.csat_avg.toFixed(1) }}</td>
          <td class="num">{{ fmtMin(r.avg_resolution_min) }}</td>
        </tr>
        <tr v-if="rows.length === 0"><td colspan="5" class="empty">Sin datos en este período.</td></tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
import { fmtPct, fmtMin } from "../../utils/metricsFormat.js";
defineProps({ rows: { type: Array, default: () => [] } });
</script>

<style scoped>
.card { background: var(--surface); border: 0.5px solid var(--border); border-radius: var(--r); padding: 16px; }
.card-title { font-family: var(--font-display); font-size: 14px; font-weight: 600; color: var(--text); display: block; margin-bottom: 10px; }
.tbl { width: 100%; border-collapse: collapse; font-size: 13px; }
.tbl th { text-align: left; padding: 6px 8px; font-family: var(--font-mono); font-size: 11px;
          text-transform: uppercase; letter-spacing: 1px; color: var(--text-3); }
.tbl td { padding: 8px; border-top: 0.5px solid var(--border); color: var(--text); }
.num { font-family: var(--font-mono); }
.empty { color: var(--text-3); text-align: center; }
</style>
